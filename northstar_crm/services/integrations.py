from __future__ import annotations

import frappe
from frappe.utils import now_datetime


def process_inbound_event(event_name: str):
    event = frappe.get_doc("CRM Integration Event", event_name)
    if event.status in {"Applied", "Ignored"}:
        return {"event": event.name, "status": event.status, "idempotent": True}

    event.db_set({"status": "Processing", "last_attempt_on": now_datetime()})
    try:
        payload = frappe.parse_json(event.payload_json) or {}
        if event.event_type == "lead.created":
            reference = _apply_lead(payload)
        elif event.event_type == "activity.logged":
            reference = _apply_activity(payload)
        else:
            event.db_set({"status": "Manual Review", "last_error": "Unsupported event type"})
            return {"event": event.name, "status": "Manual Review"}

        event.db_set(
            {
                "status": "Applied",
                "reference_doctype": reference.doctype,
                "reference_name": reference.name,
                "processed_on": now_datetime(),
                "last_error": None,
            }
        )
        return {"event": event.name, "status": "Applied", "reference": reference.name}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Northstar CRM integration processing")
        event.db_set(
            {
                "status": "Failed",
                "retry_count": int(event.retry_count or 0) + 1,
                "last_error": "Processing failed. Ask an administrator to review the Error Log.",
            }
        )
        raise


def _apply_lead(payload: dict):
    return frappe.get_doc(
        {
            "doctype": "CRM Lead",
            "lead_name": payload.get("lead_name"),
            "organization_name": payload.get("organization_name"),
            "email": payload.get("email"),
            "mobile_no": payload.get("mobile_no"),
            "source": payload.get("source") or "Other",
            "business_need": payload.get("business_need"),
            "estimated_value": payload.get("estimated_value"),
            "currency": payload.get("currency") or "SAR",
            "lead_owner": payload.get("lead_owner") or "Administrator",
            "status": "New",
        }
    ).insert(ignore_permissions=True)


def _apply_activity(payload: dict):
    return frappe.get_doc(
        {
            "doctype": "CRM Activity",
            "activity_type": payload.get("activity_type"),
            "subject": payload.get("subject"),
            "reference_doctype": payload.get("reference_doctype"),
            "reference_name": payload.get("reference_name"),
            "activity_datetime": payload.get("activity_datetime") or now_datetime(),
            "owner_user": payload.get("owner_user") or "Administrator",
            "status": payload.get("status") or "Completed",
            "notes": payload.get("notes"),
            "external_event_id": payload.get("external_event_id"),
        }
    ).insert(ignore_permissions=True)
