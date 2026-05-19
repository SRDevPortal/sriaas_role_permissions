import frappe
from frappe.tests.utils import FrappeTestCase


class TestSRIAASRolePermissionSettings(FrappeTestCase):
    def test_single_settings_loads(self):
        if frappe.db.exists("DocType", "SRIAAS Role Permission Settings"):
            self.assertEqual(
                frappe.get_single("SRIAAS Role Permission Settings").doctype,
                "SRIAAS Role Permission Settings",
            )

