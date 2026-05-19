from __future__ import annotations

import frappe
from frappe.model.document import Document


class SRIAASRolePermissionSettings(Document):
    def validate(self):
        self._validate_rows()
        self._validate_doctype_configs()
        self._validate_locked_fields()

    def on_update(self):
        frappe.clear_cache(doctype=self.doctype)

    def _validate_rows(self):
        seen = set()
        for row in self.get("roles"):
            if not row.enabled:
                continue

            key = (row.ref_doctype, row.role_type, row.role)
            if key in seen:
                frappe.throw(
                    f"Duplicate role rule: {row.ref_doctype} / {row.role_type} / {row.role}",
                    title="Duplicate Role Rule",
                )
            seen.add(key)

    def _validate_doctype_configs(self):
        seen = set()
        for row in self.get("doctype_configs"):
            if not row.enabled:
                continue

            if row.ref_doctype in seen:
                frappe.throw(
                    f"Duplicate DocType rule: {row.ref_doctype}",
                    title="Duplicate DocType Rule",
                )
            seen.add(row.ref_doctype)

            self._ensure_doctype(row.ref_doctype)
            if row.pipeline_doctype:
                self._ensure_doctype(row.pipeline_doctype)
            if row.pipeline_fieldname:
                self._ensure_field(row.ref_doctype, row.pipeline_fieldname)
            if row.owner_fieldname:
                self._ensure_field(row.ref_doctype, row.owner_fieldname)
            if row.team_leader_fieldname:
                self._ensure_field("User", row.team_leader_fieldname)

    def _validate_locked_fields(self):
        seen = set()
        for row in self.get("locked_fields"):
            if not row.enabled:
                continue

            key = (row.ref_doctype, row.fieldname)
            if key in seen:
                frappe.throw(
                    f"Duplicate locked field rule: {row.ref_doctype} / {row.fieldname}",
                    title="Duplicate Locked Field Rule",
                )
            seen.add(key)

            self._ensure_doctype(row.ref_doctype)
            self._ensure_field(row.ref_doctype, row.fieldname)

    def _ensure_doctype(self, doctype: str):
        if not doctype or not frappe.db.exists("DocType", doctype):
            frappe.throw(f"Invalid DocType: {doctype}", title="Invalid Setting")

    def _ensure_field(self, doctype: str, fieldname: str):
        if not fieldname or not fieldname.replace("_", "").isalnum():
            frappe.throw(f"Invalid fieldname: {fieldname}", title="Invalid Setting")
        if not frappe.db.has_column(doctype, fieldname):
            frappe.throw(
                f"Field {fieldname} does not exist on {doctype}",
                title="Invalid Setting",
            )
