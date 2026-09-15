from __future__ import annotations

from collections import defaultdict
from datetime import date

import frappe
from frappe.utils import flt, get_first_day, get_last_day, nowdate


def forecast_window(period: str = "quarter") -> tuple[date, date]:
    today = frappe.utils.getdate(nowdate())
    if period == "month":
        return get_first_day(today), get_last_day(today)
    quarter_month = ((today.month - 1) // 3) * 3 + 1
    start = date(today.year, quarter_month, 1)
    end_month = quarter_month + 2
    return start, get_last_day(date(today.year, end_month, 1))


def get_pipeline_forecast(period: str = "quarter", owner: str | None = None, ignore_permissions: bool = False):
    start, end = forecast_window(period)
    filters = {
        "expected_close_date": ["between", [start, end]],
        "status": ["in", ["Open", "On Hold"]],
    }
    if owner:
        filters["opportunity_owner"] = owner

    list_method = frappe.get_all if ignore_permissions else frappe.get_list
    rows = list_method(
        "CRM Opportunity",
        filters=filters,
        fields=["name", "pipeline_stage", "amount", "probability", "weighted_amount", "status"],
        order_by="expected_close_date asc",
    )
    by_stage = defaultdict(lambda: {"count": 0, "amount": 0.0, "weighted_amount": 0.0})
    for row in rows:
        bucket = by_stage[row.pipeline_stage or "Unassigned"]
        bucket["count"] += 1
        bucket["amount"] += flt(row.amount)
        bucket["weighted_amount"] += flt(row.weighted_amount)

    return {
        "period": period,
        "from_date": start,
        "to_date": end,
        "total_count": len(rows),
        "pipeline_amount": sum(flt(row.amount) for row in rows),
        "weighted_forecast": sum(flt(row.weighted_amount) for row in rows),
        "by_stage": dict(by_stage),
    }
