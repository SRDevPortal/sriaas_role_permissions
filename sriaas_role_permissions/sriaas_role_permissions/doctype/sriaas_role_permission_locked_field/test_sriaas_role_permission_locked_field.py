from unittest.mock import patch

from frappe.tests import UnitTestCase

from sriaas_role_permissions.api import field_policy


LOCKED_FIELDS = {
    "lock_after_insert": {"mobile_no"},
    "leaders_can_change": {"source"},
    "agent_always_lock": {"lead_owner"},
}


class TestSRIAASRolePermissionLockedField(UnitTestCase):
    def get_policy(
        self,
        fieldname,
        *,
        user="test@example.com",
        is_new=False,
        privileged=False,
        team_leader=False,
        agent=False,
    ):
        with (
            patch.object(field_policy, "get_locked_fields", return_value=LOCKED_FIELDS),
            patch.object(field_policy, "is_privileged", return_value=privileged),
            patch.object(field_policy, "has_team_leader_role", return_value=team_leader),
            patch.object(field_policy, "has_agent_role", return_value=agent),
        ):
            return field_policy.get_field_policy(
                "CRM Lead",
                fieldname,
                user=user,
                is_new=is_new,
            )

    def test_privileged_user_can_edit_locked_field(self):
        policy = self.get_policy("lead_owner", privileged=True)
        self.assertIs(policy["can_view"], True)
        self.assertIs(policy["can_edit"], True)
        self.assertEqual(policy["reason"], "privileged")

    def test_agent_cannot_edit_agent_locked_field(self):
        policy = self.get_policy("lead_owner", agent=True)
        self.assertIs(policy["can_edit"], False)
        self.assertEqual(policy["reason"], "agents_cannot_change")

    def test_team_leader_can_set_insert_locked_field_only_on_create(self):
        create_policy = self.get_policy("mobile_no", team_leader=True, is_new=True)
        update_policy = self.get_policy("mobile_no", team_leader=True, is_new=False)

        self.assertIs(create_policy["can_edit"], True)
        self.assertEqual(create_policy["reason"], "leaders_can_set_when_creating")
        self.assertIs(update_policy["can_edit"], False)
        self.assertEqual(update_policy["reason"], "field_rule_locked")

    def test_team_leader_can_change_explicitly_allowed_field(self):
        policy = self.get_policy("source", team_leader=True)
        self.assertIs(policy["can_edit"], True)
        self.assertEqual(policy["reason"], "leaders_can_change")

    def test_regular_user_can_edit_unconfigured_field(self):
        policy = self.get_policy("first_name")
        self.assertIs(policy["can_edit"], True)
        self.assertEqual(policy["reason"], "no_field_rule")

    def test_guest_cannot_view_field(self):
        policy = self.get_policy("lead_owner", user="Guest")
        self.assertIs(policy["can_view"], False)
