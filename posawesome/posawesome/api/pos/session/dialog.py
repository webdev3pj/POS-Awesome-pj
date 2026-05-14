from __future__ import unicode_literals

import frappe
from frappe.utils import cint, cstr

from posawesome.posawesome.api.pos.session.profile import get_default_pos_profile_for_user
from posawesome.posawesome.api.pos.session.roles import (
    OPERATIONAL_ROLES,
    is_admin_role_testing_enabled,
)


def is_token_workflow_enabled(pos_profile):
    if not pos_profile:
        return False
    return (
        cint(frappe.get_cached_value("POS Profile", pos_profile, "custom_have_token") or 0)
        == 1
    )


def get_legacy_opening_dialog_data(erpnext_version=13):
    data = {}
    data["companies"] = frappe.get_list("Company", limit_page_length=0, order_by="name")
    data["pos_profiles_data"] = frappe.get_list(
        "POS Profile",
        filters={"disabled": 0},
        fields=["name", "company", "currency"],
        limit_page_length=0,
        order_by="name",
    )
    data["default_pos_profile"] = ""
    data["default_company"] = ""
    data["token_workflow_enabled"] = 0

    pos_profiles_list = [
        cstr(row.get("name") if isinstance(row, dict) else row.name)
        for row in data["pos_profiles_data"]
    ]
    _set_payment_methods(data, pos_profiles_list, erpnext_version)
    _set_role_defaults(data, token_workflow_enabled=False)
    return data


def get_opening_dialog_data(erpnext_version=13):
    default_pos_profile = get_default_pos_profile_for_user(frappe.session.user)
    if not is_token_workflow_enabled(default_pos_profile):
        return get_legacy_opening_dialog_data(erpnext_version=erpnext_version)

    data = {
        "default_pos_profile": default_pos_profile,
        "default_company": "",
        "token_workflow_enabled": 1,
    }
    if default_pos_profile:
        default_profile_doc = frappe.get_cached_doc("POS Profile", default_pos_profile)
        data["default_company"] = default_profile_doc.company
        data["companies"] = [{"name": default_profile_doc.company}]
        data["pos_profiles_data"] = [
            {
                "name": default_profile_doc.name,
                "company": default_profile_doc.company,
                "currency": default_profile_doc.currency,
            }
        ]
    else:
        data["companies"] = []
        data["pos_profiles_data"] = []

    pos_profiles_list = [
        cstr(row.get("name") if isinstance(row, dict) else row.name)
        for row in data["pos_profiles_data"]
    ]
    _set_payment_methods(data, pos_profiles_list, erpnext_version)
    _set_role_defaults(
        data,
        token_workflow_enabled=True,
        default_pos_profile=default_pos_profile,
    )

    relay_client_auth_key = cstr(frappe.conf.get("posa_edge_relay_client_key") or "").strip()
    data["relay_client_auth_key"] = relay_client_auth_key
    data["relay_client_auth_required"] = 1 if relay_client_auth_key else 0
    return data


def _set_payment_methods(data, pos_profiles_list, erpnext_version):
    payment_method_table = (
        "POS Payment Method" if erpnext_version == 13 else "Sales Invoice Payment"
    )
    data["payments_method"] = frappe.get_list(
        payment_method_table,
        filters={"parent": ["in", pos_profiles_list]},
        fields=["*"],
        limit_page_length=0,
        order_by="parent",
        ignore_permissions=True,
    )
    for mode in data["payments_method"]:
        mode["currency"] = frappe.get_cached_value(
            "POS Profile", mode["parent"], "currency"
        )


def _set_role_defaults(data, token_workflow_enabled, default_pos_profile=""):
    admin_role_testing_enabled = is_admin_role_testing_enabled()
    data["admin_role_testing_enabled"] = (
        1 if token_workflow_enabled and admin_role_testing_enabled else 0
    )
    data["admin_test_roles"] = (
        list(OPERATIONAL_ROLES)
        if token_workflow_enabled and admin_role_testing_enabled
        else []
    )

    if not token_workflow_enabled:
        data["user_role"] = ""
        data["role_error"] = ""
        data["relay_client_auth_key"] = ""
        data["relay_client_auth_required"] = 0
        return

    cline_roles = [role for role in frappe.get_roles() if role.startswith("cline-")]
    if admin_role_testing_enabled:
        data["user_role"] = "cline-Supervisor"
        data["role_error"] = ""
    elif len(cline_roles) > 1:
        data["user_role"] = ""
        data["role_error"] = frappe._(
            "User has multiple operational roles ({0}); fix roles in Backend."
        ).format(", ".join(cline_roles))
    elif len(cline_roles) == 1:
        data["user_role"] = cline_roles[0]
        data["role_error"] = ""
        if not default_pos_profile:
            data["role_error"] = frappe._(
                "No default POS Profile is assigned to this user. Please set a default POS Profile in Backend."
            )
    else:
        _set_missing_role_error(data)


def _set_missing_role_error(data):
    token_enabled_profiles = frappe.get_all(
        "POS Profile",
        filters={"disabled": 0, "custom_have_token": 1},
        fields=["name"],
        limit_page_length=1,
    )
    if token_enabled_profiles:
        data["user_role"] = ""
        data["role_error"] = frappe._(
            "User has no assigned role. Please contact admin to assign a role (Sales Associate, Cashier, Picker, Dispatch, or Supervisor) in the Backend."
        )
    else:
        data["user_role"] = ""
        data["role_error"] = ""
