from __future__ import annotations

import frappe

from sriaas_role_permissions.api.config import get_locked_fields
from sriaas_role_permissions.api.roles import (
	has_agent_role,
	has_team_leader_role,
	is_privileged,
)


def _as_bool(value) -> bool:
	return str(value).lower() in {"1", "true", "yes"}


def get_field_policy(
	ref_doctype: str,
	fieldname: str,
	*,
	user: str | None = None,
	is_new: bool = False,
) -> dict:
	user = user or frappe.session.user
	locked = get_locked_fields(ref_doctype)
	is_privileged_user = is_privileged(user, ref_doctype)
	is_team_leader = has_team_leader_role(user, ref_doctype)
	is_agent = has_agent_role(user, ref_doctype)
	leaders_can_set_on_create = fieldname in locked.get("lock_after_insert", set())
	leaders_can_change = fieldname in locked.get("leaders_can_change", set())
	agents_cannot_change = fieldname in locked.get("agent_always_lock", set())

	can_edit = is_privileged_user
	reason = None

	if not can_edit:
		if is_agent and agents_cannot_change:
			can_edit = False
			reason = "agents_cannot_change"
		elif is_team_leader and leaders_can_change:
			can_edit = True
			reason = "leaders_can_change"
		elif is_team_leader and is_new and leaders_can_set_on_create:
			can_edit = True
			reason = "leaders_can_set_when_creating"
		elif leaders_can_set_on_create or leaders_can_change or agents_cannot_change:
			can_edit = False
			reason = "field_rule_locked"
		else:
			can_edit = True
			reason = "no_field_rule"
	else:
		reason = "privileged"

	return {
		"ref_doctype": ref_doctype,
		"fieldname": fieldname,
		"user": user,
		"can_view": user not in {"", "Guest"},
		"can_edit": bool(can_edit),
		"reason": reason,
		"is_privileged": bool(is_privileged_user),
		"has_team_leader_role": bool(is_team_leader),
		"has_agent_role": bool(is_agent),
		"leaders_can_set_when_creating": bool(leaders_can_set_on_create),
		"leaders_can_change": bool(leaders_can_change),
		"agents_cannot_change": bool(agents_cannot_change),
	}


def can_edit_field(ref_doctype: str, fieldname: str, *, user: str | None = None, is_new: bool = False) -> bool:
	return bool(get_field_policy(ref_doctype, fieldname, user=user, is_new=is_new).get("can_edit"))


def can_view_field(ref_doctype: str, fieldname: str, *, user: str | None = None) -> bool:
	return bool(get_field_policy(ref_doctype, fieldname, user=user).get("can_view"))


def get_field_policies(
	ref_doctype: str,
	*,
	fieldnames: list[str] | tuple[str, ...] | set[str] | None = None,
	user: str | None = None,
	is_new: bool = False,
) -> dict[str, dict]:
	locked = get_locked_fields(ref_doctype)
	if fieldnames is None:
		fieldnames = sorted(
			set(locked.get("lock_after_insert", set()))
			| set(locked.get("leaders_can_change", set()))
			| set(locked.get("agent_always_lock", set()))
		)

	return {
		fieldname: get_field_policy(ref_doctype, fieldname, user=user, is_new=is_new)
		for fieldname in fieldnames
	}


@frappe.whitelist()
def get_field_policy_context(ref_doctype: str, fieldnames=None, is_new: bool | int | str = False) -> dict:
	fieldnames = frappe.parse_json(fieldnames) if isinstance(fieldnames, str) else fieldnames
	if isinstance(fieldnames, str):
		fieldnames = [fieldnames]
	return {
		"ref_doctype": ref_doctype,
		"is_new": _as_bool(is_new),
		"fields": get_field_policies(ref_doctype, fieldnames=fieldnames, is_new=_as_bool(is_new)),
	}


def validate_field_change(doc, fieldname: str) -> None:
	if not hasattr(doc, fieldname) or not doc.has_value_changed(fieldname):
		return
	if can_edit_field(doc.doctype, fieldname, is_new=doc.is_new()):
		return
	frappe.throw(
		frappe._("You are not allowed to change field {0}.").format(frappe.bold(fieldname)),
		frappe.PermissionError,
	)
