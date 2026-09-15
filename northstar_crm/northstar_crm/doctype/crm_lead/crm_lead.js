frappe.ui.form.on("CRM Lead", {
  refresh(frm) {
    if (!frm.is_new() && !["Converted", "Disqualified"].includes(frm.doc.status)) {
      frm.add_custom_button(__("Convert to Opportunity"), () => {
        frappe.confirm(__("Create or link the organization and contact, then create an opportunity?"), () => {
          frappe.call({
            method: "northstar_crm.api.convert_lead",
            type: "POST",
            args: { lead_name: frm.doc.name },
            freeze: true,
            callback: (response) => {
              if (response.message?.opportunity) {
                frappe.set_route("Form", "CRM Opportunity", response.message.opportunity);
              }
            },
          });
        });
      }, __("Actions"));
    }
  },
});
