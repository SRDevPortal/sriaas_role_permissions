from __future__ import annotations

from dataclasses import asdict, dataclass

import frappe


SETTINGS_DOCTYPE = "SRIAAS Role Permission Settings"
DEFAULT_DOCTYPE_CONFIGS = {
    "CRM Lead": {
        "ref_doctype": "CRM Lead",
        "pipeline_doctype": "SR Lead Pipeline",
        "pipeline_fieldname": "sr_lead_pipeline",
        "owner_fieldname": "lead_owner",
        "team_leader_fieldname": "sr_reports_to_team_leader",
        "team_leader_label": "Team Leader",
        "agent_label": "Agent",
        "privileged_label": "Privileged",
    }
}
DEFAULT_LOCKED_FIELDS = {
    "CRM Lead": {
        "lock_after_insert": {"sr_lead_pipeline", "sr_lead_platform", "source", "mobile_no", "phone"},
        "agent_always_lock": {"lead_owner"},
    }
}


@dataclass(frozen=True)
class DoctypeConfig:
    ref_doctype: str
    pipeline_doctype: str
    pipeline_fieldname: str
    owner_fieldname: str
    team_leader_fieldname: str
    team_leader_label: str = "Team Leader"
    agent_label: str = "Agent"
    privileged_label: str = "Privileged"

    def as_dict(self) -> dict:
        return asdict(self)


def get_doctype_config(ref_doctype: str) -> DoctypeConfig:
    default = DEFAULT_DOCTYPE_CONFIGS.get(ref_doctype, {"ref_doctype": ref_doctype})
    row = _get_enabled_config_row(ref_doctype)

    data = dict(default)
    if row:
        for field in (
            "ref_doctype",
            "pipeline_doctype",
            "pipeline_fieldname",
            "owner_fieldname",
            "team_leader_fieldname",
            "team_leader_label",
            "agent_label",
            "privileged_label",
        ):
            value = row.get(field)
            if value:
                data[field] = value

    data.setdefault("pipeline_doctype", "")
    data.setdefault("pipeline_fieldname", "")
    data.setdefault("owner_fieldname", "")
    data.setdefault("team_leader_fieldname", "")
    data.setdefault("team_leader_label", "Team Leader")
    data.setdefault("agent_label", "Agent")
    data.setdefault("privileged_label", "Privileged")

    return DoctypeConfig(**data)


def get_locked_fields(ref_doctype: str) -> dict[str, set[str]]:
    configured = _get_enabled_locked_fields(ref_doctype)
    if configured["lock_after_insert"] or configured["agent_always_lock"]:
        return configured

    default = DEFAULT_LOCKED_FIELDS.get(ref_doctype, {})
    return {
        "lock_after_insert": set(default.get("lock_after_insert", set())),
        "agent_always_lock": set(default.get("agent_always_lock", set())),
    }


def get_context(ref_doctype: str) -> dict:
    config = get_doctype_config(ref_doctype)
    locked = get_locked_fields(ref_doctype)
    return {
        **config.as_dict(),
        "lock_after_insert_fields": sorted(locked["lock_after_insert"]),
        "agent_always_lock_fields": sorted(locked["agent_always_lock"]),
    }


@frappe.whitelist()
def get_doctype_context(ref_doctype: str = "CRM Lead") -> dict:
    return get_context(ref_doctype)


def safe_fieldname(fieldname: str) -> str:
    if not fieldname or not fieldname.replace("_", "").isalnum():
        frappe.throw(f"Invalid fieldname: {fieldname}", title="Invalid Role Permission Setting")
    return fieldname


def safe_doctype(doctype: str) -> str:
    if not doctype or not frappe.db.exists("DocType", doctype):
        frappe.throw(f"Invalid DocType: {doctype}", title="Invalid Role Permission Setting")
    return doctype


def sql_column(ref_doctype: str, fieldname: str) -> str:
    safe_doctype(ref_doctype)
    safe_fieldname(fieldname)
    if not frappe.db.has_column(ref_doctype, fieldname):
        frappe.throw(
            f"Field {fieldname} does not exist on {ref_doctype}",
            title="Invalid Role Permission Setting",
        )
    return f"`tab{ref_doctype}`.`{fieldname}`"


def _get_enabled_config_row(ref_doctype: str):
    if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
        return None

    settings = frappe.get_single(SETTINGS_DOCTYPE)
    if not settings.enabled:
        return None

    for row in settings.get("doctype_configs"):
        if row.enabled and row.ref_doctype == ref_doctype:
            return row
    return None


def _get_enabled_locked_fields(ref_doctype: str) -> dict[str, set[str]]:
    fields = {"lock_after_insert": set(), "agent_always_lock": set()}
    if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
        return fields

    settings = frappe.get_single(SETTINGS_DOCTYPE)
    if not settings.enabled:
        return fields

    for row in settings.get("locked_fields"):
        if not row.enabled or row.ref_doctype != ref_doctype or not row.fieldname:
            continue
        if row.lock_after_insert:
            fields["lock_after_insert"].add(row.fieldname)
        if row.agent_always_lock:
            fields["agent_always_lock"].add(row.fieldname)

    return fields
