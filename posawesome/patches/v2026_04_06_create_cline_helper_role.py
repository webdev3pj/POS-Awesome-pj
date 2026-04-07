# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.permissions import add_permission, update_permission_property


HELPER_ROLE_NAME = "cline helper"
POS_PAGE_NAME = "posapp"
STANDARD_PERMISSION_FIELDS = (
    "select",
    "read",
    "write",
    "create",
    "delete",
    "submit",
    "cancel",
    "amend",
    "print",
    "email",
    "report",
    "import",
    "export",
    "share",
)
HELPER_DOCTYPE_PERMISSIONS = {
    "Page": {"select": 1, "read": 1},
    "User": {"select": 1, "read": 1, "write": 1},
    "Role": {"select": 1, "read": 1},
    "POS Profile": {"select": 1, "read": 1, "write": 1},
    "Company": {"select": 1, "read": 1},
}


def execute():
    _ensure_helper_role()
    _ensure_helper_page_access(POS_PAGE_NAME)
    for doctype, permissions in HELPER_DOCTYPE_PERMISSIONS.items():
        _ensure_helper_doctype_permissions(doctype, permissions)
    frappe.clear_cache()


def _ensure_helper_role():
    existing_name = frappe.db.get_value("Role", {"role_name": HELPER_ROLE_NAME}, "name")
    if not existing_name:
        frappe.get_doc(
            {
                "doctype": "Role",
                "role_name": HELPER_ROLE_NAME,
                "desk_access": 1,
                "disabled": 0,
                "is_custom": 1,
                "two_factor_auth": 0,
            }
        ).insert(ignore_permissions=True)
        return

    frappe.db.set_value("Role", existing_name, "desk_access", 1, update_modified=False)
    frappe.db.set_value("Role", existing_name, "disabled", 0, update_modified=False)


def _ensure_helper_page_access(page_name):
    if not frappe.db.exists("Page", page_name):
        return

    page = frappe.get_doc("Page", page_name)
    existing_roles = page.get("roles") or []
    role_names = {str((row or {}).get("role") or "").strip() for row in existing_roles}
    if HELPER_ROLE_NAME in role_names:
        return

    page.append("roles", {"role": HELPER_ROLE_NAME})
    page.save(ignore_permissions=True)


def _ensure_helper_doctype_permissions(doctype, desired_permissions):
    from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype

    if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
        for row in frappe.get_all("DocPerm", fields="*", filters={"parent": doctype}):
            custom_row = frappe.new_doc("Custom DocPerm")
            custom_row.update(row)
            custom_row.insert(ignore_permissions=True)

    permission_name = frappe.db.get_value(
        "Custom DocPerm",
        {"parent": doctype, "role": HELPER_ROLE_NAME, "permlevel": 0, "if_owner": 0},
        "name",
    )
    if not permission_name:
        seed_ptype = next((ptype for ptype, enabled in desired_permissions.items() if enabled), "read")
        permission_name = add_permission(doctype, HELPER_ROLE_NAME, 0, seed_ptype)

    for fieldname in STANDARD_PERMISSION_FIELDS:
        update_permission_property(
            doctype,
            HELPER_ROLE_NAME,
            0,
            fieldname,
            1 if desired_permissions.get(fieldname) else 0,
            validate=False,
        )

    validate_permissions_for_doctype(doctype)
