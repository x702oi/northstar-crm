import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, validate_email_address

from northstar_crm.defaults import get_default_currency
from northstar_crm.services.scoring import calculate_lead_score, classify_lead_score


class CRMLead(Document):
    def before_validate(self):
        self.currency = self.currency or get_default_currency()

    def validate(self):
        previous = self.get_doc_before_save()
        self.lead_name = " ".join((self.lead_name or "").split())
        if self.email:
            validate_email_address(self.email, throw=True)
        if not self.email and not self.mobile_no:
            frappe.throw(_("Enter at least an email address or mobile number."))
        if flt(self.estimated_value) < 0:
            frappe.throw(_("Estimated value cannot be negative."))
        if not 0 <= cint(self.engagement_score) <= 15:
            frappe.throw(_("Engagement score must be between 0 and 15."))
        if self.status == "Qualified" and not self.business_need:
            frappe.throw(_("Describe the business need before qualifying this lead."))
        if (not previous or previous.lead_owner != self.lead_owner) and (
            self.lead_owner != frappe.session.user
            and not set(frappe.get_roles()) & {"CRM Sales Manager", "System Manager"}
        ):
            frappe.throw(_("Only a sales manager can assign a lead to another user."), frappe.PermissionError)
        score, factors = calculate_lead_score(self)
        self.lead_score = score
        self.score_breakdown = factors
        self.rating = classify_lead_score(score)
