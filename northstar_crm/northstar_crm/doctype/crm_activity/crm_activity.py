import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime


ALLOWED_REFERENCES = {"CRM Lead", "CRM Opportunity", "CRM Organization", "CRM Contact", "CRM Quote"}


class CRMActivity(Document):
    def validate(self):
        if self.reference_doctype not in ALLOWED_REFERENCES:
            frappe.throw(_("Unsupported CRM reference type."))
        if not frappe.db.exists(self.reference_doctype, self.reference_name):
            frappe.throw(_("The referenced CRM record does not exist."))
        if cint(self.duration_minutes) < 0:
            frappe.throw(_("Duration cannot be negative."))
        if self.status == "Completed" and get_datetime(self.activity_datetime) > now_datetime():
            frappe.throw(_("A completed activity cannot be dated in the future."))
        self._derive_organization()

    def _derive_organization(self):
        reference = frappe.get_doc(self.reference_doctype, self.reference_name)
        reference.check_permission("read")
        if self.reference_doctype == "CRM Organization":
            derived_organization = reference.name
        else:
            derived_organization = reference.get("organization")
        if self.reference_doctype == "CRM Contact" and not self.contact:
            self.contact = reference.name
        if self.organization and derived_organization and self.organization != derived_organization:
            frappe.throw(_("Activity organization must match the referenced record."))
        self.organization = derived_organization or self.organization

        if self.contact and self.organization:
            contact_organization = frappe.db.get_value("CRM Contact", self.contact, "organization")
            if contact_organization and contact_organization != self.organization:
                frappe.throw(_("Activity contact must belong to the selected organization."))
