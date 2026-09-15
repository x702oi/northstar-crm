import frappe


def get_default_currency():
    return (
        frappe.db.get_single_value("CRM Settings", "default_currency")
        or frappe.db.get_single_value("Global Defaults", "default_currency")
        or "SAR"
    )


def get_default_document_classification():
    return (
        frappe.db.get_single_value("CRM Settings", "default_document_classification")
        or "Confidential"
    )
