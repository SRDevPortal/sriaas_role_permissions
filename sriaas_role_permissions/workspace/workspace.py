from __future__ import annotations

import json

import frappe


WORKSPACE_NAME = "SRIAAS Role Permissions"


def create_workspace():
    if not frappe.db.exists("DocType", "SRIAAS Role Permission Settings"):
        return

    if frappe.db.exists("Workspace", WORKSPACE_NAME):
        doc = frappe.get_doc("Workspace", WORKSPACE_NAME)
    else:
        doc = frappe.new_doc("Workspace")

    doc.name = WORKSPACE_NAME
    doc.label = WORKSPACE_NAME
    doc.title = WORKSPACE_NAME
    doc.module = "SRIAAS Role Permissions"
    doc.app = "sriaas_role_permissions"
    doc.public = 0
    doc.is_standard = 1
    doc.icon = "users"
    doc.category = "Modules"
    doc.sequence_id = 999
    doc.hide_custom = 0
    doc.content = json.dumps(
        [
            {
                "type": "header",
                "data": {
                    "text": '<span class="h4"><b>Role Permissions</b></span>',
                    "col": 12,
                },
            },
            {
                "type": "shortcut",
                "data": {
                    "shortcut_name": "Role Permission Settings",
                    "col": 3,
                },
            },
        ]
    )

    doc.set("shortcuts", [])
    doc.append(
        "shortcuts",
        {
            "type": "DocType",
            "link_to": "SRIAAS Role Permission Settings",
            "label": "Role Permission Settings",
            "color": "Blue",
        },
    )

    doc.set("links", [])
    doc.append(
        "links",
        {
            "type": "Card Break",
            "label": "Configuration",
            "icon": "settings",
        },
    )
    doc.append(
        "links",
        {
            "type": "Link",
            "label": "Role Permission Settings",
            "link_type": "DocType",
            "link_to": "SRIAAS Role Permission Settings",
        },
    )

    doc.save(ignore_permissions=True)
