app_name = "northstar_crm"
app_title = "Northstar CRM"
app_publisher = "Northstar CRM Team"
app_description = "Enterprise customer relationship management for Frappe Framework"
app_email = "engineering@example.com"
app_license = "MIT"
required_apps = []

before_install = "northstar_crm.install.before_install"
after_install = "northstar_crm.install.after_install"

app_include_css = ["/assets/northstar_crm/css/northstar_crm.css"]

add_to_apps_screen = [
    {
        "name": "northstar_crm",
        "logo": "/assets/northstar_crm/images/northstar-logo.svg",
        "title": "Northstar CRM",
        "route": "/desk/sales-cockpit",
        "has_permission": "northstar_crm.api.has_app_permission",
    }
]

fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "CRM Sales User",
        "CRM Sales Manager",
        "CRM Analyst",
        "CRM Compliance Manager",
        "CRM Integration User",
    ]]]},
]

doc_events = {
    "CRM Opportunity": {
        "after_insert": "northstar_crm.events.opportunity.after_insert",
        "on_update": "northstar_crm.events.opportunity.on_update",
    },
    "CRM Activity": {
        "after_insert": "northstar_crm.events.activity.after_insert",
    },
    "CRM Document Asset": {
        "after_insert": "northstar_crm.events.document_asset.after_insert",
    },
    "CRM Integration Event": {
        "after_insert": "northstar_crm.events.integration_event.after_insert",
    },
}

permission_query_conditions = {
    "CRM Lead": "northstar_crm.permissions.lead_query",
    "CRM Opportunity": "northstar_crm.permissions.opportunity_query",
    "CRM Organization": "northstar_crm.permissions.organization_query",
    "CRM Contact": "northstar_crm.permissions.contact_query",
    "CRM Activity": "northstar_crm.permissions.activity_query",
    "CRM Document Asset": "northstar_crm.permissions.document_asset_query",
    "CRM Consent": "northstar_crm.permissions.consent_query",
    "CRM Quote": "northstar_crm.permissions.quote_query",
    "CRM Stage History": "northstar_crm.permissions.stage_history_query",
}

has_permission = {
    "CRM Lead": "northstar_crm.permissions.lead_has_permission",
    "CRM Opportunity": "northstar_crm.permissions.opportunity_has_permission",
    "CRM Organization": "northstar_crm.permissions.organization_has_permission",
    "CRM Contact": "northstar_crm.permissions.contact_has_permission",
    "CRM Activity": "northstar_crm.permissions.activity_has_permission",
    "CRM Document Asset": "northstar_crm.permissions.document_asset_has_permission",
    "CRM Consent": "northstar_crm.permissions.consent_has_permission",
    "CRM Quote": "northstar_crm.permissions.quote_has_permission",
    "CRM Stage History": "northstar_crm.permissions.stage_history_has_permission",
}

scheduler_events = {
    "hourly": [
        "northstar_crm.tasks.refresh_stale_opportunity_flags",
    ],
    "daily": [
        "northstar_crm.tasks.recalculate_all_lead_scores",
        "northstar_crm.tasks.create_daily_forecast_snapshots",
        "northstar_crm.tasks.flag_expiring_consents",
    ],
}
