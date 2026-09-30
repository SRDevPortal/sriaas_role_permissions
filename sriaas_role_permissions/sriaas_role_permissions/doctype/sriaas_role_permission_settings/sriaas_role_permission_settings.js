// Copyright (c) 2026, SRIAAS and contributors
// For license information, please see license.txt

frappe.ui.form.on("SRIAAS Role Permission Settings", {
  refresh(frm) {
    configure_number_privacy_grid(frm);
    frm.set_query("ref_doctype", "roles", () => ({
      filters: {
        istable: 0,
      },
    }));
    frm.set_query("ref_doctype", "doctype_configs", () => ({
      filters: {
        istable: 0,
      },
    }));
    frm.set_query("pipeline_doctype", "doctype_configs", () => ({
      filters: {
        istable: 0,
      },
    }));
    frm.set_query("ref_doctype", "locked_fields", () => ({
      filters: {
        istable: 0,
      },
    }));

    frm.add_custom_button(__("Test Current User Access"), () => {
      frappe.prompt(
        [
          {
            fieldname: "ref_doctype",
            label: __("DocType"),
            fieldtype: "Link",
            options: "DocType",
            default: "CRM Lead",
            reqd: 1,
            get_query: () => ({
              filters: {
                istable: 0,
              },
            }),
          },
        ],
        (values) => {
          frappe.call({
            method: "sriaas_role_permissions.api.roles.test_current_user_access",
            args: {
              ref_doctype: values.ref_doctype,
            },
            callback(r) {
              const data = r.message || {};
              frappe.msgprint({
                title: __("Current User Access"),
                indicator: data.is_privileged ? "green" : "blue",
                message: `
                  <div>
                    <p><b>${__("DocType")}:</b> ${frappe.utils.escape_html(data.ref_doctype || "")}</p>
                    <p><b>${__("Privileged")}:</b> ${data.is_privileged ? __("Yes") : __("No")}</p>
                    <p><b>${__("Team Leader Role")}:</b> ${data.has_team_leader_role ? __("Yes") : __("No")}</p>
                    <p><b>${__("Agent Role")}:</b> ${data.has_agent_role ? __("Yes") : __("No")}</p>
                    <p><b>${__("Team Leader Roles")}:</b> ${frappe.utils.escape_html((data.team_leader_roles || []).join(", ") || "-")}</p>
                    <p><b>${__("Agent Roles")}:</b> ${frappe.utils.escape_html((data.agent_roles || []).join(", ") || "-")}</p>
                    <p><b>${__("Privileged Roles")}:</b> ${frappe.utils.escape_html((data.privileged_roles || []).join(", ") || "-")}</p>
                  </div>
                `,
              });
            },
          });
        },
        __("Test Access"),
        __("Test")
      );
    });

    frm.add_custom_button(__("Reset Default CRM Lead Roles"), () => {
      frappe.confirm(
        __("This will add or re-enable the default CRM Lead role rules. Existing custom rows will not be removed."),
        () => {
          frappe.call({
            method: "sriaas_role_permissions.api.roles.reset_default_crm_lead_roles",
            freeze: true,
            callback(r) {
              const data = r.message || {};
              frm.reload_doc();
              frappe.msgprint({
                title: __("Default Roles Reset"),
                indicator: "green",
                message: `
	                  <p><b>${__("Added")}:</b> ${(data.added || []).length}</p>
	                  <p><b>${__("Re-enabled")}:</b> ${(data.enabled || []).length}</p>
	                  <p><b>${__("DocType Rules Added")}:</b> ${(data.config_added || []).length}</p>
	                  <p><b>${__("Locked Fields Added")}:</b> ${(data.locked_added || []).length}</p>
	                  <p><b>${__("Skipped")}:</b> ${(data.skipped || []).length}</p>
                `,
              });
            },
          });
        }
      );
    });
  },
});

// This settings matrix always shows every permission, including for users with
// an older saved grid layout. Scope layout changes to this grid instance only.
function configure_number_privacy_grid(frm) {
  const grid = frm.fields_dict.privacy_number_roles?.grid;
  if (!grid || grid.__number_privacy_layout) return;
  grid.__number_privacy_layout = true;
  grid.editable_fields = [
    {fieldname: "role", columns: 3},
    {fieldname: "view_full", columns: 1},
    {fieldname: "edit_original", columns: 2},
    {fieldname: "enter_new_numbers", columns: 2},
    {fieldname: "add_contact_numbers", columns: 1},
    {fieldname: "change_primary_number", columns: 1}
  ];
  grid.setup_user_defined_columns = function () { this.user_defined_columns = []; };
  grid.wrapper.addClass("number-privacy-grid");
  if (!document.getElementById("number-privacy-grid-style")) {
    $("<style>", {id: "number-privacy-grid-style", text: `
      .number-privacy-grid { overflow-x: auto; }
      .number-privacy-grid .form-grid { min-width: 1100px; }
      .number-privacy-grid .grid-heading-row .static-area {
        white-space: normal; overflow: visible; text-overflow: clip;
      }
    `}).appendTo(document.head);
  }
  grid.reset_grid();
}
