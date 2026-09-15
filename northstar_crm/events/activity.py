import frappe
from frappe.utils import get_datetime


def after_insert(doc, method=None):
    if doc.status != "Completed":
        return
    if doc.reference_doctype in {"CRM Lead", "CRM Opportunity", "CRM Organization"} and (
        doc.reference_name and frappe.db.exists(doc.reference_doctype, doc.reference_name)
    ):
        _set_latest_activity(doc.reference_doctype, doc.reference_name, doc)

    if doc.organization and frappe.db.exists("CRM Organization", doc.organization):
        _set_latest_activity("CRM Organization", doc.organization, doc)

    if doc.contact and frappe.db.exists("CRM Contact", doc.contact):
        current = frappe.db.get_value("CRM Contact", doc.contact, "last_contacted_on")
        if not current or get_datetime(doc.activity_datetime) >= get_datetime(current):
            frappe.db.set_value(
                "CRM Contact",
                doc.contact,
                "last_contacted_on",
                doc.activity_datetime,
                update_modified=False,
            )

    if doc.reference_doctype == "CRM Lead":
        frappe.enqueue(
            "northstar_crm.services.scoring.recalculate_lead_score",
            queue="short",
            enqueue_after_commit=True,
            lead_name=doc.reference_name,
        )


def _set_latest_activity(doctype, name, activity):
    current = frappe.db.get_value(doctype, name, "last_activity_on")
    if current and get_datetime(activity.activity_datetime) < get_datetime(current):
        return
    frappe.db.set_value(
        doctype,
        name,
        {"last_activity_on": activity.activity_datetime, "last_activity_type": activity.activity_type},
        update_modified=False,
    )
