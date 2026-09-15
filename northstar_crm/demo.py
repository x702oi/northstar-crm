import frappe
from frappe.utils import add_days, nowdate


DEMO_ORGANIZATIONS = (
    ("CloudNova Technologies", "Technology", "Enterprise", "Riyadh"),
    ("Vertex Holdings", "Financial Services", "Enterprise", "Jeddah"),
    ("Riyadh Systems", "Information Technology", "Mid-Market", "Riyadh"),
    ("Noura Retail Group", "Retail", "Enterprise", "Dammam"),
)


def _stage(label):
    return frappe.db.get_value("CRM Pipeline Stage", {"stage_name": label}, "name")


def create_demo_data():
    created = {"organizations": [], "contacts": [], "opportunities": []}
    manager = frappe.session.user
    for organization_name, industry, segment, city in DEMO_ORGANIZATIONS:
        name = frappe.db.get_value("CRM Organization", {"organization_name": organization_name}, "name")
        if not name:
            doc = frappe.get_doc(
                {
                    "doctype": "CRM Organization",
                    "organization_name": organization_name,
                    "industry": industry,
                    "segment": segment,
                    "city": city,
                    "country": "Saudi Arabia",
                    "account_manager": manager,
                    "lifecycle_stage": "Prospect",
                }
            ).insert(ignore_permissions=True)
            name = doc.name
            created["organizations"].append(name)

    examples = (
        ("CloudNova AI Infrastructure", "CloudNova Technologies", "Negotiation", 620000, 7),
        ("Enterprise Cloud Migration", "Vertex Holdings", "Proposal", 480000, 16),
        ("Analytics Platform Rollout", "Riyadh Systems", "Qualified", 355000, 24),
        ("Customer Data Hub", "Noura Retail Group", "New Lead", 290000, 32),
    )
    for title, company, stage, amount, close_in_days in examples:
        if frappe.db.exists("CRM Opportunity", {"opportunity_name": title}):
            continue
        organization = frappe.db.get_value("CRM Organization", {"organization_name": company}, "name")
        doc = frappe.get_doc(
            {
                "doctype": "CRM Opportunity",
                "opportunity_name": title,
                "organization": organization,
                "pipeline_stage": _stage(stage),
                "amount": amount,
                "expected_close_date": add_days(nowdate(), close_in_days),
                "opportunity_owner": manager,
                "status": "Open",
            }
        ).insert(ignore_permissions=True)
        created["opportunities"].append(doc.name)
    return created
