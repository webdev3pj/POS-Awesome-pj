# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.permissions import add_permission, update_permission_property
from frappe.utils import cstr


POS_PAGE_NAME = "posapp"

ROLE_SPECS = (
    {"role_name": "cline-Sales Associate", "desk_access": 1},
    {"role_name": "cline-Cashier", "desk_access": 1},
    {"role_name": "cline-Supervisor", "desk_access": 1},
)

ROLE_PROFILES = {
    "POS Sales Associate": ("cline-Sales Associate",),
    "POS Cashier": ("cline-Cashier",),
}

USER_SPECS = (
    {
        "email": "pos-sales-associate@pjjamaica.com",
        "first_name": "POS",
        "last_name": "Sales Associate",
        "role_profile": "POS Sales Associate",
    },
    {
        "email": "pos-cashier@pjjamaica.com",
        "first_name": "POS",
        "last_name": "Cashier",
        "role_profile": "POS Cashier",
    },
)

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

READ_ONLY = {"select": 1, "read": 1}
TRANSACTION_WRITE = {
    "select": 1,
    "read": 1,
    "write": 1,
    "create": 1,
    "submit": 1,
    "print": 1,
    "email": 1,
    "report": 1,
}
SHIFT_WRITE = {
    "select": 1,
    "read": 1,
    "write": 1,
    "create": 1,
    "submit": 1,
    "print": 1,
    "report": 1,
}

COMMON_READ_DOCTYPES = (
    "Page",
    "Company",
    "POS Profile",
    "POS Settings",
    "Customer Group",
    "Territory",
    "Item",
    "Item Group",
    "Warehouse",
    "UOM",
    "Mode of Payment",
    "Price List",
    "Item Price",
    "Sales Taxes and Charges Template",
    "Address",
    "Contact",
    "Sales Person",
    "Sales Partner",
)

SA_WRITE_DOCTYPES = (
    "Customer",
    "Sales Order",
    "Quotation",
)

CASHIER_EXTRA_WRITE_DOCTYPES = (
    "Sales Invoice",
    "Payment Entry",
    "POS Opening Shift",
    "POS Closing Shift",
)

TOKEN_PROFILE_FLAGS = {
    "posa_allow_sales_order": 1,
    "posa_default_sales_order": 1,
    "custom_allow_select_sales_order": 1,
    "posa_allow_sa_quotation": 1,
    "posa_allow_cashier_quotation": 1,
}


def execute():
    _ensure_roles()
    _ensure_role_profiles()
    _ensure_users()
    _ensure_pos_page_roles()
    _ensure_role_permissions()
    _configure_token_pos_profiles()
    frappe.clear_cache()


def _ensure_roles():
    for spec in ROLE_SPECS:
        role_name = spec["role_name"]
        existing_name = frappe.db.get_value("Role", {"role_name": role_name}, "name")
        if existing_name:
            frappe.db.set_value(
                "Role",
                existing_name,
                {"desk_access": spec.get("desk_access", 1), "disabled": 0},
                update_modified=False,
            )
            continue

        frappe.get_doc(
            {
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": spec.get("desk_access", 1),
                "disabled": 0,
                "is_custom": 1,
            }
        ).insert(ignore_permissions=True)


def _available_roles(role_names):
    roles = []
    for role_name in role_names:
        role_name = cstr(role_name).strip()
        if not role_name:
            continue
        if role_name.startswith("cline-"):
            _ensure_role_if_missing(role_name)
        if frappe.db.exists("Role", role_name):
            roles.append(role_name)
    return roles


def _ensure_role_if_missing(role_name):
    if frappe.db.exists("Role", role_name):
        return
    frappe.get_doc(
        {
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1,
            "disabled": 0,
            "is_custom": 1,
        }
    ).insert(ignore_permissions=True)


def _ensure_role_profiles():
    for profile_name, role_names in ROLE_PROFILES.items():
        roles = _available_roles(role_names)
        if frappe.db.exists("Role Profile", profile_name):
            profile = frappe.get_doc("Role Profile", profile_name)
            profile.set("roles", [])
        else:
            profile = frappe.get_doc(
                {"doctype": "Role Profile", "role_profile": profile_name}
            )

        for role_name in roles:
            profile.append("roles", {"role": role_name})

        profile.flags.ignore_permissions = True
        if profile.is_new():
            profile.insert(ignore_permissions=True)
        else:
            profile.save(ignore_permissions=True)


def _ensure_users():
    for spec in USER_SPECS:
        email = spec["email"]
        role_profile = spec["role_profile"]
        roles = _available_roles(ROLE_PROFILES.get(role_profile, ()))

        if frappe.db.exists("User", email):
            user = frappe.get_doc("User", email)
        else:
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "username": email,
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                    "send_welcome_email": 0,
                    "user_type": "System User",
                }
            )
            user.flags.no_welcome_mail = True

        user.enabled = 1
        user.first_name = spec["first_name"]
        user.last_name = spec["last_name"]
        user.user_type = "System User"
        user.role_profile_name = role_profile

        existing_roles = {row.role for row in user.get("roles") or [] if row.role}
        for role_name in roles:
            if role_name not in existing_roles:
                user.append("roles", {"role": role_name})
                existing_roles.add(role_name)

        user.flags.ignore_permissions = True
        user.flags.no_welcome_mail = True
        if user.is_new():
            user.insert(ignore_permissions=True)
        else:
            user.save(ignore_permissions=True)


def _ensure_pos_page_roles():
    if not frappe.db.exists("Page", POS_PAGE_NAME):
        return

    page = frappe.get_doc("Page", POS_PAGE_NAME)
    existing_roles = {
        cstr(row.get("role")).strip() for row in (page.get("roles") or []) if row
    }
    changed = False
    for role_name in ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"):
        if role_name in existing_roles or not frappe.db.exists("Role", role_name):
            continue
        page.append("roles", {"role": role_name})
        existing_roles.add(role_name)
        changed = True

    if changed:
        page.save(ignore_permissions=True)


def _ensure_role_permissions():
    for role_name in ("cline-Sales Associate", "cline-Cashier"):
        for doctype in COMMON_READ_DOCTYPES:
            _ensure_doctype_permission(doctype, role_name, READ_ONLY)

    for doctype in SA_WRITE_DOCTYPES:
        _ensure_doctype_permission(doctype, "cline-Sales Associate", TRANSACTION_WRITE)
        _ensure_doctype_permission(doctype, "cline-Cashier", TRANSACTION_WRITE)

    for doctype in CASHIER_EXTRA_WRITE_DOCTYPES:
        _ensure_doctype_permission(doctype, "cline-Cashier", TRANSACTION_WRITE)

    for doctype in ("POS Opening Shift", "POS Closing Shift"):
        _ensure_doctype_permission(doctype, "cline-Cashier", SHIFT_WRITE)


def _ensure_doctype_permission(doctype, role_name, desired_permissions):
    if not frappe.db.exists("DocType", doctype) or not frappe.db.exists("Role", role_name):
        return

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
        seed_ptype = next(
            (ptype for ptype, enabled in desired_permissions.items() if enabled),
            "read",
        )
        add_permission(doctype, role_name, 0, seed_ptype)

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


def _configure_token_pos_profiles():
    profile_names = _get_token_profile_names()
    if not profile_names:
        return

    for profile_name in profile_names:
        profile = frappe.get_doc("POS Profile", profile_name)
        changed = False

        for fieldname, value in TOKEN_PROFILE_FLAGS.items():
            if profile.meta.has_field(fieldname) and profile.get(fieldname) != value:
                profile.set(fieldname, value)
                changed = True

        for spec in USER_SPECS:
            changed = _ensure_profile_user(profile, spec["email"]) or changed
            _ensure_user_permission(spec["email"], "Company", profile.company)

        if changed:
            profile.save(ignore_permissions=True)


def _get_token_profile_names():
    if not frappe.db.exists("DocType", "POS Profile"):
        return []

    meta = frappe.get_meta("POS Profile")
    if not meta.has_field("custom_have_token"):
        return []

    filters = {"disabled": 0, "custom_have_token": 1}

    return frappe.get_all(
        "POS Profile",
        filters=filters,
        pluck="name",
        order_by="name",
        ignore_permissions=True,
    )


def _ensure_profile_user(profile, user):
    if not profile.meta.has_field("applicable_for_users"):
        return False

    company = cstr(profile.get("company")).strip()
    _clear_default_profile_rows(user, company, except_profile=profile.name)
    for row in profile.get("applicable_for_users") or []:
        if row.get("user") != user:
            continue
        if not row.get("default"):
            row.default = 1
            return True
        return False

    profile.append(
        "applicable_for_users",
        {
            "user": user,
            "default": 1,
        },
    )
    return True


def _clear_default_profile_rows(user, company, except_profile):
    if not user or not company or not except_profile:
        return

    frappe.db.sql(
        """
        update `tabPOS Profile User` pfu
        inner join `tabPOS Profile` pf on pf.name = pfu.parent
        set pfu.default = 0
        where pfu.user = %s
            and pf.company = %s
            and pf.name != %s
        """,
        (user, company, except_profile),
    )


def _ensure_user_permission(user, allow, for_value):
    if not user or not for_value or not frappe.db.exists(allow, for_value):
        return

    existing = frappe.db.exists(
        "User Permission",
        {
            "user": user,
            "allow": allow,
            "for_value": for_value,
            "applicable_for": "",
        },
    )
    if existing:
        return

    frappe.get_doc(
        {
            "doctype": "User Permission",
            "user": user,
            "allow": allow,
            "for_value": for_value,
            "applicable_for": "",
            "apply_to_all_doctypes": 1,
        }
    ).insert(ignore_permissions=True)
