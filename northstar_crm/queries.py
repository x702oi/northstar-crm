import frappe


@frappe.whitelist(methods=["GET"])
@frappe.validate_and_sanitize_search_inputs
def organization_for_opportunity(doctype, txt, searchfield, start, page_len, filters):
    opportunity = (filters or {}).get("opportunity")
    if not opportunity:
        return []
    organization = frappe.db.get_value("CRM Opportunity", opportunity, "organization")
    if not organization:
        return []
    return frappe.get_list(
        "CRM Organization",
        filters={"name": organization},
        fields=["name", "organization_name"],
        as_list=True,
    )

