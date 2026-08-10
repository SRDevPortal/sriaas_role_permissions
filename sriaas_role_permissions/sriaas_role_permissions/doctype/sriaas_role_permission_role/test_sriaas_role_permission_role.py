from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from sriaas_role_permissions.api.roles import (
    is_privileged,
    test_current_user_access,
    user_has_any_role,
)


class TestSRIAASRolePermissionRole(FrappeTestCase):
    def test_user_role_match_returns_boolean(self):
        with patch.object(frappe, "get_roles", return_value=["Agent", "Desk User"]):
            self.assertIs(user_has_any_role("agent@example.com", {"Agent"}), True)
            self.assertIs(user_has_any_role("agent@example.com", {"Team Leader"}), False)
            self.assertIs(user_has_any_role("agent@example.com", set()), False)

    def test_administrator_is_always_privileged(self):
        self.assertIs(is_privileged("Administrator", "CRM Lead"), True)

    def test_diagnostic_endpoint_requires_system_manager(self):
        original_user = frappe.session.user
        try:
            frappe.set_user("Guest")
            with self.assertRaises(frappe.PermissionError):
                test_current_user_access("CRM Lead")
        finally:
            frappe.set_user(original_user)
