import frappe
from frappe import _
from frappe.model.document import Document


class CRMIntegrationEvent(Document):
    def validate(self):
        if self.direction == "Inbound" and not self.received_on:
            frappe.throw(_("Inbound events require a received timestamp."))
        if not isinstance(frappe.parse_json(self.payload_json), dict):
            frappe.throw(_("Integration payload must be a JSON object."))

