import frappe


def after_insert(doc, method=None):
    if not doc.file_url or not doc.extract_text:
        return
    frappe.db.set_value(doc.doctype, doc.name, "extraction_status", "Queued", update_modified=False)
    frappe.enqueue(
        "northstar_crm.services.document_intelligence.extract_document_text",
        queue="long",
        enqueue_after_commit=True,
        asset_name=doc.name,
    )

