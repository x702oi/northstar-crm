frappe.ui.form.on("CRM Opportunity", {
  setup(frm) {
    frm.set_query("primary_contact", () => ({ filters: { organization: frm.doc.organization } }));
  },
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button(__("Add Note"), () => {
      const dialog = new frappe.ui.Dialog({
        title: __("Add Opportunity Note"),
        fields: [
          { fieldname: "subject", fieldtype: "Data", label: __("Subject"), reqd: 1 },
          { fieldname: "notes", fieldtype: "Text Editor", label: __("Notes"), reqd: 1 },
        ],
        primary_action_label: __("Save Note"),
        primary_action(values) {
          frappe.call({
            method: "northstar_crm.api.add_note",
            type: "POST",
            args: { reference_doctype: frm.doctype, reference_name: frm.doc.name, ...values },
            callback: () => {
              dialog.hide();
              frappe.show_alert({ message: __("Note added"), indicator: "green" });
            },
          });
        },
      });
      dialog.show();
    }, __("Activity"));
  },
});

frappe.ui.form.on("CRM Opportunity Item", {
  quantity(frm, cdt, cdn) { calculate_item(frm, cdt, cdn); },
  rate(frm, cdt, cdn) { calculate_item(frm, cdt, cdn); },
});

function calculate_item(frm, cdt, cdn) {
  const row = locals[cdt][cdn];
  frappe.model.set_value(cdt, cdn, "amount", toNumber(row.quantity) * toNumber(row.rate));
  frm.refresh_field("items");
}

function toNumber(value) {
  const number = Number.parseFloat(value);
  return Number.isFinite(number) ? number : 0;
}
