import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, validate_email_address

from northstar_crm.defaults import get_default_currency


class CRMOrganization(Document):
    def before_validate(self):
        self.currency = self.currency or get_default_currency()

    def validate(self):
        previous = self.get_doc_before_save()
        self.organization_name = " ".join((self.organization_name or "").split())
        if self.primary_email:
            validate_email_address(self.primary_email, throw=True)
        if self.website and not re.match(r"^https?://", self.website, flags=re.I):
            self.website = f"https://{self.website}"
        if flt(self.annual_revenue) < 0 or cint(self.employee_count) < 0:
            frappe.throw(_("Revenue and employee count cannot be negative."))
        if not 0 <= cint(self.health_score) <= 100:
            frappe.throw(_("Relationship health must be between 0 and 100."))
        if (not previous or previous.account_manager != self.account_manager) and (
            self.account_manager != frappe.session.user
            and not set(frappe.get_roles()) & {"CRM Sales Manager", "System Manager"}
        ):
            frappe.throw(
                _("Only a sales manager can assign an organization to another user."),
                frappe.PermissionError,
            )
