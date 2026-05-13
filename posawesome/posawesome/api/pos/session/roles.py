# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, cstr


OPERATIONAL_ROLES = (
    "cline-Sales Associate",
    "cline-Cashier",
    "cline-Picker",
    "cline-Dispatch",
    "cline-Supervisor",
)


def is_admin_role_testing_enabled():
    return (
        frappe.session.user == "Administrator"
        and cint(frappe.conf.get("developer_mode") or 0) == 1
    )


def admin_requested_test_role():
    if not is_admin_role_testing_enabled():
        return ""
    for key in ("role", "session_role", "posa_test_role"):
        role = cstr(frappe.form_dict.get(key) or "").strip()
        if role in OPERATIONAL_ROLES:
            return role
    return "cline-Supervisor"


def get_single_operational_role():
    admin_role = admin_requested_test_role()
    if admin_role:
        return admin_role
    user_roles = frappe.get_roles() or []
    cline_roles = [r for r in user_roles if cstr(r).startswith("cline-")]
    if len(cline_roles) != 1:
        return ""
    return cstr(cline_roles[0]).strip()


def request_header(name):
    name = cstr(name or "").strip()
    if not name:
        return ""
    try:
        getter = getattr(frappe, "get_request_header", None)
        if callable(getter):
            return cstr(getter(name) or "").strip()
    except Exception:
        pass
    try:
        req = getattr(frappe.local, "request", None)
        if req and getattr(req, "headers", None):
            return cstr(req.headers.get(name) or "").strip()
    except Exception:
        pass
    return ""


def is_relay_sync_request():
    return bool(request_header("X-Relay-Event-ID"))


def require_operational_role_for_action(allowed_roles, action_label, allow_relay_sync=False):
    allowed_roles = tuple(cstr(r).strip() for r in (allowed_roles or []) if cstr(r).strip())

    if allow_relay_sync and is_relay_sync_request():
        return "__relay_sync__"

    role = get_single_operational_role()
    if not role:
        frappe.throw(
            _(
                "A single operational role is required to {0}. Assign exactly one cline-* role."
            ).format(action_label)
        )
    if allowed_roles and role not in allowed_roles:
        frappe.throw(_("Role {0} is not allowed to {1}.").format(role, action_label))
    return role

