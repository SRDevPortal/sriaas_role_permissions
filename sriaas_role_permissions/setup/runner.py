from __future__ import annotations

import frappe

from sriaas_role_permissions.api.config import (
    DEFAULT_DOCTYPE_CONFIGS,
    DEFAULT_LOCKED_FIELDS,
    get_available_doctype_config,
)
from sriaas_role_permissions.api.roles import DEFAULT_ROLE_ROWS


def setup_all():
    ensure_default_settings()
    frappe.clear_cache()


def ensure_default_settings():
    if not frappe.db.exists("DocType", "SRIAAS Role Permission Settings"):
        return

    settings = frappe.get_single("SRIAAS Role Permission Settings")
    changed = False

    if not settings.enabled:
        settings.enabled = 1
        changed = True

    existing = {
        (row.ref_doctype, row.role_type, row.role)
        for row in settings.get("roles")
        if row.ref_doctype and row.role_type and row.role
    }

    for ref_doctype, role_type, role in DEFAULT_ROLE_ROWS:
        if (ref_doctype, role_type, role) in existing:
            continue
        if not frappe.db.exists("DocType", ref_doctype):
            continue
        if not frappe.db.exists("Role", role):
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
        changed = True

    existing_configs = {
        row.ref_doctype: row
        for row in settings.get("doctype_configs")
        if row.ref_doctype
    }
    for ref_doctype, config in DEFAULT_DOCTYPE_CONFIGS.items():
        if not frappe.db.exists("DocType", ref_doctype):
            continue

        available_config = get_available_doctype_config(ref_doctype, config)
        if row := existing_configs.get(ref_doctype):
            for fieldname, value in available_config.items():
                if fieldname != "ref_doctype" and value and not row.get(fieldname):
                    row.set(fieldname, value)
                    changed = True
        else:
            settings.append("doctype_configs", {"enabled": 1, **available_config})
            changed = True

    existing_locked = {
        (row.ref_doctype, row.fieldname)
        for row in settings.get("locked_fields")
        if row.ref_doctype and row.fieldname
    }
    for ref_doctype, groups in DEFAULT_LOCKED_FIELDS.items():
        if not frappe.db.exists("DocType", ref_doctype):
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
            changed = True

    if changed:
        settings.save(ignore_permissions=True)
