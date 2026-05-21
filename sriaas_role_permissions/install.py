import frappe

from sriaas_role_permissions.setup.runner import setup_all


DOCTYPE_DOCS = (
    "sriaas_role_permission_role",
    "sriaas_role_permission_doctype_rule",
    "sriaas_role_permission_locked_field",
    "sriaas_role_permission_settings",
)


def after_install():
    sync_doctypes()
    setup_all()


def after_migrate():
    setup_all()


def sync_doctypes():
    for doctype in DOCTYPE_DOCS:
        frappe.reload_doc("sriaas_role_permissions", "doctype", doctype, force=True)
