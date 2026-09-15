import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from northstar_crm.defaults import get_default_currency


class CRMOpportunity(Document):
    def before_validate(self):
        organization_currency = (
            frappe.db.get_value("CRM Organization", self.organization, "currency")
            if self.organization
            else None
        )
        self.currency = self.currency or organization_currency or get_default_currency()

    def validate(self):
        previous = self.get_doc_before_save()
        frappe.get_doc("CRM Organization", self.organization).check_permission("read")
        if (not previous or previous.opportunity_owner != self.opportunity_owner) and (
            self.opportunity_owner != frappe.session.user
            and not set(frappe.get_roles()) & {"CRM Sales Manager", "System Manager"}
        ):
            frappe.throw(
                _("Only a sales manager can assign an opportunity to another user."),
                frappe.PermissionError,
            )
        self._apply_stage_rules()
        self._calculate_item_amounts()
        self._validate_values()
        self._validate_stakeholders()
        self.weighted_amount = flt(self.amount) * flt(self.probability) / 100

    def before_save(self):
        previous = self.get_doc_before_save()
        if self.is_new() or not previous or previous.pipeline_stage != self.pipeline_stage:
            self.stage_entered_on = now_datetime()

    def _apply_stage_rules(self):
        stage = frappe.db.get_value(
            "CRM Pipeline Stage",
            self.pipeline_stage,
            ["probability", "is_won", "is_lost", "disabled"],
            as_dict=True,
        )
        if not stage:
            frappe.throw(_("Select a valid pipeline stage."))
        if stage.disabled:
            frappe.throw(_("The selected pipeline stage is disabled."))
        self.probability = stage.probability
        if stage.is_won:
            self.status = "Won"
            self.forecast_category = "Closed"
        elif stage.is_lost:
            self.status = "Lost"
            self.forecast_category = "Closed"
        else:
            if self.status in {"Won", "Lost"}:
                self.status = "Open"
            if self.forecast_category == "Closed":
                self.forecast_category = "Pipeline"
            self.loss_reason = None

    def _calculate_item_amounts(self):
        item_total = 0
        for item in self.items:
            if flt(item.quantity) <= 0 or flt(item.rate) < 0:
                frappe.throw(_("Item quantity must be positive and rate cannot be negative."))
            item.amount = flt(item.quantity) * flt(item.rate)
            item_total += item.amount
        if self.items:
            self.amount = item_total

    def _validate_values(self):
        if flt(self.amount) < 0 or flt(self.expected_recurring_revenue) < 0:
            frappe.throw(_("Opportunity values cannot be negative."))
        if not 0 <= flt(self.discount_requested) <= 100:
            frappe.throw(_("Requested discount must be between 0 and 100 percent."))
        if self.status == "Lost" and not self.loss_reason:
            frappe.throw(_("Enter a loss reason before closing an opportunity as lost."))

    def _validate_stakeholders(self):
        contacts = [row.contact for row in self.stakeholders if row.contact]
        if len(contacts) != len(set(contacts)):
            frappe.throw(_("A contact can only appear once in the stakeholder table."))
        stakeholder_organizations = {
            frappe.db.get_value("CRM Contact", contact, "organization") for contact in contacts
        }
        if self.organization and any(
            organization and organization != self.organization for organization in stakeholder_organizations
        ):
            frappe.throw(_("Every stakeholder must belong to the opportunity organization."))
        if self.primary_contact and self.organization:
            contact_org = frappe.db.get_value("CRM Contact", self.primary_contact, "organization")
            if contact_org and contact_org != self.organization:
                frappe.throw(_("The primary contact belongs to a different organization."))
