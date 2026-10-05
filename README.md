# SRIAAS Role Permissions

Reusable role permission configuration for SRIAAS Frappe apps.

This app provides UI-configurable role groups such as Team Leader, Agent, and Privileged roles per DocType. Business apps can import the helper API instead of hard-coding role names.


## Customer Number Privacy activation

In **SRIAAS Role Permission Settings → Customer Number Privacy**, the status
shows the effective site switch. System Managers and Administrator can change
**Enable Customer Number Privacy** and click **Apply Privacy Setting**.
Save any role-rule edits first; the normal Save button only saves the form.

This control writes the existing site-specific privacy_shield_desk_enabled
setting. There is no second database activation setting and no automatic
activation during installation or migration. Existing values and role rows are
preserved. Changes appear in the settings document's change history.

New requests and jobs read the site configuration. Refresh open customer pages
after changing privacy; already loaded responses and running jobs are not
retroactively changed. Initial deployment of the Python code may require the
normal service reload for that environment.

The switch covers the existing opted-in privacy routes. Appointment patient
lookups and support customer lookups keep their independent protections.
The Vobiz click-to-call, system-call, and AI integrations apply the same role
policy while keeping provider routing numbers on the server.

Validation from the sites directory:

    ../env/bin/python -m unittest sriaas_role_permissions.tests.test_customer_number_privacy
    node ../apps/sriaas_role_permissions/sriaas_role_permissions/tests/test_customer_number_privacy_ui.cjs
