// Copyright (c) 2026, SRIAAS and contributors
// For license information, please see license.txt

frappe.ui.form.on("SRIAAS Role Permission Settings", {
  refresh(frm) {
    configure_number_privacy_grid(frm);
    load_number_privacy_control(frm);
    configure_settings_ui(frm);
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

    const testAccessButton = frm.add_custom_button(__("Test Current User Access"), () => {
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

    const resetRolesButton = frm.add_custom_button(__("Reset Default CRM Lead Roles"), () => {
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
    // Place these existing actions with the role rules; retain their callbacks.
    const actions = frm.fields_dict.role_access_actions?.$wrapper;
    if (actions) {
      actions.empty();
      $("<div>", {class: "role-settings-actions"})
        .append(testAccessButton, resetRolesButton).appendTo(actions);
    }
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
  configure_role_dropdown(grid);
  grid.reset_grid();
}

// Keep the native Link menu and its keyboard/click handlers, but position it
// outside the scrolling grid's clipping area while it is open.
function configure_role_dropdown(grid) {
  grid.wrapper.on("awesomplete-open", 'input[data-target="Role"]', function () {
    const input = this;
    const menu = input.closest(".awesomplete")?.querySelector("ul");
    if (!menu) return;
    grid.__role_dropdown_cleanup?.();
    const originalStyle = menu.getAttribute("style");
    const position = () => {
      if (!input.isConnected || menu.hidden) {
        cleanup();
        return;
      }
      const rect = input.getBoundingClientRect();
      const below = window.innerHeight - rect.bottom - 12;
      const above = rect.top - 12;
      const openAbove = below < 180 && above > below;
      const available = Math.max(0, openAbove ? above : below);
      const width = Math.min(rect.width, window.innerWidth - 24);
      Object.assign(menu.style, {
        position: "fixed",
        left: `${Math.max(12, Math.min(rect.left, window.innerWidth - width - 12))}px`,
        top: openAbove ? "auto" : `${rect.bottom + 4}px`,
        bottom: openAbove ? `${window.innerHeight - rect.top + 4}px` : "auto",
        width: `${width}px`,
        minWidth: "0",
        maxHeight: `${Math.min(280, available)}px`,
        overflowY: "auto",
        margin: "0",
        zIndex: "1100"
      });
    };
    const onScroll = (event) => {
      // Scrolling suggestions must not reposition or close their own menu.
      if (!menu.contains(event.target)) position();
    };
    const cleanup = () => {
      document.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", position);
      input.removeEventListener("awesomplete-close", cleanup);
      if (originalStyle === null) menu.removeAttribute("style");
      else menu.setAttribute("style", originalStyle);
      if (grid.__role_dropdown_cleanup === cleanup) grid.__role_dropdown_cleanup = null;
    };
    grid.__role_dropdown_cleanup = cleanup;
    input.addEventListener("awesomplete-close", cleanup);
    document.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", position);
    position();
  });
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
  wrapper.empty().addClass("role-settings-privacy-control");
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
  const explanation = $("<details>", {class: "role-settings-guide"}).appendTo(wrapper);
  $("<summary>", {text: __("About this setting")}).appendTo(explanation);
  $("<p>", {
    class: "text-muted small mt-2",
    text: __("When active, supported screens mask existing numbers unless a role grants View Full. Turning it off restores normal access on those screens, subject to document permissions. Appointment patient lookups and support customer lookups keep their existing protection. Supported Vobiz call and AI workflows apply the same saved role policy.")
  }).appendTo(explanation);
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

// Presentation only: use the existing child fields, native grid filtering and
// normal add-row/model events. Save and server permission checks are unchanged.
function configure_settings_ui(frm) {
  frm.wrapper.addClass("role-permission-settings-ui");
  if (!document.getElementById("role-settings-ui-style")) {
    $("<style>", {id: "role-settings-ui-style", text: `
      .role-permission-settings-ui .role-settings-toolbar {
        display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin: 8px 0 12px;
      }
      .role-settings-toolbar .role-settings-search { width: 260px; max-width: 100%; }
      .role-settings-toolbar .role-settings-filter { width: 200px; max-width: 100%; }
      .role-settings-toolbar .role-settings-add { margin-left: auto; }
      .role-permission-settings-ui .role-settings-guide {
        border: 1px solid var(--border-color); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px;
      }
      .role-settings-guide summary { cursor: pointer; font-weight: 500; }
      .role-settings-guide .alert { margin-top: 10px; margin-bottom: 0 !important; }
      .role-settings-privacy-control { border: 1px solid var(--border-color); border-radius: 8px; padding: 14px; }
      .role-permission-settings-ui .role-settings-actions,
      .role-permission-settings-ui .role-settings-display-example {
        display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin: 12px 0;
      }
      .role-permission-settings-ui .role-settings-display-example {
        border: 1px solid var(--border-color); border-radius: 8px; padding: 12px;
        font-size: var(--text-sm);
      }
      .role-settings-example-number {
        padding: 4px 12px; background: var(--control-bg); border-radius: 6px;
        font-variant-numeric: tabular-nums;
      }
      .role-permission-settings-ui .grid-heading-row .static-area { white-space: normal; }
      .role-permission-settings-ui .number-privacy-grid .grid-row > .data-row > [data-fieldname="role"] {
        position: sticky; left: 0; z-index: 2; background: var(--fg-color);
      }
    `}).appendTo(document.head);
  }
  const tables = [
    ["doctype_configs", "ref_doctype", "Search DocType", "Add Rule", []],
    ["locked_fields", "fieldname", "Search fields", "Add Rule", ["ref_doctype"]],
    ["roles", "role", "Search roles", "Add Role", ["ref_doctype", "role_type"]],
    ["privacy_number_roles", "role", "Search roles", "Add Role", []]
  ];
  for (const [fieldname, searchField, placeholder, addLabel, filters] of tables) {
    const control = frm.fields_dict[fieldname];
    const grid = control?.grid;
    if (!grid) continue;
    if (!grid.__settings_toolbar) {
      const toolbar = $("<div>", {class: "role-settings-toolbar"}).insertBefore(grid.wrapper);
      const applyFilter = (field, value) => {
        const df = grid.docfields.find(d => d.fieldname === field);
        if (!df) return;
        if (value) grid.filter[field] = {df, value};
        else delete grid.filter[field];
        grid.grid_pagination.page_index = 1;
        grid.refresh();
      };
      $("<input>", {
        type: "search", class: "form-control input-sm role-settings-search",
        placeholder: __(placeholder), "aria-label": __(placeholder)
      }).on("input", function () { applyFilter(searchField, this.value.trim()); }).appendTo(toolbar);
      for (const filterField of filters) {
        const df = grid.docfields.find(d => d.fieldname === filterField);
        const select = $("<select>", {
          class: "form-control input-sm role-settings-filter", "aria-label": __(df.label)
        }).appendTo(toolbar);
        select.append($("<option>", {value: "", text: __("All {0}", [__(df.label)])}));
        select.on("change", function () { applyFilter(filterField, this.value); });
        select.data("filter-field", filterField);
      }
      const add = $("<button>", {
        type: "button", class: "btn btn-sm btn-primary role-settings-add", text: __(addLabel)
      }).appendTo(toolbar).on("click", () => open_settings_row_dialog(frm, grid, addLabel));
      grid.__settings_toolbar = {toolbar, add};
    }
    const {toolbar, add} = grid.__settings_toolbar;
    add.toggle(grid.is_editable());
    toolbar.find("select").each(function () {
      const select = $(this), field = select.data("filter-field"), previous = select.val();
      const df = grid.docfields.find(d => d.fieldname === field);
      const values = df.fieldtype === "Select" ? df.options.split("\n").filter(Boolean)
        : [...new Set((frm.doc[fieldname] || []).map(row => row[field]).filter(Boolean))].sort();
      select.find("option:not(:first)").remove();
      values.forEach(value => select.append($("<option>", {value, text: value})));
      select.val(values.includes(previous) ? previous : "");
      if (previous && !values.includes(previous)) {
        delete grid.filter[field];
        grid.refresh();
      }
    });
  }
}

function open_settings_row_dialog(frm, grid, title) {
  if (!grid.is_editable()) return;
  const fields = grid.docfields.filter(df => !frappe.model.no_value_type.includes(df.fieldtype)
    && !df.hidden && !df.read_only).map(df => {
      const field = {
        fieldname: df.fieldname, label: df.label, fieldtype: df.fieldtype,
        options: df.options, reqd: df.reqd, default: df.default, description: df.description
      };
      if (df.fieldtype === "Link" && df.options === "DocType") {
        field.get_query = () => ({filters: {istable: 0}});
      }
      return field;
    });
  const dialog = new frappe.ui.Dialog({
    title: __(title), fields,
    primary_action_label: __("Add"),
    async primary_action(values) {
      if (!grid.is_editable()) return;
      const row = grid.add_new_row(null, null, false);
      if (!row) return;
      dialog.get_primary_btn().prop("disabled", true);
      try {
        await frappe.model.set_value(row.doctype, row.name, values);
        frm.dirty();
        grid.filter = {};
        grid.__settings_toolbar.toolbar.find("input, select").val("");
        frm.refresh_field(grid.df.fieldname);
        configure_settings_ui(frm);
        dialog.hide();
      } finally {
        dialog.get_primary_btn().prop("disabled", false);
      }
    }
  });
  dialog.show();
}
