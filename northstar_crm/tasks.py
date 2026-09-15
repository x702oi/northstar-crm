import frappe
from frappe.utils import add_days, nowdate


def recalculate_all_lead_scores():
    from northstar_crm.services.scoring import recalculate_lead_score

    for name in frappe.get_all("CRM Lead", filters={"status": ["not in", ["Converted", "Disqualified"]]}, pluck="name"):
        frappe.enqueue(recalculate_lead_score, queue="short", lead_name=name)


def create_daily_forecast_snapshots():
    from northstar_crm.services.forecasting import get_pipeline_forecast

    today = nowdate()
    if frappe.db.exists("CRM Forecast Snapshot", {"snapshot_date": today, "scope": "Company"}):
        return
    forecast = get_pipeline_forecast("quarter", ignore_permissions=True)
    frappe.get_doc(
        {
            "doctype": "CRM Forecast Snapshot",
            "snapshot_date": today,
            "scope": "Company",
            "pipeline_amount": forecast["pipeline_amount"],
            "weighted_forecast": forecast["weighted_forecast"],
            "open_opportunities": forecast["total_count"],
            "stage_breakdown": frappe.as_json(forecast["by_stage"]),
        }
    ).insert(ignore_permissions=True)


def refresh_stale_opportunity_flags():
    stale_days = frappe.db.get_single_value("CRM Settings", "stale_opportunity_days") or 14
    cutoff = add_days(nowdate(), -int(stale_days))
    frappe.db.sql(
        """
        update `tabCRM Opportunity`
        set is_stale = case when coalesce(last_activity_on, creation) < %s then 1 else 0 end
        where status in ('Open', 'On Hold')
        """,
        cutoff,
    )


def flag_expiring_consents():
    today = nowdate()
    cutoff = add_days(nowdate(), 30)
    frappe.db.sql(
        """
        update `tabCRM Consent`
        set status = 'Expired'
        where status in ('Active', 'Expiring') and valid_until is not null and valid_until < %s
        """,
        today,
    )
    frappe.db.sql(
        """
        update `tabCRM Consent`
        set status = 'Expiring'
        where status = 'Active' and valid_until is not null and valid_until between %s and %s
        """,
        (today, cutoff),
    )
