from __future__ import annotations

import frappe

from sriaas_role_permissions.api.config import DEFAULT_DOCTYPE_CONFIGS, DEFAULT_LOCKED_FIELDS
from sriaas_role_permissions.api.roles import DEFAULT_ROLE_ROWS
from sriaas_role_permissions.workspace.workspace import create_workspace


def setup_all():
    ensure_default_settings()
    create_workspace()
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
        row.ref_doctype
        for row in settings.get("doctype_configs")
        if row.ref_doctype
    }
    for ref_doctype, config in DEFAULT_DOCTYPE_CONFIGS.items():
        if ref_doctype in existing_configs or not frappe.db.exists("DocType", ref_doctype):
            continue
        settings.append("doctype_configs", {"enabled": 1, **config})
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
