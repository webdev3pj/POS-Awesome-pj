import frappe
from frappe.utils.password import update_password


DEFAULT_PASSWORD = "Test@12345"
DEFAULT_SOURCE_PROFILE = "PJ7 CASHIER"
DEFAULT_TEST_PROFILE = "POS TEST SA CASHIER"

SA_USER = {
    "email": "pos.sa.test@example.com",
    "first_name": "POS",
    "last_name": "Sales Associate Test",
    "role_profile": "POS Test Sales Associate",
    "roles": ("cline-Sales Associate", "Sales User", "Stock User", "Accounts User", "Desk User"),
}

CASHIER_USER = {
    "email": "pos.cashier.test@example.com",
    "first_name": "POS",
    "last_name": "Cashier Test",
    "role_profile": "POS Test Cashier",
    "roles": ("cline-Cashier", "Sales User", "Stock User", "Accounts User", "Desk User"),
}


def _role_exists(role):
    return frappe.db.exists("Role", role)


def _ensure_role(role):
    if _role_exists(role):
        return
    doc = frappe.get_doc(
        {
            "doctype": "Role",
            "role_name": role,
            "desk_access": 1,
        }
    )
    doc.insert(ignore_permissions=True)


def _available_roles(roles):
    out = []
    for role in roles:
        if role.startswith("cline-"):
            _ensure_role(role)
        if _role_exists(role):
            out.append(role)
    return out


def _ensure_role_profile(name, roles):
    roles = _available_roles(roles)
    if frappe.db.exists("Role Profile", name):
        doc = frappe.get_doc("Role Profile", name)
        doc.set("roles", [])
    else:
        doc = frappe.get_doc({"doctype": "Role Profile", "role_profile": name})

    for role in roles:
        doc.append("roles", {"role": role})

    doc.flags.ignore_permissions = True
    doc.save()
    return doc.name


def _ensure_user(config, password):
    email = config["email"]
    roles = _available_roles(config["roles"])
    _ensure_role_profile(config["role_profile"], roles)

    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
    else:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "username": email,
                "first_name": config["first_name"],
                "last_name": config["last_name"],
                "send_welcome_email": 0,
                "user_type": "System User",
            }
        )

    user.enabled = 1
    user.first_name = config["first_name"]
    user.last_name = config["last_name"]
    user.user_type = "System User"
    user.role_profile_name = config["role_profile"]
    user.module_profile = ""
    user.set("roles", [])
    for role in roles:
        user.append("roles", {"role": role})

    user.flags.ignore_permissions = True
    user.flags.no_welcome_mail = True
    user.save()
    update_password(email, password)
    return user.name


def _copy_profile(source_profile, target_profile):
    if not frappe.db.exists("POS Profile", source_profile):
        frappe.throw(f"Source POS Profile does not exist: {source_profile}")

    source = frappe.get_doc("POS Profile", source_profile)
    users = (SA_USER["email"], CASHIER_USER["email"])
    _clear_default_profile_rows(users, source.company)
    if frappe.db.exists("POS Profile", target_profile):
        profile = frappe.get_doc("POS Profile", target_profile)
    else:
        profile = frappe.copy_doc(source)
        profile.name = target_profile

    simple_fields = [
        "company",
        "customer",
        "country",
        "warehouse",
        "campaign",
        "currency",
        "selling_price_list",
        "write_off_account",
        "write_off_cost_center",
        "income_account",
        "expense_account",
        "taxes_and_charges",
        "tax_category",
        "cost_center",
        "print_format",
        "letter_head",
        "select_print_heading",
        "posa_cash_mode_of_payment",
        "posa_sales_order_naming_series",
        "custom_edge_relay_url",
        "posa_edge_relay_connectivity_mode",
    ]
    for fieldname in simple_fields:
        if source.meta.has_field(fieldname) and profile.meta.has_field(fieldname):
            setattr(profile, fieldname, source.get(fieldname))

    for table_field in (
        "payments",
        "item_groups",
        "customer_groups",
        "pos_awesome_payments",
    ):
        if source.meta.has_field(table_field) and profile.meta.has_field(table_field):
            profile.set(table_field, [])
            for row in source.get(table_field) or []:
                profile.append(table_field, row.as_dict(no_nulls=True))

    _ensure_profile_payment_method(profile, source)

    profile.disabled = 0
    for fieldname, value in {
        "custom_have_token": 1,
        "posa_allow_sales_order": 1,
        "custom_allow_select_sales_order": 1,
        "posa_simplified_sa_cashier_ui": 1,
        "posa_allow_sa_quotation": 1,
        "posa_allow_cashier_quotation": 1,
        "posa_allow_print_draft_invoices": 1,
        "posa_allow_cloud_fallback_when_relay_down": 1,
        "posa_hide_closing_shift": 0,
    }.items():
        if profile.meta.has_field(fieldname):
            setattr(profile, fieldname, value)

    profile.set("applicable_for_users", [])
    for email in users:
        profile.append("applicable_for_users", {"user": email, "default": 1})

    profile.flags.ignore_permissions = True
    if profile.is_new():
        profile.insert(ignore_permissions=True)
    else:
        profile.save()
    return profile.name


def _ensure_profile_payment_method(profile, source):
    if not profile.meta.has_field("payments"):
        return

    preferred_modes = [
        source.get("posa_cash_mode_of_payment"),
        "Cash",
        "Bank Transfer",
        "Credit Card",
        "Cash PJ7",
        "PJ7 OPENING INVOICE PAYMENT",
    ]
    added_default = any(row.get("default") for row in profile.get("payments") or [])
    for mode in preferred_modes:
        mode = frappe.as_unicode(mode or "").strip()
        if mode:
            added_default = _append_payment_mode(profile, mode, default=0 if added_default else 1)

    if not profile.get("payments"):
        mode = frappe.db.get_value("Mode of Payment", {"enabled": 1}, "name")
        if not mode:
            frappe.throw("No enabled Mode of Payment exists for POS Profile provisioning.")
        _append_payment_mode(profile, mode, default=1)

    if not any(row.get("default") for row in profile.get("payments") or []):
        profile.get("payments")[0].default = 1


def _append_payment_mode(profile, mode, default=0):
    if not frappe.db.exists("Mode of Payment", mode):
        return False
    if any(row.get("mode_of_payment") == mode for row in profile.get("payments") or []):
        return bool(any(row.get("default") for row in profile.get("payments") or []))

    row = {"mode_of_payment": mode}
    if profile.meta.get_field("payments").options == "POS Payment Method":
        row.update({"default": default, "allow_in_returns": 1})
    else:
        row.update({"default": default, "amount": 0})
    profile.append("payments", row)
    return bool(default) or bool(any(row.get("default") for row in profile.get("payments") or []))


def _clear_default_profile_rows(users, company):
    if not users or not company:
        return
    frappe.db.sql(
        """
        update `tabPOS Profile User` pfu
        inner join `tabPOS Profile` pf on pf.name = pfu.parent
        set pfu.default = 0
        where pfu.user in %(users)s
            and pf.company = %(company)s
        """,
        {"users": tuple(users), "company": company},
    )


def _ensure_user_permission(user, allow, for_value):
    if not for_value or not frappe.db.exists(allow, for_value):
        return None
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
        return existing
    doc = frappe.get_doc(
        {
            "doctype": "User Permission",
            "user": user,
            "allow": allow,
            "for_value": for_value,
            "applicable_for": "",
            "apply_to_all_doctypes": 1,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _clear_test_user_pos_profile_permissions(users):
    # POS boot may restore a previously active profile from browser storage.
    # Do not hard-restrict these test users to one profile at permission level.
    names = frappe.get_all(
        "User Permission",
        filters={"user": ["in", users], "allow": "POS Profile"},
        pluck="name",
        ignore_permissions=True,
    )
    for name in names:
        frappe.delete_doc("User Permission", name, ignore_permissions=True, force=True)


@frappe.whitelist()
def provision(
    source_profile=DEFAULT_SOURCE_PROFILE,
    target_profile=DEFAULT_TEST_PROFILE,
    password=DEFAULT_PASSWORD,
):
    """Create reusable SA/Cashier users and a POS Profile for manual POS flow tests."""
    sa_email = _ensure_user(SA_USER, password)
    cashier_email = _ensure_user(CASHIER_USER, password)
    profile_name = _copy_profile(source_profile, target_profile)
    profile = frappe.get_doc("POS Profile", profile_name)

    for user in (sa_email, cashier_email):
        _ensure_user_permission(user, "Company", profile.company)
    _clear_test_user_pos_profile_permissions((sa_email, cashier_email))

    frappe.db.commit()
    frappe.clear_cache()

    return {
        "site": frappe.local.site,
        "password": password,
        "source_profile": source_profile,
        "pos_profile": profile_name,
        "company": profile.company,
        "customer": profile.customer,
        "sales_associate": {
            "email": SA_USER["email"],
            "role_profile": SA_USER["role_profile"],
            "roles": _available_roles(SA_USER["roles"]),
        },
        "cashier": {
            "email": CASHIER_USER["email"],
            "role_profile": CASHIER_USER["role_profile"],
            "roles": _available_roles(CASHIER_USER["roles"]),
        },
    }
