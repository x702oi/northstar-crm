frappe.ui.form.on("CRM Organization", {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button(__("Open Customer 360"), () => {
        frappe.set_route("sales-cockpit", { organization: frm.doc.name });
      });
    }
  },
});

