from __future__ import annotations

import frappe


MANAGER_ROLES = {"System Manager", "CRM Sales Manager"}
READ_ALL_ROLES = MANAGER_ROLES | {"CRM Analyst"}
READ_TYPES = {None, "read", "select", "report", "export", "print", "email"}


def _roles(user=None):
    return set(frappe.get_roles(user or frappe.session.user))


def _read_all(user=None, *, compliance=False):
    roles = _roles(user)
    return bool(roles & (READ_ALL_ROLES | ({"CRM Compliance Manager"} if compliance else set())))


def _sales_user(user=None):
    return "CRM Sales User" in _roles(user)


def _escaped_user(user=None):
    return frappe.db.escape(user or frappe.session.user)


def _organization_owner_condition(doctype, organization_field, owner_field=None, user=None, *, compliance=False):
    user = user or frappe.session.user
    if _read_all(user, compliance=compliance):
        return ""
    if not _sales_user(user):
        return "1=0"

    escaped = _escaped_user(user)
    clauses = [f"`tab{doctype}`.`owner` = {escaped}"]
    if owner_field:
        clauses.append(f"`tab{doctype}`.`{owner_field}` = {escaped}")
    clauses.append(
        f"`tab{doctype}`.`{organization_field}` in "
        f"(select `name` from `tabCRM Organization` where `account_manager` = {escaped})"
    )
    return f"({' or '.join(clauses)})"


def lead_query(user=None):
    user = user or frappe.session.user
    if _read_all(user):
        return ""
    if not _sales_user(user):
        return "1=0"
    escaped = _escaped_user(user)
    return f"(`tabCRM Lead`.`owner` = {escaped} or `tabCRM Lead`.`lead_owner` = {escaped})"


def opportunity_query(user=None):
    return _organization_owner_condition(
        "CRM Opportunity", "organization", "opportunity_owner", user, compliance=True
    )


def organization_query(user=None):
    user = user or frappe.session.user
    if _read_all(user, compliance=True):
        return ""
    if not _sales_user(user):
        return "1=0"
    escaped = _escaped_user(user)
    return f"(`tabCRM Organization`.`owner` = {escaped} or `tabCRM Organization`.`account_manager` = {escaped})"


def contact_query(user=None):
    return _organization_owner_condition("CRM Contact", "organization", user=user, compliance=True)


def activity_query(user=None):
    return _organization_owner_condition("CRM Activity", "organization", "owner_user", user, compliance=True)


def document_asset_query(user=None):
    return _organization_owner_condition(
        "CRM Document Asset", "organization", "content_owner", user, compliance=True
    )


def consent_query(user=None):
    user = user or frappe.session.user
    if _read_all(user, compliance=True):
        return ""
    if not _sales_user(user):
        return "1=0"
    escaped = _escaped_user(user)
    return (
        f"(`tabCRM Consent`.`owner` = {escaped} or `tabCRM Consent`.`contact` in "
        f"(select c.`name` from `tabCRM Contact` c inner join `tabCRM Organization` o "
        f"on o.`name` = c.`organization` where o.`account_manager` = {escaped}))"
    )


def quote_query(user=None):
    user = user or frappe.session.user
    if _read_all(user):
        return ""
    if not _sales_user(user):
        return "1=0"
    escaped = _escaped_user(user)
    return (
        f"(`tabCRM Quote`.`owner` = {escaped} or `tabCRM Quote`.`opportunity` in "
        f"(select `name` from `tabCRM Opportunity` where `opportunity_owner` = {escaped}))"
    )


def stage_history_query(user=None):
    user = user or frappe.session.user
    if _read_all(user):
        return ""
    if not _sales_user(user):
        return "1=0"
    escaped = _escaped_user(user)
    return (
        f"`tabCRM Stage History`.`opportunity` in "
        f"(select `name` from `tabCRM Opportunity` where `opportunity_owner` = {escaped})"
    )


def _base_role_decision(user=None, permission_type=None, *, compliance=False):
    roles = _roles(user)
    if roles & MANAGER_ROLES:
        return True
    if "CRM Analyst" in roles:
        return permission_type in READ_TYPES
    if compliance and "CRM Compliance Manager" in roles:
        return permission_type in READ_TYPES
    if "CRM Sales User" not in roles:
        return False
    return None


def _organization_owned(organization, user):
    return bool(organization and frappe.db.get_value("CRM Organization", organization, "account_manager") == user)


def lead_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    decision = _base_role_decision(user, permission_type)
    if decision is not None:
        return decision
    return user in {doc.owner, doc.lead_owner}


def opportunity_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    decision = _base_role_decision(user, permission_type, compliance=True)
    if decision is not None:
        return decision
    return user in {doc.owner, doc.opportunity_owner} or _organization_owned(doc.organization, user)


def organization_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    decision = _base_role_decision(user, permission_type, compliance=True)
    if decision is not None:
        return decision
    return user in {doc.owner, doc.account_manager}


def contact_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    decision = _base_role_decision(user, permission_type, compliance=True)
    if decision is not None:
        return decision
    return doc.owner == user or _organization_owned(doc.organization, user)


def activity_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    decision = _base_role_decision(user, permission_type, compliance=True)
    if decision is not None:
        return decision
    return user in {doc.owner, doc.owner_user} or _organization_owned(doc.organization, user)


def document_asset_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    decision = _base_role_decision(user, permission_type, compliance=True)
    if decision is not None:
        return decision
    return user in {doc.owner, doc.content_owner} or _organization_owned(doc.organization, user)


def consent_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    decision = _base_role_decision(user, permission_type, compliance=True)
    if decision is not None:
        return decision
    organization = frappe.db.get_value("CRM Contact", doc.contact, "organization")
    return doc.owner == user or _organization_owned(organization, user)


def quote_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    decision = _base_role_decision(user, permission_type)
    if decision is not None:
        return decision
    opportunity_owner = frappe.db.get_value("CRM Opportunity", doc.opportunity, "opportunity_owner")
    return doc.owner == user or opportunity_owner == user


def stage_history_has_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    decision = _base_role_decision(user, permission_type)
    if decision is not None:
        return decision
    opportunity_owner = frappe.db.get_value("CRM Opportunity", doc.opportunity, "opportunity_owner")
    return doc.owner == user or opportunity_owner == user
