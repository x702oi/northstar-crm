from __future__ import annotations

import frappe
from frappe.utils import date_diff, nowdate


STATUS_POINTS = {"New": 0, "Contacted": 5, "Qualified": 12, "Disqualified": -20, "Converted": 20}


def calculate_lead_score(lead) -> tuple[int, dict]:
    """Return a transparent 0–100 score and the factors used to calculate it."""
    factors = {
        "status": STATUS_POINTS.get(lead.status, 0),
        "budget": 20 if lead.estimated_value and lead.estimated_value >= 250000 else 8 if lead.estimated_value else 0,
        "authority": (
            15
            if lead.decision_authority in {"Decision Maker", "Executive Sponsor"}
            else 6
            if lead.decision_authority in {"Influencer", "Evaluator"}
            else 0
        ),
        "need": 15 if lead.business_need else 0,
        "timeline": 15 if lead.target_close_date else 0,
        "engagement": min(int(lead.engagement_score or 0), 15),
        "recency": 0,
    }
    if lead.last_activity_on:
        age = date_diff(nowdate(), lead.last_activity_on)
        factors["recency"] = 12 if age <= 3 else 7 if age <= 14 else 0
    score = max(0, min(100, sum(factors.values())))
    return score, factors


def classify_lead_score(score: int) -> str:
    warm_threshold = frappe.db.get_single_value("CRM Settings", "warm_lead_score")
    hot_threshold = frappe.db.get_single_value("CRM Settings", "hot_lead_score")
    warm_threshold = 40 if warm_threshold is None else int(warm_threshold)
    hot_threshold = 70 if hot_threshold is None else int(hot_threshold)
    return "Hot" if score >= hot_threshold else "Warm" if score >= warm_threshold else "Cold"


def recalculate_lead_score(lead_name: str):
    if not frappe.db.exists("CRM Lead", lead_name):
        return
    lead = frappe.get_doc("CRM Lead", lead_name)
    score, factors = calculate_lead_score(lead)
    rating = classify_lead_score(score)
    frappe.db.set_value(
        "CRM Lead",
        lead_name,
        {"lead_score": score, "score_breakdown": frappe.as_json(factors), "rating": rating},
        update_modified=False,
    )
    return {"lead": lead_name, "score": score, "rating": rating, "factors": factors}
