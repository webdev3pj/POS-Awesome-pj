# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.permissions import add_permission, update_permission_property


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
PAGE_ACCESS_ROLES = (
    "cline helper",
    "cline-Sales Associate",
    "cline-Cashier",
    "cline-Picker",
    "cline-Dispatch",
    "cline-Supervisor",
)
PAGE_DOCTYPE_PERMISSIONS = {"select": 1, "read": 1}


def execute():
    _ensure_pos_page_roles(POS_PAGE_NAME, PAGE_ACCESS_ROLES)
    for role_name in PAGE_ACCESS_ROLES:
        if frappe.db.exists("Role", role_name):
            _ensure_doctype_permissions("Page", role_name, PAGE_DOCTYPE_PERMISSIONS)
    frappe.clear_cache()


def _ensure_pos_page_roles(page_name, role_names):
    if not frappe.db.exists("Page", page_name):
        return

    page = frappe.get_doc("Page", page_name)
    existing_roles = {str((row or {}).get("role") or "").strip() for row in (page.get("roles") or [])}
    changed = False
    for role_name in role_names:
        normalized = str(role_name or "").strip()
        if not normalized or normalized in existing_roles:
            continue
        if not frappe.db.exists("Role", normalized):
            continue
        page.append("roles", {"role": normalized})
        existing_roles.add(normalized)
        changed = True

    if changed:
        page.save(ignore_permissions=True)


def _ensure_doctype_permissions(doctype, role_name, desired_permissions):
    from frappe.core.doctype.doctype.doctype import validate_permissions_for_doctype

    if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
        for row in frappe.get_all("DocPerm", fields="*", filters={"parent": doctype}):
            custom_row = frappe.new_doc("Custom DocPerm")
            custom_row.update(row)
            custom_row.insert(ignore_permissions=True)

    permission_name = frappe.db.get_value(
        "Custom DocPerm",
        {"parent": doctype, "role": role_name, "permlevel": 0, "if_owner": 0},
        "name",
    )
    if not permission_name:
        seed_ptype = next((ptype for ptype, enabled in desired_permissions.items() if enabled), "read")
        permission_name = add_permission(doctype, role_name, 0, seed_ptype)

    for fieldname in STANDARD_PERMISSION_FIELDS:
        update_permission_property(
            doctype,
            role_name,
            0,
            fieldname,
            1 if desired_permissions.get(fieldname) else 0,
            validate=False,
        )

    validate_permissions_for_doctype(doctype)
