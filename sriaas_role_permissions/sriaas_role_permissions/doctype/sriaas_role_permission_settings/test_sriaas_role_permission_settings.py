import frappe
from frappe.tests.utils import FrappeTestCase

from sriaas_role_permissions.api.config import get_available_doctype_config
from sriaas_role_permissions.setup.runner import ensure_default_settings


class TestSRIAASRolePermissionSettings(FrappeTestCase):
    def test_single_settings_loads(self):
        if frappe.db.exists("DocType", "SRIAAS Role Permission Settings"):
            self.assertEqual(
                frappe.get_single("SRIAAS Role Permission Settings").doctype,
                "SRIAAS Role Permission Settings",
            )

    def test_optional_config_references_are_omitted_when_missing(self):
        config = get_available_doctype_config(
            "CRM Lead",
            {
                "pipeline_doctype": "Missing Pipeline DocType",
                "pipeline_fieldname": "missing_pipeline_field",
                "owner_fieldname": "lead_owner",
                "team_leader_fieldname": "missing_team_leader_field",
                "team_leader_label": "Team Leader",
            },
        )

        self.assertNotIn("pipeline_doctype", config)
        self.assertNotIn("pipeline_fieldname", config)
        self.assertNotIn("team_leader_fieldname", config)
        self.assertEqual(config.get("owner_fieldname"), "lead_owner")
        self.assertEqual(config.get("team_leader_label"), "Team Leader")

    def test_default_setup_is_idempotent(self):
        ensure_default_settings()
        first = frappe.get_single("SRIAAS Role Permission Settings")
        first_counts = (
            len(first.get("roles")),
            len(first.get("doctype_configs")),
            len(first.get("locked_fields")),
        )

        ensure_default_settings()
        second = frappe.get_single("SRIAAS Role Permission Settings")
        second_counts = (
            len(second.get("roles")),
            len(second.get("doctype_configs")),
            len(second.get("locked_fields")),
        )

        self.assertEqual(second_counts, first_counts)

    def test_standard_workspace_is_restricted_to_system_manager(self):
        workspace = frappe.db.get_value(
            "Workspace",
            "SRIAAS Role Permissions",
            ["public", "app"],
            as_dict=True,
        )
        self.assertTrue(workspace)
        self.assertEqual(workspace.public, 1)
        self.assertEqual(workspace.app, "sriaas_role_permissions")

        roles = frappe.get_all(
            "Has Role",
            filters={
                "parent": "SRIAAS Role Permissions",
                "parenttype": "Workspace",
            },
            pluck="role",
        )
        self.assertIn("System Manager", roles)
