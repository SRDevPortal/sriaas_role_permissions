"""Admin UI for the existing site privacy switch; no alternative policy source."""
import json
from pathlib import Path

import frappe
from frappe import _
from frappe.installer import update_site_config
from frappe.utils.synchronization import filelock

SETTINGS = "SRIAAS Role Permission Settings"
KEY = "privacy_shield_desk_enabled"


def _authorize(permission):
    frappe.only_for("System Manager")
    settings = frappe.get_single(SETTINGS)
    settings.check_permission(permission)
    return settings


def _parse_enabled(value):
    if value not in (True, False, 0, 1, "0", "1"):
        frappe.throw(_("Expected an enabled or disabled value."))
    return value in (True, 1, "1")


def _status():
    config = frappe.get_site_config()
    return {
        "enabled": bool(config.get(KEY, False)),
        "installed": "privacy_shield" in frappe.get_installed_apps(),
    }


@frappe.whitelist()
def get_status():
    _authorize("read")
    return _status()


@frappe.whitelist(methods=["POST"])
def set_enabled(enabled, expected_enabled):
    _authorize("write")
    desired = _parse_enabled(enabled)
    expected = _parse_enabled(expected_enabled)
    # Serializes this UI's read/change/audit operation. The config writer also
    # takes Frappe's site_config lock and preserves unrelated configuration keys.
    with filelock("customer_number_privacy"):
        status = _status()
        if status["enabled"] != expected:
            frappe.throw(_("Privacy changed in another session. Reload before applying."),
                         frappe.TimestampMismatchError)
        if desired and not status["installed"]:
            frappe.throw(_("Install Privacy Shield before enabling Customer Number Privacy."))
        if desired == status["enabled"]:
            return status

        config_path = Path(frappe.get_site_path("site_config.json"))
        original = json.loads(config_path.read_text())
        had_override = KEY in original
        previous_override = original.get(KEY)
        changed = False
        try:
            frappe.get_doc({
                "doctype": "Version",
                "ref_doctype": SETTINGS,
                "docname": SETTINGS,
                "data": json.dumps({"changed": [[
                    "privacy_number_control",
                    "Enabled" if status["enabled"] else "Disabled",
                    "Enabled" if desired else "Disabled",
                ]]}),
            }).insert(ignore_permissions=True)
            update_site_config(KEY, desired)
            changed = True
            frappe.conf[KEY] = desired
            frappe.clear_cache(doctype=SETTINGS)
            # Commit the history while holding the activation lock. If it fails,
            # restore the previous override rather than leaving an unaudited change.
            frappe.db.commit()
        except Exception:
            if changed:
                update_site_config(KEY, previous_override if had_override else "None")
                frappe.conf[KEY] = status["enabled"]
            frappe.db.rollback()
            raise
        return {"enabled": desired, "installed": status["installed"]}
