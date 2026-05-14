# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import cstr

from posawesome.posawesome.api.pos.session.bootstrap import (
    bootstrap_non_cash_pos_session,
    bootstrap_pos_session,
    update_opening_shift_data,
)
from posawesome.posawesome.api.pos.session.dialog import (
    get_legacy_opening_dialog_data,
    get_opening_dialog_data,
    is_token_workflow_enabled,
)
from posawesome.posawesome.api.pos.session.profile import (
    get_default_pos_profile_for_user,
    require_user_default_pos_profile,
)
from posawesome.posawesome.api.pos.session.roles import (
    get_single_operational_role,
    require_operational_role_for_action,
)


def create_opening_voucher(pos_profile, company, balance_details, relay_workflow_enabled_fn=None):
    relay_workflow_enabled_fn = relay_workflow_enabled_fn or (lambda _pos_profile: False)
    token_workflow_enabled = relay_workflow_enabled_fn(cstr(pos_profile or "").strip())
    if token_workflow_enabled:
        pos_profile = require_user_default_pos_profile(pos_profile)
        require_operational_role_for_action(
            ("cline-Cashier", "cline-Supervisor"),
            "create POS opening shifts",
        )
    else:
        pos_profile = cstr(pos_profile or "").strip()
        if not pos_profile:
            frappe.throw(_("POS Profile is required"))

    company = cstr(company or "").strip()
    profile_company = cstr(
        frappe.get_cached_value("POS Profile", pos_profile, "company") or ""
    ).strip()
    if token_workflow_enabled and company and company != profile_company:
        frappe.throw(_("Selected Company does not match your default POS Profile."))
    company = profile_company if token_workflow_enabled else company
    if not company:
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
        if pos_profile and is_token_workflow_enabled(pos_profile):
            return bootstrap_non_cash_pos_session(pos_profile, role)
    return data
