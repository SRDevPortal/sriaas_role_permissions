function applySriaasFieldPolicy(frm) {
	frappe.call({
		method: "sriaas_role_permissions.api.field_policy.get_field_policy_context",
		args: {
			ref_doctype: frm.doctype,
			is_new: frm.is_new() ? 1 : 0,
		},
		callback(r) {
			const fields = (r.message || {}).fields || {};
			Object.keys(fields).forEach((fieldname) => {
				if (!frm.fields_dict[fieldname]) return;
				const policy = fields[fieldname] || {};
				frm.set_df_property(fieldname, "hidden", !policy.can_view);
				frm.set_df_property(fieldname, "read_only", !policy.can_edit);
			});
		},
	});
}

frappe.ui.form.on("CRM Lead", {
	refresh: applySriaasFieldPolicy,
});
