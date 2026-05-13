# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import cstr, nowdate

from posawesome.posawesome.api.pos.session.profile import (
    get_default_pos_profile_for_user,
    require_user_default_pos_profile,
)
from posawesome.posawesome.api.pos.session.roles import (
    OPERATIONAL_ROLES,
    get_single_operational_role,
    is_admin_role_testing_enabled,
    require_operational_role_for_action,
)


def get_opening_dialog_data(erpnext_version=13):
    data = {}
    default_pos_profile = get_default_pos_profile_for_user(frappe.session.user)
    data["default_pos_profile"] = default_pos_profile
    data["default_company"] = ""
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

    pos_profiles_list = []
    for i in data["pos_profiles_data"]:
        pos_profiles_list.append(cstr(i.get("name") if isinstance(i, dict) else i.name))

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

    admin_role_testing_enabled = is_admin_role_testing_enabled()
    data["admin_role_testing_enabled"] = 1 if admin_role_testing_enabled else 0
    data["admin_test_roles"] = list(OPERATIONAL_ROLES) if admin_role_testing_enabled else []

    user_roles = frappe.get_roles()
    cline_roles = [r for r in user_roles if r.startswith("cline-")]

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
        token_enabled_profiles = frappe.get_all(
            "POS Profile",
            filters={"disabled": 0, "custom_have_token": 1},
            fields=["name"],
            limit_page_length=1,
        )
        has_token_workflow = len(token_enabled_profiles) > 0

        if has_token_workflow:
            data["user_role"] = ""
            data["role_error"] = frappe._(
                "User has no assigned role. Please contact admin to assign a role (Sales Associate, Cashier, Picker, Dispatch, or Supervisor) in the Backend."
            )
        else:
            data["user_role"] = ""
            data["role_error"] = ""

    relay_client_auth_key = cstr(frappe.conf.get("posa_edge_relay_client_key") or "").strip()
    data["relay_client_auth_key"] = relay_client_auth_key
    data["relay_client_auth_required"] = 1 if relay_client_auth_key else 0

    return data


def create_opening_voucher(pos_profile, company, balance_details, relay_workflow_enabled_fn=None):
    pos_profile = require_user_default_pos_profile(pos_profile)
    relay_workflow_enabled_fn = relay_workflow_enabled_fn or (lambda _pos_profile: False)
    if relay_workflow_enabled_fn(cstr(pos_profile or "").strip()):
        require_operational_role_for_action(
            ("cline-Cashier", "cline-Supervisor"),
            "create POS opening shifts",
        )
    company = cstr(company or "").strip()
    profile_company = cstr(
        frappe.get_cached_value("POS Profile", pos_profile, "company") or ""
    ).strip()
    if company and company != profile_company:
        frappe.throw(_("Selected Company does not match your default POS Profile."))
    company = profile_company

    balance_details = json.loads(balance_details)

    new_pos_opening = frappe.get_doc(
        {
            "doctype": "POS Opening Shift",
            "period_start_date": frappe.utils.get_datetime(),
            "posting_date": frappe.utils.getdate(),
            "user": frappe.session.user,
            "pos_profile": pos_profile,
            "company": company,
            "docstatus": 1,
        }
    )
    new_pos_opening.set("balance_details", balance_details)
    new_pos_opening.insert(ignore_permissions=True)

    data = {}
    data["pos_opening_shift"] = new_pos_opening.as_dict()
    update_opening_shift_data(data, new_pos_opening.pos_profile)
    return data


def check_opening_shift(user):
    user = cstr(user or frappe.session.user).strip()
    if user != frappe.session.user and frappe.session.user != "Administrator":
        frappe.throw(_("You can only check your own POS opening shift."))

    open_vouchers = frappe.db.get_all(
        "POS Opening Shift",
        filters={
            "user": user,
            "pos_closing_shift": ["in", ["", None]],
            "docstatus": 1,
            "status": "Open",
        },
        fields=["name", "pos_profile"],
        order_by="period_start_date desc",
    )
    data = ""
    if len(open_vouchers) > 0:
        data = {}
        data["pos_opening_shift"] = frappe.get_doc(
            "POS Opening Shift", open_vouchers[0]["name"]
        )
        update_opening_shift_data(data, open_vouchers[0]["pos_profile"])
        return data

    role = get_single_operational_role()
    if role and role != "cline-Cashier":
        pos_profile = get_default_pos_profile_for_user(user)
        if pos_profile:
            return bootstrap_non_cash_pos_session(pos_profile, role)
    return data


def update_opening_shift_data(data, pos_profile):
    data["pos_profile"] = frappe.get_doc("POS Profile", pos_profile)
    data["company"] = frappe.get_doc("Company", data["pos_profile"].company)
    allow_negative_stock = frappe.get_value(
        "Stock Settings", None, "allow_negative_stock"
    )
    data["stock_settings"] = {}
    data["stock_settings"].update({"allow_negative_stock": allow_negative_stock})


def bootstrap_non_cash_pos_session(pos_profile, role):
    data = {
        "pos_opening_shift": {
            "name": "",
            "is_virtual_session": 1,
            "session_role": role or "",
        },
        "session_mode": "no_cash_role_session",
        "session_role": role or "",
        "session_business_date": nowdate(),
    }
    update_opening_shift_data(data, pos_profile)
    return data


def bootstrap_pos_session(pos_profile, company=None):
    pos_profile = require_user_default_pos_profile(pos_profile)
    company = cstr(company or "").strip()
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))

    pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
    target_company = cstr(company or pos_profile_doc.company or "").strip()
    if not target_company:
        frappe.throw(_("Company is required"))

    if target_company != cstr(pos_profile_doc.company or "").strip():
        frappe.throw(_("Selected Company does not match the POS Profile company."))

    role = get_single_operational_role()
    if not role:
        frappe.throw(
            _(
                "A single operational role is required for a non-cash POS session. Assign exactly one cline-* role."
            )
        )

    if role == "cline-Cashier":
        frappe.throw(
            _(
                "Cashier must open a POS Opening Shift for money accountability. Use the standard opening shift flow."
            )
        )

    if role not in (
        "cline-Sales Associate",
        "cline-Picker",
        "cline-Dispatch",
        "cline-Supervisor",
    ):
        frappe.throw(
            _("Role {0} is not allowed to start a non-cash POS session.").format(role)
        )

    return bootstrap_non_cash_pos_session(pos_profile, role)

