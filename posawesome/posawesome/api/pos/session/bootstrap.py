from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cstr, nowdate

from posawesome.posawesome.api.pos.session.profile import require_user_default_pos_profile
from posawesome.posawesome.api.pos.session.roles import get_single_operational_role


def update_opening_shift_data(data, pos_profile):
    data["pos_profile"] = frappe.get_doc("POS Profile", pos_profile)
    data["company"] = frappe.get_doc("Company", data["pos_profile"].company)
    allow_negative_stock = frappe.get_value(
        "Stock Settings", None, "allow_negative_stock"
    )
    data["stock_settings"] = {"allow_negative_stock": allow_negative_stock}


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
