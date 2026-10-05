const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

class Element {
  constructor(tag, props = {}) { this.tag = tag; this.attrs = {...props}; this.children = []; this.handlers = {}; }
  empty() { this.children = []; return this; }
  text(value) { this.attrs.text = value; return this; }
  appendTo(parent) { parent.children.push(this); return this; }
  prop(key, value) { if (arguments.length === 1) return this.attrs[key]; this.attrs[key] = value; return this; }
  on(event, callback) { this.handlers[event] = callback; return this; }
}
const calls = [], messages = [], confirmations = [];
const context = {
  $: (tag, props) => new Element(tag, props),
  __: text => text,
  frappe: {
    ui: {form: {on() {}}},
    call: opts => calls.push(opts),
    msgprint: text => messages.push(text),
    confirm: (text, callback) => { confirmations.push(text); callback(); },
    show_alert() {}
  }
};
vm.createContext(context);
const source = path.join(__dirname, "../sriaas_role_permissions/doctype/sriaas_role_permission_settings/sriaas_role_permission_settings.js");
vm.runInContext(fs.readFileSync(source, "utf8"), context);

function render(enabled, write = true, dirty = false) {
  const wrapper = new Element("root");
  const frm = {fields_dict: {privacy_number_control: {$wrapper: wrapper}},
    perm: [{write: Number(write)}], is_dirty: () => dirty, reload_doc() {}};
  context.render_number_privacy_control(frm, {enabled, installed: true});
  const row = wrapper.children[1], checkbox = row.children[0].children[0], button = row.children[1];
  return {frm, wrapper, checkbox, button};
}
let ui = render(false);
assert.equal(ui.wrapper.children[0].attrs.text, "Inactive");
assert.equal(ui.button.prop("disabled"), true);
ui.checkbox.prop("checked", true);
ui.checkbox.handlers.change();
assert.equal(calls.length, 0, "Changing checkbox must not change the saved policy");
assert.equal(ui.button.prop("disabled"), false);
ui.button.handlers.click();
assert.equal(calls.at(-1).type, "POST");
assert.equal(calls.at(-1).args.enabled, 1);
assert.equal(calls.at(-1).args.expected_enabled, 0);

ui = render(true);
assert.equal(ui.wrapper.children[0].attrs.text, "Active");
ui.checkbox.prop("checked", false);
ui.checkbox.handlers.change();
ui.button.handlers.click();
assert.equal(calls.at(-1).args.enabled, 0);
assert.match(confirmations.at(-1), /full numbers/);

ui = render(false, false);
assert.equal(ui.checkbox.prop("disabled"), true);
assert.equal(ui.button.prop("disabled"), true);

ui = render(false, true, true);
ui.checkbox.prop("checked", true);
ui.checkbox.handlers.change();
const before = calls.length;
ui.button.handlers.click();
assert.equal(calls.length, before);
assert.match(messages.at(-1), /Save your role-rule changes/);

calls.length = 0;
context.load_number_privacy_control(ui.frm);
calls[0].error();
assert.match(ui.wrapper.attrs.text, /unavailable/);
console.log("Privacy UI checks passed: status, pending changes, enable, disable, read-only, unsaved roles, error state.");
