import frappe


CRM_ROLES = (
    "CRM Sales User",
    "CRM Sales Manager",
    "CRM Analyst",
    "CRM Compliance Manager",
    "CRM Integration User",
)


PIPELINE_STAGES = (
    {"stage_name": "New Lead", "sequence": 10, "probability": 10, "color": "#63B3FF"},
    {"stage_name": "Qualified", "sequence": 20, "probability": 35, "color": "#5FE0C1"},
    {"stage_name": "Discovery", "sequence": 30, "probability": 45, "color": "#78DCCA"},
    {"stage_name": "Proposal", "sequence": 40, "probability": 60, "color": "#B491FF"},
    {"stage_name": "Negotiation", "sequence": 50, "probability": 80, "color": "#FFAB63"},
    {"stage_name": "Won", "sequence": 90, "probability": 100, "color": "#B9F76A", "is_won": 1},
    {"stage_name": "Lost", "sequence": 99, "probability": 0, "color": "#FF7A75", "is_lost": 1},
)


def before_install():
    """Create app-specific roles before DocType permissions are synchronized."""
    for role_name in CRM_ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
                ignore_permissions=True
            )


def after_install():
    """Create deterministic reference data and initialize singleton settings."""
    for values in PIPELINE_STAGES:
        if not frappe.db.exists("CRM Pipeline Stage", {"stage_name": values["stage_name"]}):
            frappe.get_doc({"doctype": "CRM Pipeline Stage", **values}).insert(ignore_permissions=True)

    settings = frappe.get_single("CRM Settings")
    if not settings.default_currency:
        settings.default_currency = frappe.db.get_single_value("Global Defaults", "default_currency") or "SAR"
    if not settings.stale_opportunity_days:
        settings.stale_opportunity_days = 14
    if not settings.high_value_threshold:
        settings.high_value_threshold = 500000
    if settings.discount_approval_threshold is None:
        settings.discount_approval_threshold = 10
    settings.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def seed_demo_data():
    """Create a small, idempotent demo dataset when explicitly requested by an administrator."""
    frappe.only_for("System Manager")
    from northstar_crm.demo import create_demo_data

    return create_demo_data()
