from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, now_datetime, nowdate

from northstar_crm.services.forecasting import get_pipeline_forecast


def has_app_permission():
    return bool(
        set(frappe.get_roles())
        & {"System Manager", "CRM Sales User", "CRM Sales Manager", "CRM Analyst", "CRM Compliance Manager"}
    )


def _payload(value):
    try:
        parsed = json.loads(value) if isinstance(value, str) else value or {}
    except (TypeError, ValueError):
        frappe.throw(_("Payload must be valid JSON."))
    if not isinstance(parsed, dict):
        frappe.throw(_("Payload must be a JSON object."))
    return parsed


def _require_read(doctype):
    if not frappe.has_permission(doctype, ptype="read"):
        frappe.throw(_("You are not permitted to read {0}.").format(doctype), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def get_sales_cockpit(period: str = "quarter"):
    _require_read("CRM Opportunity")
    if period not in {"month", "quarter"}:
        frappe.throw(_("Period must be month or quarter."))

    forecast = get_pipeline_forecast(period)
    stages = frappe.get_list(
        "CRM Pipeline Stage",
        filters={"disabled": 0},
        fields=["name", "stage_name", "sequence", "probability", "color", "is_won", "is_lost"],
        order_by="sequence asc",
    )
    opportunities = frappe.get_list(
        "CRM Opportunity",
        filters={"status": ["in", ["Open", "On Hold"]]},
        fields=[
            "name",
            "opportunity_name",
            "organization",
            "pipeline_stage",
            "currency",
            "amount",
            "weighted_amount",
            "probability",
            "expected_close_date",
            "opportunity_owner",
            "is_stale",
        ],
        order_by="expected_close_date asc, modified desc",
        limit_page_length=100,
    )
    activities = frappe.get_list(
        "CRM Activity",
        filters={"status": ["in", ["Open", "Scheduled"]]},
        fields=["name", "activity_type", "subject", "activity_datetime", "reference_doctype", "reference_name", "priority", "owner_user"],
        order_by="activity_datetime asc",
        limit_page_length=20,
    )
    overdue = sum(
        1
        for item in activities
        if item.activity_datetime and get_datetime(item.activity_datetime) < now_datetime()
    )
    return {
        "forecast": forecast,
        "currency": frappe.db.get_single_value("CRM Settings", "default_currency") or "SAR",
        "stages": stages,
        "opportunities": opportunities,
        "activities": activities,
        "overdue_count": overdue,
    }


@frappe.whitelist(methods=["POST"])
def create_lead(data):
    values = _payload(data)
    requested_owner = values.get("lead_owner")
    if requested_owner and requested_owner != frappe.session.user and not (
        set(frappe.get_roles()) & {"CRM Sales Manager", "System Manager"}
    ):
        frappe.throw(_("Only a sales manager can assign a new lead to another user."), frappe.PermissionError)
    lead = frappe.new_doc("CRM Lead")
    lead.update(
        {
            "lead_name": values.get("lead_name"),
            "organization_name": values.get("organization_name"),
            "email": values.get("email"),
            "mobile_no": values.get("mobile_no"),
            "source": values.get("source") or "Website",
            "industry": values.get("industry"),
            "business_need": values.get("business_need"),
            "estimated_value": flt(values.get("estimated_value")),
            "target_close_date": values.get("target_close_date"),
            "lead_owner": values.get("lead_owner") or frappe.session.user,
            "status": "New",
        }
    )
    lead.insert()
    return {"name": lead.name, "lead_score": lead.lead_score, "status": lead.status}


@frappe.whitelist(methods=["POST"])
def convert_lead(lead_name: str, organization_name: str | None = None, opportunity_name: str | None = None):
    lead = frappe.get_doc("CRM Lead", lead_name)
    lead.check_permission("write")
    if lead.status == "Converted":
        frappe.throw(_("This lead has already been converted."))
    if lead.status == "Disqualified":
        frappe.throw(_("A disqualified lead cannot be converted."))

    organization = None
    company_name = organization_name or lead.organization_name or f"{lead.lead_name} (Individual)"
    organization = frappe.db.get_value("CRM Organization", {"organization_name": company_name}, "name")
    if organization:
        frappe.get_doc("CRM Organization", organization).check_permission("read")
    else:
        organization_doc = frappe.get_doc(
            {
                "doctype": "CRM Organization",
                "organization_name": company_name,
                "industry": lead.industry,
                "account_manager": lead.lead_owner,
                "lifecycle_stage": "Prospect",
                "currency": lead.currency,
            }
        ).insert()
        organization = organization_doc.name

    contact = None
    if lead.email or lead.mobile_no:
        contact = (
            frappe.db.get_value(
                "CRM Contact", {"email": lead.email, "organization": organization}, "name"
            )
            if lead.email
            else None
        )
        if contact:
            contact_doc = frappe.get_doc("CRM Contact", contact)
            contact_doc.check_permission("read")
        else:
            contact_doc = frappe.get_doc(
                {
                    "doctype": "CRM Contact",
                    "full_name": lead.lead_name,
                    "organization": organization,
                    "email": lead.email,
                    "mobile_no": lead.mobile_no,
                    "is_primary": 1,
                    "status": "Active",
                }
            ).insert()
            contact = contact_doc.name

    default_stages = frappe.get_all(
        "CRM Pipeline Stage",
        filters={"disabled": 0, "is_won": 0, "is_lost": 0},
        fields=["name"],
        order_by="sequence asc",
        limit_page_length=1,
    )
    if not default_stages:
        frappe.throw(_("No active pipeline stage is configured."))
    default_stage = default_stages[0].name
    opportunity = frappe.get_doc(
        {
            "doctype": "CRM Opportunity",
            "opportunity_name": opportunity_name or f"{company_name or lead.lead_name} Opportunity",
            "organization": organization,
            "primary_contact": contact,
            "source_lead": lead.name,
            "pipeline_stage": default_stage,
            "currency": lead.currency,
            "amount": lead.estimated_value,
            "expected_close_date": lead.target_close_date or add_days(nowdate(), 30),
            "opportunity_owner": lead.lead_owner,
            "status": "Open",
        }
    ).insert()
    frappe.db.set_value(
        "CRM Lead",
        lead.name,
        {"status": "Converted", "converted_opportunity": opportunity.name},
    )
    return {"organization": organization, "contact": contact, "opportunity": opportunity.name}


@frappe.whitelist(methods=["POST"])
def move_opportunity(opportunity_name: str, pipeline_stage: str, loss_reason: str | None = None):
    opportunity = frappe.get_doc("CRM Opportunity", opportunity_name)
    opportunity.check_permission("write")
    stage = frappe.db.get_value(
        "CRM Pipeline Stage", pipeline_stage, ["name", "is_lost", "disabled"], as_dict=True
    )
    if not stage:
        frappe.throw(_("Pipeline stage does not exist."))
    if stage.disabled:
        frappe.throw(_("The selected pipeline stage is disabled."))
    if stage.is_lost and not (loss_reason or "").strip():
        frappe.throw(_("Enter a loss reason before closing an opportunity as lost."))
    opportunity.pipeline_stage = pipeline_stage
    if stage.is_lost:
        opportunity.loss_reason = loss_reason.strip()
    opportunity.save()
    return {
        "name": opportunity.name,
        "pipeline_stage": opportunity.pipeline_stage,
        "probability": opportunity.probability,
        "weighted_amount": opportunity.weighted_amount,
        "status": opportunity.status,
    }


@frappe.whitelist(methods=["GET"])
def get_customer_360(organization_name: str):
    organization = frappe.get_doc("CRM Organization", organization_name)
    organization.check_permission("read")
    organization_view = {
        field: organization.get(field)
        for field in (
            "name",
            "organization_name",
            "lifecycle_stage",
            "segment",
            "industry",
            "territory",
            "website",
            "primary_email",
            "phone",
            "city",
            "country",
            "account_manager",
            "currency",
            "annual_revenue",
            "employee_count",
            "health_score",
            "last_activity_on",
            "last_activity_type",
            "tags",
            "notes",
        )
    }
    contacts = frappe.get_list(
        "CRM Contact",
        filters={"organization": organization.name},
        fields=["name", "full_name", "job_title", "email", "mobile_no", "is_primary", "status", "last_contacted_on"],
        order_by="is_primary desc, full_name asc",
    )
    opportunities = frappe.get_list(
        "CRM Opportunity",
        filters={"organization": organization.name},
        fields=["name", "opportunity_name", "pipeline_stage", "status", "amount", "weighted_amount", "expected_close_date"],
        order_by="modified desc",
    )
    activities = frappe.get_list(
        "CRM Activity",
        filters={"organization": organization.name},
        fields=["name", "activity_type", "subject", "activity_datetime", "status", "owner_user"],
        order_by="activity_datetime desc",
        limit_page_length=50,
    )
    assets = frappe.get_list(
        "CRM Document Asset",
        filters={"organization": organization.name},
        fields=["name", "title", "document_type", "file_url", "classification", "extraction_status", "modified"],
        order_by="modified desc",
        limit_page_length=30,
    )
    return {
        "organization": organization_view,
        "contacts": contacts,
        "opportunities": opportunities,
        "activities": activities,
        "assets": assets,
    }


@frappe.whitelist(methods=["GET"])
def search_document_assets(query: str, organization: str | None = None, limit: int = 20):
    _require_read("CRM Document Asset")
    query = (query or "").strip()
    if len(query) < 2:
        frappe.throw(_("Search query must contain at least two characters."))
    filters = {"organization": organization} if organization else {}
    return frappe.get_list(
        "CRM Document Asset",
        filters=filters,
        or_filters={"title": ["like", f"%{query}%"], "extracted_text": ["like", f"%{query}%"], "tags": ["like", f"%{query}%"]},
        fields=["name", "title", "organization", "document_type", "classification", "file_url", "extraction_status", "modified"],
        order_by="modified desc",
        limit_page_length=min(max(cint(limit), 1), 100),
    )


@frappe.whitelist(methods=["POST"])
def add_note(reference_doctype: str, reference_name: str, subject: str, notes: str):
    if reference_doctype not in {"CRM Lead", "CRM Opportunity", "CRM Organization", "CRM Contact"}:
        frappe.throw(_("Unsupported reference type."))
    reference = frappe.get_doc(reference_doctype, reference_name)
    reference.check_permission("read")
    activity = frappe.get_doc(
        {
            "doctype": "CRM Activity",
            "activity_type": "Note",
            "subject": subject,
            "notes": notes,
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "organization": reference.get("organization") or (reference.name if reference_doctype == "CRM Organization" else None),
            "activity_datetime": now_datetime(),
            "owner_user": frappe.session.user,
            "status": "Completed",
        }
    ).insert()
    return {"name": activity.name, "activity_datetime": activity.activity_datetime}


@frappe.whitelist(methods=["POST"])
def decide_quote(quote_name: str, decision: str, rejection_reason: str | None = None):
    if not set(frappe.get_roles()) & {"CRM Sales Manager", "System Manager"}:
        frappe.throw(_("Only a sales manager can decide quote approvals."), frappe.PermissionError)
    if decision not in {"Approved", "Rejected"}:
        frappe.throw(_("Decision must be Approved or Rejected."))

    quote = frappe.get_doc("CRM Quote", quote_name)
    quote.check_permission("write")
    if quote.docstatus != 0:
        frappe.throw(_("Only draft quotes can be approved or rejected."))
    if quote.approval_status != "Pending":
        frappe.throw(_("This quote is not waiting for approval."))
    if decision == "Rejected" and not (rejection_reason or "").strip():
        frappe.throw(_("Enter a rejection reason."))

    values = {
        "approval_status": decision,
        "approved_by": frappe.session.user if decision == "Approved" else None,
        "approved_on": now_datetime() if decision == "Approved" else None,
        "rejection_reason": (rejection_reason or "").strip() if decision == "Rejected" else None,
        "quote_status": "Approved" if decision == "Approved" else "Rejected",
    }
    frappe.db.set_value("CRM Quote", quote.name, values)
    frappe.get_doc(
        {
            "doctype": "CRM Activity",
            "activity_type": "Contract Event",
            "subject": f"Quote {decision.lower()}",
            "reference_doctype": "CRM Quote",
            "reference_name": quote.name,
            "organization": quote.organization,
            "activity_datetime": now_datetime(),
            "owner_user": frappe.session.user,
            "status": "Completed",
            "notes": values.get("rejection_reason") or f"Decision recorded by {frappe.session.user}.",
        }
    ).insert(ignore_permissions=True)
    return {"name": quote.name, **values}


@frappe.whitelist(methods=["POST"])
def ingest_integration_event(source_system: str, event_type: str, idempotency_key: str, payload):
    frappe.only_for(("CRM Integration User", "System Manager"))
    if not source_system or not event_type or not idempotency_key:
        frappe.throw(_("Source system, event type, and idempotency key are required."))
    payload_data = _payload(payload)
    if len(json.dumps(payload_data, ensure_ascii=False).encode("utf-8")) > 1_000_000:
        frappe.throw(_("Integration payload cannot exceed 1 MB."))
    existing = frappe.db.get_value(
        "CRM Integration Event",
        {"idempotency_key": idempotency_key},
        ["name", "status"],
        as_dict=True,
    )
    if existing:
        return {"name": existing.name, "status": existing.status, "idempotent": True}
    try:
        event = frappe.get_doc(
            {
                "doctype": "CRM Integration Event",
                "direction": "Inbound",
                "source_system": source_system,
                "event_type": event_type,
                "idempotency_key": idempotency_key,
                "schema_version": "1.0",
                "status": "Received",
                "payload_json": payload_data,
                "received_on": now_datetime(),
            }
        ).insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        existing = frappe.db.get_value(
            "CRM Integration Event",
            {"idempotency_key": idempotency_key},
            ["name", "status"],
            as_dict=True,
        )
        return {"name": existing.name, "status": existing.status, "idempotent": True}
    return {"name": event.name, "status": event.status, "idempotent": False}
