import frappe
from frappe.utils import now_datetime, time_diff_in_hours


def after_insert(doc, method=None):
    frappe.get_doc(
        {
            "doctype": "CRM Stage History",
            "opportunity": doc.name,
            "from_stage": None,
            "to_stage": doc.pipeline_stage,
            "changed_on": doc.stage_entered_on or now_datetime(),
            "changed_by": frappe.session.user,
            "duration_hours": 0,
            "reason": "Opportunity created",
        }
    ).insert(ignore_permissions=True)


def on_update(doc, method=None):
    previous = doc.get_doc_before_save()
    if not previous or previous.pipeline_stage == doc.pipeline_stage:
        return

    changed_on = now_datetime()
    frappe.get_doc(
        {
            "doctype": "CRM Stage History",
            "opportunity": doc.name,
            "from_stage": previous.pipeline_stage,
            "to_stage": doc.pipeline_stage,
            "changed_on": changed_on,
            "changed_by": frappe.session.user,
            "duration_hours": max(time_diff_in_hours(changed_on, previous.stage_entered_on), 0)
            if previous.stage_entered_on
            else 0,
        }
    ).insert(ignore_permissions=True)

    frappe.get_doc(
        {
            "doctype": "CRM Activity",
            "activity_type": "Stage Change",
            "subject": f"Moved to {doc.pipeline_stage}",
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "organization": doc.organization,
            "activity_datetime": changed_on,
            "owner_user": frappe.session.user,
            "status": "Completed",
            "notes": f"Pipeline stage changed from {previous.pipeline_stage or 'Unassigned'} to {doc.pipeline_stage}.",
        }
    ).insert(ignore_permissions=True)
    if frappe.db.get_single_value("CRM Settings", "enable_realtime_updates"):
        frappe.publish_realtime(
            "northstar_crm_pipeline_update",
            {"opportunity": doc.name, "stage": doc.pipeline_stage},
            user=doc.opportunity_owner,
            after_commit=True,
        )
