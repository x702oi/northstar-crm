import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, validate_email_address


class CRMContact(Document):
    def validate(self):
        self.full_name = " ".join((self.full_name or "").split())
        if self.email:
            validate_email_address(self.email, throw=True)
        if not self.email and not self.mobile_no:
            frappe.throw(_("Enter at least an email address or mobile number."))
        if not 0 <= cint(self.relationship_strength) <= 100:
            frappe.throw(_("Relationship strength must be between 0 and 100."))
        if self.organization:
            frappe.get_doc("CRM Organization", self.organization).check_permission("read")

    def after_insert(self):
        self._enforce_single_primary_contact()

    def on_update(self):
        self._enforce_single_primary_contact()

    def _enforce_single_primary_contact(self):
        if self.is_primary and self.organization:
            other_primary_contacts = frappe.get_all(
                "CRM Contact",
                filters={"organization": self.organization, "is_primary": 1, "name": ["!=", self.name]},
                pluck="name",
            )
            for contact_name in other_primary_contacts:
                frappe.db.set_value(
                    "CRM Contact", contact_name, "is_primary", 0, update_modified=False
                )
