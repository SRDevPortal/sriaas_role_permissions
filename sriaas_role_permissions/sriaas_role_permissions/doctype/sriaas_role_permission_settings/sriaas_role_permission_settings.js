// Copyright (c) 2026, SRIAAS and contributors
// For license information, please see license.txt

frappe.ui.form.on("SRIAAS Role Permission Settings", {
  refresh(frm) {
    configure_number_privacy_grid(frm);
    load_number_privacy_control(frm);
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

// This control updates the existing site switch. The form Save button continues
// to save role rules; it never silently activates or disables privacy.
function load_number_privacy_control(frm) {
  const wrapper = frm.fields_dict.privacy_number_control?.$wrapper;
  if (!wrapper) return;
  wrapper.empty().text(__("Loading privacy status…"));
  frappe.call({
    method: "sriaas_role_permissions.customer_number_privacy.get_status",
    callback(r) {
      render_number_privacy_control(frm, r.message);
    },
    error() {
      wrapper.empty().text(__("Privacy status unavailable. Reload to try again."));
    }
  });
}

function render_number_privacy_control(frm, status) {
  const wrapper = frm.fields_dict.privacy_number_control?.$wrapper;
  if (!wrapper || !status) return;
  wrapper.empty();
  const label = !status.installed ? __("Privacy Shield is not installed")
    : status.enabled ? __("Active") : __("Inactive");
  $("<span>", {
    class: "indicator-pill " + (status.installed && status.enabled ? "green" : "orange"),
    text: label
  }).appendTo(wrapper);
  const row = $("<div>", {class: "mt-3 mb-2"}).appendTo(wrapper);
  const toggleLabel = $("<label>").appendTo(row);
  const toggle = $("<input>", {type: "checkbox", class: "mr-2"})
    .prop("checked", Boolean(status.enabled)).appendTo(toggleLabel);
  $("<span>", {text: __("Enable Customer Number Privacy")}).appendTo(toggleLabel);
  const apply = $("<button>", {
    type: "button", class: "btn btn-sm btn-primary ml-3",
    text: __("Apply Privacy Setting")
  }).prop("disabled", true).appendTo(row);
  const note = $("<p>", {class: "text-muted small"}).appendTo(wrapper);
  const canWrite = Boolean(frm.perm?.[0]?.write);
  toggle.prop("disabled", !canWrite || (!status.installed && !status.enabled));
  function update_pending() {
    const changed = toggle.prop("checked") !== Boolean(status.enabled);
    apply.prop("disabled", !canWrite || !changed);
    note.text(changed ? __("Pending change. Click Apply Privacy Setting to activate it.")
      : __("Role rules use Save. This switch uses Apply Privacy Setting. Refresh open customer pages after changing it."));
  }
  toggle.on("change", update_pending);
  update_pending();
  $("<p>", {
    class: "text-muted small",
    text: __("When active, supported screens mask existing numbers unless a role grants View Full. Turning it off restores normal access on those screens, subject to document permissions. Appointment patient lookups and support customer lookups keep their existing protection. Supported Vobiz call and AI workflows apply the same saved role policy.")
  }).appendTo(wrapper);
  apply.on("click", () => {
    if (frm.is_dirty()) {
      frappe.msgprint(__("Save your role-rule changes before applying the privacy setting."));
      return;
    }
    const desired = toggle.prop("checked");
    const message = desired
      ? __("Enable Customer Number Privacy using the saved role rules?")
      : __("Disable Customer Number Privacy? Users may see full numbers on switch-controlled screens when document permissions allow.");
    frappe.confirm(message, () => {
      apply.prop("disabled", true);
      toggle.prop("disabled", true);
      frappe.call({
        method: "sriaas_role_permissions.customer_number_privacy.set_enabled",
        type: "POST",
        args: {enabled: Number(desired), expected_enabled: Number(Boolean(status.enabled))},
        freeze: true,
        callback() {
          frappe.show_alert({message: __("Privacy setting updated. Refresh open customer pages."), indicator: "green"});
          frm.reload_doc();
        },
        error() { load_number_privacy_control(frm); }
      });
    });
  });
}
