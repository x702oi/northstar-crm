from __future__ import annotations

import mimetypes

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from northstar_crm.defaults import get_default_document_classification


ALLOWED_REFERENCES = {"CRM Lead", "CRM Opportunity", "CRM Organization", "CRM Contact", "CRM Quote"}


class CRMDocumentAsset(Document):
    def before_validate(self):
        self.classification = self.classification or get_default_document_classification()

    def validate(self):
        if self.reference_doctype and self.reference_doctype not in ALLOWED_REFERENCES:
            frappe.throw(_("Unsupported CRM reference type."))
        if bool(self.reference_doctype) != bool(self.reference_name):
            frappe.throw(_("Set both reference type and reference, or leave both empty."))
        if self.reference_doctype:
            if not frappe.db.exists(self.reference_doctype, self.reference_name):
                frappe.throw(_("The referenced CRM record does not exist."))
            reference = frappe.get_doc(self.reference_doctype, self.reference_name)
            reference.check_permission("read")
            derived_organization = (
                reference.name
                if self.reference_doctype == "CRM Organization"
                else reference.get("organization")
            )
            if self.organization and derived_organization and self.organization != derived_organization:
                frappe.throw(_("Document organization must match the referenced record."))
            self.organization = derived_organization or self.organization
        elif self.organization:
            frappe.get_doc("CRM Organization", self.organization).check_permission("read")
        if self.legal_hold and self.retention_until:
            self.retention_until = None
        if self.retention_until and getdate(self.retention_until) < getdate():
            frappe.throw(_("Retention date cannot be in the past."))
        self._read_file_metadata()

    def _read_file_metadata(self):
        if not self.file_url:
            return
        file_doc = frappe.db.get_value(
            "File",
            {"file_url": self.file_url},
            ["name", "file_name", "file_size", "is_private"],
            as_dict=True,
        )
        if not file_doc:
            return
        frappe.get_doc("File", file_doc.name).check_permission("read")
        if frappe.db.get_single_value("CRM Settings", "require_private_documents") and not file_doc.is_private:
            frappe.throw(_("CRM document files must be private."))
        max_upload_size_mb = frappe.db.get_single_value("CRM Settings", "max_upload_size_mb") or 25
        if file_doc.file_size and file_doc.file_size > int(max_upload_size_mb) * 1024 * 1024:
            frappe.throw(
                _("CRM documents cannot exceed {0} MB.").format(max_upload_size_mb)
            )
        self.file_size_bytes = file_doc.file_size
        self.mime_type = mimetypes.guess_type(file_doc.file_name or self.file_url)[0] or "application/octet-stream"
