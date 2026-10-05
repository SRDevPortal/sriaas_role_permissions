import json
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import MagicMock, patch

import frappe
from sriaas_role_permissions import customer_number_privacy as api


class PrivacyControlTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "site_config.json"
        self.path.write_text(json.dumps({"unrelated": "keep"}))
        self.config = {}
        self.settings = MagicMock()
        self.audit = MagicMock()
        self.database = MagicMock()
        self.patches = [
            patch.object(api, "_", side_effect=lambda text: text),
            patch.object(frappe.local, "flags", frappe._dict(in_test=True), create=True),
            patch.object(frappe, "conf", self.config),
            patch.object(frappe, "db", self.database),
            patch.object(frappe, "only_for"),
            patch.object(frappe, "get_single", return_value=self.settings),
            patch.object(frappe, "get_doc", return_value=self.audit),
            patch.object(frappe, "get_site_path", return_value=str(self.path)),
            patch.object(frappe, "get_site_config", side_effect=self.read),
            patch.object(frappe, "get_installed_apps", return_value=["privacy_shield"]),
            patch.object(frappe, "clear_cache"),
            patch.object(api, "filelock", return_value=nullcontext()),
            patch.object(api, "update_site_config", side_effect=self.write),
            patch.object(frappe, "throw", side_effect=lambda message, exc=frappe.ValidationError: self.raise_error(exc)),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    @staticmethod
    def raise_error(exc):
        raise exc()

    def read(self):
        return json.loads(self.path.read_text())

    def write(self, key, value):
        data = self.read()
        if value == "None":
            data.pop(key, None)
        else:
            data[key] = value
        self.path.write_text(json.dumps(data))

    def test_enable_disable_preserves_other_settings_and_records_each_change(self):
        self.assertFalse(api.get_status()["enabled"])
        self.assertTrue(api.set_enabled(1, 0)["enabled"])
        self.assertTrue(self.read()[api.KEY])
        self.assertFalse(api.set_enabled(0, 1)["enabled"])
        self.assertFalse(self.read()[api.KEY])
        self.assertEqual(self.read()["unrelated"], "keep")
        self.assertEqual(self.audit.insert.call_count, 2)
        self.assertEqual(self.database.commit.call_count, 2)
        self.settings.check_permission.assert_any_call("read")
        self.settings.check_permission.assert_any_call("write")
        for call in frappe.get_doc.call_args_list:
            self.assertEqual(call.args[0]["ref_doctype"], api.SETTINGS)
            self.assertEqual(call.args[0]["docname"], api.SETTINGS)

    def test_unauthorized_user_cannot_read_or_change(self):
        frappe.only_for.side_effect = frappe.PermissionError
        for call in (api.get_status, lambda: api.set_enabled(1, 0)):
            with self.assertRaises(frappe.PermissionError):
                call()
        api.update_site_config.assert_not_called()
        self.audit.insert.assert_not_called()

    def test_document_write_permission_is_required(self):
        self.settings.check_permission.side_effect = frappe.PermissionError
        with self.assertRaises(frappe.PermissionError):
            api.set_enabled(1, 0)
        api.update_site_config.assert_not_called()

    def test_invalid_and_stale_requests_do_not_change_config(self):
        for invalid in ("true", "yes", "", None, [], 2):
            with self.subTest(value=invalid), self.assertRaises(frappe.ValidationError):
                api.set_enabled(invalid, 0)
        with self.assertRaises(frappe.TimestampMismatchError):
            api.set_enabled(0, 1)
        api.update_site_config.assert_not_called()

    def test_missing_app_cannot_be_enabled(self):
        frappe.get_installed_apps.return_value = []
        with self.assertRaises(frappe.ValidationError):
            api.set_enabled(1, 0)
        api.update_site_config.assert_not_called()

    def test_no_change_does_not_write_or_audit(self):
        api.set_enabled(0, 0)
        api.update_site_config.assert_not_called()
        self.audit.insert.assert_not_called()

    def test_audit_failure_leaves_config_untouched(self):
        self.audit.insert.side_effect = RuntimeError("audit unavailable")
        with self.assertRaises(RuntimeError):
            api.set_enabled(1, 0)
        api.update_site_config.assert_not_called()
        self.database.rollback.assert_called_once()

    def test_commit_failure_restores_absent_override(self):
        self.database.commit.side_effect = RuntimeError("commit failed")
        with self.assertRaises(RuntimeError):
            api.set_enabled(1, 0)
        self.assertNotIn(api.KEY, self.read())
        self.assertEqual(self.read()["unrelated"], "keep")
        self.database.rollback.assert_called_once()

    def test_commit_failure_restores_explicit_override(self):
        self.write(api.KEY, True)
        self.database.commit.side_effect = RuntimeError("commit failed")
        with self.assertRaises(RuntimeError):
            api.set_enabled(0, 1)
        self.assertIs(self.read()[api.KEY], True)

    def test_read_status_exposes_no_other_config_values(self):
        self.assertEqual(set(api.get_status()), {"enabled", "installed"})

    def test_switch_is_post_only(self):
        self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[api.set_enabled], ["POST"])
