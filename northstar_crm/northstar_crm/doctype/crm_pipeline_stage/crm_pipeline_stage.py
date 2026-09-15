import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class CRMPipelineStage(Document):
    def validate(self):
        if not 0 <= flt(self.probability) <= 100:
            frappe.throw(_("Probability must be between 0 and 100."))
        if cint(self.is_won) and cint(self.is_lost):
            frappe.throw(_("A pipeline stage cannot be both Won and Lost."))
        if cint(self.is_won):
            self.probability = 100
        if cint(self.is_lost):
            self.probability = 0
        if cint(self.is_won) and not cint(self.disabled) and frappe.db.exists(
            "CRM Pipeline Stage", {"is_won": 1, "disabled": 0, "name": ["!=", self.name]}
        ):
            frappe.throw(_("Only one active Won stage can be configured."))
        if cint(self.is_lost) and not cint(self.disabled) and frappe.db.exists(
            "CRM Pipeline Stage", {"is_lost": 1, "disabled": 0, "name": ["!=", self.name]}
        ):
            frappe.throw(_("Only one active Lost stage can be configured."))
