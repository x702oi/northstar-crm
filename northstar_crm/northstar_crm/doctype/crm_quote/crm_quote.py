import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, nowdate

from northstar_crm.defaults import get_default_currency


class CRMQuote(Document):
    def before_validate(self):
        opportunity_currency = (
            frappe.db.get_value("CRM Opportunity", self.opportunity, "currency")
            if self.opportunity
            else None
        )
        self.currency = self.currency or opportunity_currency or get_default_currency()

    def validate(self):
        previous = self.get_doc_before_save()
        self._validate_relationships()
        self._calculate_totals()
        self._set_approval_requirement(previous)
        self._validate_approval_transition(previous)
        if self.valid_until and getdate(self.valid_until) < getdate(nowdate()) and self.docstatus == 0:
            frappe.throw(_("Quote validity date cannot be in the past."))

    def before_submit(self):
        if self.approval_status == "Pending":
            frappe.throw(_("This quote requires manager approval before submission."))
        if self.approval_status == "Rejected":
            frappe.throw(_("A rejected quote cannot be submitted."))
        self.quote_status = "Approved"

    def on_submit(self):
        frappe.get_doc(
            {
                "doctype": "CRM Activity",
                "activity_type": "Proposal Sent",
                "subject": f"Quote {self.name} approved",
                "reference_doctype": "CRM Opportunity",
                "reference_name": self.opportunity,
                "organization": self.organization,
                "activity_datetime": now_datetime(),
                "owner_user": self.owner,
                "status": "Completed",
                "notes": f"Approved quote total: {self.currency} {self.grand_total}",
            }
        ).insert(ignore_permissions=True)

    def _validate_relationships(self):
        if not frappe.db.exists("CRM Opportunity", self.opportunity):
            frappe.throw(_("Select a valid opportunity."))
        opportunity = frappe.get_doc("CRM Opportunity", self.opportunity)
        opportunity.check_permission("read")
        if opportunity.organization != self.organization:
            frappe.throw(_("Quote organization must match the opportunity organization."))
        if self.primary_contact:
            contact_organization = frappe.db.get_value(
                "CRM Contact", self.primary_contact, "organization"
            )
            if contact_organization and contact_organization != self.organization:
                frappe.throw(_("Quote contact must belong to the selected organization."))
        if self.primary_contact and opportunity.primary_contact and self.primary_contact != opportunity.primary_contact:
            frappe.msgprint(_("The quote contact differs from the opportunity's primary contact."), alert=True)

    def _calculate_totals(self):
        if not self.items:
            frappe.throw(_("Add at least one quote item."))
        subtotal = 0
        for row in self.items:
            if flt(row.quantity) <= 0 or flt(row.rate) < 0:
                frappe.throw(_("Item quantity must be positive and rate cannot be negative."))
            if not 0 <= flt(row.discount_percent) <= 100:
                frappe.throw(_("Line discount must be between 0 and 100 percent."))
            row.net_rate = flt(row.rate) * (1 - flt(row.discount_percent) / 100)
            row.amount = flt(row.quantity) * row.net_rate
            subtotal += row.amount
        if not 0 <= flt(self.additional_discount_percent) <= 100:
            frappe.throw(_("Additional discount must be between 0 and 100 percent."))
        if not 0 <= flt(self.tax_percent) <= 100:
            frappe.throw(_("Tax percent must be between 0 and 100."))
        self.subtotal = subtotal
        self.discount_amount = subtotal * flt(self.additional_discount_percent) / 100
        taxable = subtotal - self.discount_amount
        self.tax_amount = taxable * flt(self.tax_percent) / 100
        self.grand_total = taxable + self.tax_amount

    def _set_approval_requirement(self, previous=None):
        threshold = frappe.db.get_single_value("CRM Settings", "discount_approval_threshold")
        threshold = 10 if threshold is None else flt(threshold)
        high_value_threshold = frappe.db.get_single_value("CRM Settings", "high_value_threshold")
        high_value_threshold = 500000 if high_value_threshold is None else flt(high_value_threshold)
        max_line_discount = max((flt(row.discount_percent) for row in self.items), default=0)
        requires_approval = (
            max(max_line_discount, flt(self.additional_discount_percent)) > threshold
            or (high_value_threshold > 0 and flt(self.grand_total) >= high_value_threshold)
        )
        signature = self._commercial_signature()
        commercial_terms_changed = not previous or previous.approval_signature != signature

        if requires_approval:
            if commercial_terms_changed or self.approval_status not in {"Pending", "Approved", "Rejected"}:
                self.approval_status = "Pending"
                self.requested_by = frappe.session.user
                self.approved_by = None
                self.approved_on = None
                self.rejection_reason = None
                self.quote_status = "Under Review"
        else:
            self.approval_status = "Not Required"
            self.requested_by = None
            self.approved_by = None
            self.approved_on = None
            self.rejection_reason = None
            if self.docstatus == 0:
                self.quote_status = "Draft"

        self.approval_signature = signature

    def _commercial_signature(self):
        payload = {
            "opportunity": self.opportunity,
            "organization": self.organization,
            "currency": self.currency,
            "valid_until": str(self.valid_until or ""),
            "additional_discount_percent": flt(self.additional_discount_percent),
            "tax_percent": flt(self.tax_percent),
            "payment_terms": self.payment_terms or "",
            "delivery_terms": self.delivery_terms or "",
            "assumptions": self.assumptions or "",
            "exclusions": self.exclusions or "",
            "items": [
                {
                    "service_name": row.service_name,
                    "description": row.description,
                    "quantity": flt(row.quantity),
                    "rate": flt(row.rate),
                    "discount_percent": flt(row.discount_percent),
                }
                for row in self.items
            ],
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _validate_approval_transition(self, previous=None):
        if self.approval_status == "Rejected" and not self.rejection_reason:
            frappe.throw(_("Enter a rejection reason."))
        if not previous or self.approval_status == previous.approval_status:
            return
        if self.approval_status in {"Approved", "Rejected"} and not (
            set(frappe.get_roles()) & {"CRM Sales Manager", "System Manager"}
        ):
            frappe.throw(_("Only a sales manager can approve or reject a quote."), frappe.PermissionError)
