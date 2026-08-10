from __future__ import annotations

import frappe

from sriaas_role_permissions.api.config import DEFAULT_DOCTYPE_CONFIGS, DEFAULT_LOCKED_FIELDS


SETTINGS_DOCTYPE = "SRIAAS Role Permission Settings"
DEFAULT_ROLE_ROWS = (
    ("CRM Lead", "Team Leader", "Team Leader"),
    ("CRM Lead", "Agent", "Agent"),
    ("CRM Lead", "Privileged", "System Manager"),
    ("Patient", "Payment Viewer", "System Manager"),
    ("Patient", "Payment Viewer", "Accounts Manager"),
    ("Patient", "Payment Viewer", "Accounts User"),
)
DEFAULT_RULES = {
    "CRM Lead": {
        "Team Leader": {"Team Leader"},
        "Agent": {"Agent"},
        "Privileged": {"System Manager"},
    },
    "Patient": {
        "Payment Viewer": {"System Manager", "Accounts Manager", "Accounts User"},
    },
}


def get_roles(ref_doctype: str, role_type: str) -> set[str]:
    configured = _get_configured_roles(ref_doctype, role_type)
    if configured:
        return configured

    return set(DEFAULT_RULES.get(ref_doctype, {}).get(role_type, set()))


def get_team_leader_roles(ref_doctype: str) -> set[str]:
    return get_roles(ref_doctype, "Team Leader")


def get_agent_roles(ref_doctype: str) -> set[str]:
    return get_roles(ref_doctype, "Agent")


def get_privileged_roles(ref_doctype: str) -> set[str]:
    return get_roles(ref_doctype, "Privileged")


def user_has_any_role(user: str, roles: set[str]) -> bool:
    if not roles:
        return False
    return bool(set(frappe.get_roles(user) or []) & roles)


def is_privileged(user: str, ref_doctype: str) -> bool:
    if user == "Administrator":
        return True
    return user_has_any_role(user, get_privileged_roles(ref_doctype))


def has_team_leader_role(user: str, ref_doctype: str) -> bool:
    return user_has_any_role(user, get_team_leader_roles(ref_doctype))


def has_agent_role(user: str, ref_doctype: str) -> bool:
    return user_has_any_role(user, get_agent_roles(ref_doctype))


@frappe.whitelist()
def get_user_permission_context(ref_doctype: str) -> dict:
    user = frappe.session.user
    return {
        "ref_doctype": ref_doctype,
        "is_privileged": is_privileged(user, ref_doctype),
        "has_team_leader_role": has_team_leader_role(user, ref_doctype),
        "has_agent_role": has_agent_role(user, ref_doctype),
        "team_leader_roles": sorted(get_team_leader_roles(ref_doctype)),
        "agent_roles": sorted(get_agent_roles(ref_doctype)),
        "privileged_roles": sorted(get_privileged_roles(ref_doctype)),
    }


@frappe.whitelist()
def test_current_user_access(ref_doctype: str = "CRM Lead") -> dict:
    frappe.only_for("System Manager")
    return get_user_permission_context(ref_doctype)


@frappe.whitelist()
def reset_default_crm_lead_roles() -> dict:
    frappe.only_for("System Manager")

    settings = frappe.get_single(SETTINGS_DOCTYPE)
    if not settings.enabled:
        settings.enabled = 1

    existing = {
        (row.ref_doctype, row.role_type, row.role): row
        for row in settings.get("roles")
        if row.ref_doctype and row.role_type and row.role
    }

    added = []
    enabled = []
    config_added = []
    locked_added = []
    skipped = []

    for ref_doctype, role_type, role in DEFAULT_ROLE_ROWS:
        if not frappe.db.exists("DocType", ref_doctype):
            skipped.append({"doctype": ref_doctype, "role_type": role_type, "role": role, "reason": "Missing DocType"})
            continue

        if not frappe.db.exists("Role", role):
            skipped.append({"doctype": ref_doctype, "role_type": role_type, "role": role, "reason": "Missing Role"})
            continue

        row = existing.get((ref_doctype, role_type, role))
        if row:
            if not row.enabled:
                row.enabled = 1
                enabled.append({"doctype": ref_doctype, "role_type": role_type, "role": role})
            continue

        settings.append(
            "roles",
            {
                "enabled": 1,
                "ref_doctype": ref_doctype,
                "role_type": role_type,
                "role": role,
            },
        )
        added.append({"doctype": ref_doctype, "role_type": role_type, "role": role})

    existing_configs = {
        row.ref_doctype
        for row in settings.get("doctype_configs")
        if row.ref_doctype
    }
    for ref_doctype, config in DEFAULT_DOCTYPE_CONFIGS.items():
        if ref_doctype in existing_configs:
            continue
        if not frappe.db.exists("DocType", ref_doctype):
            skipped.append({"doctype": ref_doctype, "reason": "Missing DocType"})
            continue
        settings.append("doctype_configs", {"enabled": 1, **config})
        config_added.append({"doctype": ref_doctype})

    existing_locked = {
        (row.ref_doctype, row.fieldname)
        for row in settings.get("locked_fields")
        if row.ref_doctype and row.fieldname
    }
    for ref_doctype, groups in DEFAULT_LOCKED_FIELDS.items():
        if not frappe.db.exists("DocType", ref_doctype):
            skipped.append({"doctype": ref_doctype, "reason": "Missing DocType"})
            continue
        fieldnames = (
            set(groups.get("lock_after_insert", set()))
            | set(groups.get("leaders_can_change", set()))
            | set(groups.get("agent_always_lock", set()))
        )
        for fieldname in sorted(fieldnames):
            if (ref_doctype, fieldname) in existing_locked:
                continue
            if not frappe.db.has_column(ref_doctype, fieldname):
                skipped.append({"doctype": ref_doctype, "fieldname": fieldname, "reason": "Missing field"})
                continue
            settings.append(
                "locked_fields",
                {
                    "enabled": 1,
                    "ref_doctype": ref_doctype,
                    "fieldname": fieldname,
                    "lock_after_insert": fieldname in groups.get("lock_after_insert", set()),
                    "leaders_can_change": fieldname in groups.get("leaders_can_change", set()),
                    "agent_always_lock": fieldname in groups.get("agent_always_lock", set()),
                },
            )
            locked_added.append({"doctype": ref_doctype, "fieldname": fieldname})

    settings.save(ignore_permissions=True)
    frappe.clear_cache(doctype=SETTINGS_DOCTYPE)

    return {
        "added": added,
        "enabled": enabled,
        "config_added": config_added,
        "locked_added": locked_added,
        "skipped": skipped,
    }


def _get_configured_roles(ref_doctype: str, role_type: str) -> set[str]:
    if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
        return set()

    settings = frappe.get_single(SETTINGS_DOCTYPE)
    if not settings.enabled:
        return set()

    roles = {
        row.role
        for row in settings.get("roles")
        if row.enabled and row.ref_doctype == ref_doctype and row.role_type == role_type and row.role
    }
    return roles
