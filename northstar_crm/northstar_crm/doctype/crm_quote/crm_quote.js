frappe.ui.form.on("CRM Quote", {
  setup(frm) {
    frm.set_query("organization", () => ({
      query: "northstar_crm.queries.organization_for_opportunity",
      filters: { opportunity: frm.doc.opportunity },
    }));
  },
  refresh(frm) {
    if (frm.is_new() || frm.doc.docstatus !== 0) return;
    if (frm.doc.approval_status === "Pending" && (
      frappe.user.has_role("CRM Sales Manager") || frappe.user.has_role("System Manager")
    )) {
      frm.add_custom_button(__("Approve"), () => decideQuote(frm, "Approved"), __("Approval"));
      frm.add_custom_button(__("Reject"), () => showRejectionDialog(frm), __("Approval"));
    }
  },
});

frappe.ui.form.on("CRM Quote Item", {
  quantity(frm, cdt, cdn) { updateQuoteItem(frm, cdt, cdn); },
  rate(frm, cdt, cdn) { updateQuoteItem(frm, cdt, cdn); },
  discount_percent(frm, cdt, cdn) { updateQuoteItem(frm, cdt, cdn); },
});

async function decideQuote(frm, decision, rejectionReason = null) {
  await frappe.call({
    method: "northstar_crm.api.decide_quote",
    type: "POST",
    args: {
      quote_name: frm.doc.name,
      decision,
      rejection_reason: rejectionReason,
    },
    freeze: true,
  });
  frappe.show_alert({
    message: decision === "Approved" ? __("Quote approved") : __("Quote rejected"),
    indicator: decision === "Approved" ? "green" : "orange",
  });
  await frm.reload_doc();
}

function showRejectionDialog(frm) {
  const dialog = new frappe.ui.Dialog({
    title: __("Reject Quote"),
    fields: [
      {
        fieldname: "rejection_reason",
        fieldtype: "Small Text",
        label: __("Reason"),
        reqd: 1,
      },
    ],
    primary_action_label: __("Reject"),
    async primary_action(values) {
      await decideQuote(frm, "Rejected", values.rejection_reason);
      dialog.hide();
    },
  });
  dialog.show();
}

function updateQuoteItem(frm, cdt, cdn) {
  const row = locals[cdt][cdn];
  const netRate = toNumber(row.rate) * (1 - toNumber(row.discount_percent) / 100);
  frappe.model.set_value(cdt, cdn, "net_rate", netRate);
  frappe.model.set_value(cdt, cdn, "amount", toNumber(row.quantity) * netRate);
  frm.refresh_field("items");
}

function toNumber(value) {
  const number = Number.parseFloat(value);
  return Number.isFinite(number) ? number : 0;
}
