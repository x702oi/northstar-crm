import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime


class CRMConsent(Document):
    def validate(self):
        frappe.get_doc("CRM Contact", self.contact).check_permission("read")
        if self.evidence_asset:
            frappe.get_doc("CRM Document Asset", self.evidence_asset).check_permission("read")
        if self.valid_until and getdate(self.valid_until) < getdate(self.captured_on):
            frappe.throw(_("Consent expiry cannot be before its capture date."))
        if self.status == "Revoked" and not self.revoked_on:
            self.revoked_on = now_datetime()
        if self.status != "Revoked":
            self.revoked_on = None
        duplicate = frappe.db.exists(
            "CRM Consent",
            {
                "contact": self.contact,
                "purpose": self.purpose,
                "channel": self.channel,
                "status": ["in", ["Active", "Expiring"]],
                "name": ["!=", self.name],
            },
        )
        if duplicate and self.status in {"Active", "Expiring"}:
            frappe.throw(_("An active consent record already exists for this contact, purpose, and channel."))
