import frappe


def after_insert(doc, method=None):
    if doc.direction != "Inbound" or doc.status != "Received":
        return
    frappe.enqueue(
        "northstar_crm.services.integrations.process_inbound_event",
        queue="default",
        enqueue_after_commit=True,
        event_name=doc.name,
    )

