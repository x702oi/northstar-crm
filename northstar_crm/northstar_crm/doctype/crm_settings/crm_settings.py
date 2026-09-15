import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class CRMSettings(Document):
    def validate(self):
        if cint(self.stale_opportunity_days) < 1:
            frappe.throw(_("Stale opportunity days must be at least 1."))
        if flt(self.high_value_threshold) < 0:
            frappe.throw(_("High value threshold cannot be negative."))
        if not 0 <= flt(self.discount_approval_threshold) <= 100:
            frappe.throw(_("Discount approval threshold must be between 0 and 100 percent."))
        if cint(self.max_upload_size_mb) < 1:
            frappe.throw(_("Maximum upload size must be at least 1 MB."))
        if cint(self.max_extracted_text_chars) < 1000:
            frappe.throw(_("Maximum extracted text must be at least 1,000 characters."))
        if not 0 <= cint(self.warm_lead_score) < cint(self.hot_lead_score) <= 100:
            frappe.throw(_("Lead thresholds must satisfy 0 ≤ warm < hot ≤ 100."))
