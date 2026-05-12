# -*- coding: utf-8 -*-
# Copyright (c) 2020, Youssef Restom and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import time
import frappe
import copy
import requests
from urllib.parse import urlparse
from frappe.utils import nowdate, flt, cstr, getdate, cint, now_datetime, add_days
from frappe import _
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.stock.get_item_details import get_item_details
from erpnext.accounts.doctype.pos_profile.pos_profile import get_item_groups
from frappe.utils.background_jobs import enqueue
from erpnext.accounts.party import get_party_bank_account
from erpnext.stock.doctype.batch.batch import (
    get_batch_no,
    get_batch_qty,
    set_batch_nos,
)
from erpnext.accounts.doctype.payment_request.payment_request import (
    get_dummy_message,
    get_existing_payment_request_amount,
)

from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
    get_loyalty_program_details_with_points,
)
from posawesome.posawesome.doctype.pos_coupon.pos_coupon import check_coupon_code
from posawesome.posawesome.doctype.delivery_charges.delivery_charges import (
    get_applicable_delivery_charges as _get_applicable_delivery_charges,
)
from frappe.utils.caching import redis_cache

OPERATIONAL_ROLES = (
    "cline-Sales Associate",
    "cline-Cashier",
    "cline-Picker",
    "cline-Dispatch",
    "cline-Supervisor",
)


@frappe.whitelist()
def get_opening_dialog_data():
    data = {}
    default_pos_profile = _get_default_pos_profile_for_user(frappe.session.user)
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
        "POS Payment Method" if get_version() == 13 else "Sales Invoice Payment"
    )
    data["payments_method"] = frappe.get_list(
        payment_method_table,
        filters={"parent": ["in", pos_profiles_list]},
        fields=["*"],
        limit_page_length=0,
        order_by="parent",
        ignore_permissions=True,
    )
    # set currency from pos profile
    for mode in data["payments_method"]:
        mode["currency"] = frappe.get_cached_value(
            "POS Profile", mode["parent"], "currency"
        )

    admin_role_testing_enabled = _is_admin_role_testing_enabled()
    data["admin_role_testing_enabled"] = 1 if admin_role_testing_enabled else 0
    data["admin_test_roles"] = list(OPERATIONAL_ROLES) if admin_role_testing_enabled else []

    # Derive role from ERPNext user roles (not user-selectable), except the
    # local Administrator/dev-mode test harness.
    user_roles = frappe.get_roles()
    cline_roles = [r for r in user_roles if r.startswith('cline-')]

    if admin_role_testing_enabled:
        data["user_role"] = "cline-Supervisor"
        data["role_error"] = ""
    elif len(cline_roles) > 1:
        # Multiple operational roles - block login
        data["user_role"] = ""
        data["role_error"] = frappe._(
            "User has multiple operational roles ({0}); fix roles in Backend."
        ).format(", ".join(cline_roles))
    elif len(cline_roles) == 1:
        # Exactly one role - use it
        data["user_role"] = cline_roles[0]
        data["role_error"] = ""
        if not default_pos_profile:
            data["role_error"] = frappe._(
                "No default POS Profile is assigned to this user. Please set a default POS Profile in Backend."
            )
    else:
        # No cline-* roles - check if any POS Profile has token workflow enabled
        token_enabled_profiles = frappe.get_all(
            "POS Profile",
            filters={"disabled": 0, "custom_have_token": 1},
            fields=["name"],
            limit_page_length=1,
        )
        has_token_workflow = len(token_enabled_profiles) > 0

        if has_token_workflow:
            # Token workflow enabled but user has no role - block
            data["user_role"] = ""
            data["role_error"] = frappe._(
                "User has no assigned role. Please contact admin to assign a role (Sales Associate, Cashier, Picker, Dispatch, or Supervisor) in the Backend."
            )
        else:
            # No token workflow - allow legacy mode
            data["user_role"] = ""
            data["role_error"] = ""

    # Optional Phase 3 relay client auth bootstrap. Keep empty unless the site
    # operator configures a shared key in site_config (or equivalent conf source).
    relay_client_auth_key = cstr(frappe.conf.get("posa_edge_relay_client_key") or "").strip()
    data["relay_client_auth_key"] = relay_client_auth_key
    data["relay_client_auth_required"] = 1 if relay_client_auth_key else 0

    return data


def _is_admin_role_testing_enabled():
    return frappe.session.user == "Administrator" and cint(frappe.conf.get("developer_mode") or 0) == 1


def _admin_requested_test_role():
    if not _is_admin_role_testing_enabled():
        return ""
    for key in ("role", "session_role", "posa_test_role"):
        role = cstr(frappe.form_dict.get(key) or "").strip()
        if role in OPERATIONAL_ROLES:
            return role
    return "cline-Supervisor"


@frappe.whitelist()
def create_opening_voucher(pos_profile, company, balance_details):
    pos_profile = _require_user_default_pos_profile(pos_profile)
    if _is_relay_workflow_enabled(cstr(pos_profile or "").strip()):
        _require_operational_role_for_action(
            ("cline-Cashier", "cline-Supervisor"),
            "create POS opening shifts",
        )
    company = cstr(company or "").strip()
    profile_company = cstr(frappe.get_cached_value("POS Profile", pos_profile, "company") or "").strip()
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


@frappe.whitelist()
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

    role = _get_single_operational_role()
    if role and role != "cline-Cashier":
        pos_profile = _get_default_pos_profile_for_user(user)
        if pos_profile:
            return _bootstrap_non_cash_pos_session(pos_profile, role)
    return data


def _get_default_pos_profile_for_user(user):
    user = cstr(user or "").strip()
    if not user:
        return ""

    rows = frappe.db.sql(
        """
        select pf.name
        from `tabPOS Profile` pf
        inner join `tabPOS Profile User` pfu on pfu.parent = pf.name
        where pfu.user = %s
            and pfu.default = 1
            and pf.disabled = 0
        order by pf.modified desc
        limit 1
        """,
        (user,),
        as_dict=True,
    )
    if rows:
        return cstr(rows[0].name or "").strip()

    rows = frappe.db.sql(
        """
        select pf.name
        from `tabPOS Profile` pf
        inner join `tabPOS Profile User` pfu on pfu.parent = pf.name
        where pfu.user = %s
            and pf.disabled = 0
        order by pf.modified desc
        limit 1
        """,
        (user,),
        as_dict=True,
    )
    if rows:
        return cstr(rows[0].name or "").strip()
    return ""


def _require_user_default_pos_profile(pos_profile):
    pos_profile = cstr(pos_profile or "").strip()
    default_pos_profile = _get_default_pos_profile_for_user(frappe.session.user)
    if not default_pos_profile:
        frappe.throw(_("No default POS Profile is assigned to this user."))
    if pos_profile != default_pos_profile:
        frappe.throw(_("You can only use your default POS Profile {0}.").format(default_pos_profile))
    return default_pos_profile


def update_opening_shift_data(data, pos_profile):
    data["pos_profile"] = frappe.get_doc("POS Profile", pos_profile)
    data["company"] = frappe.get_doc("Company", data["pos_profile"].company)
    allow_negative_stock = frappe.get_value(
        "Stock Settings", None, "allow_negative_stock"
    )
    data["stock_settings"] = {}
    data["stock_settings"].update({"allow_negative_stock": allow_negative_stock})


def _bootstrap_non_cash_pos_session(pos_profile, role):
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


def _get_single_operational_role():
    admin_role = _admin_requested_test_role()
    if admin_role:
        return admin_role
    user_roles = frappe.get_roles() or []
    cline_roles = [r for r in user_roles if cstr(r).startswith("cline-")]
    if len(cline_roles) != 1:
        return ""
    return cstr(cline_roles[0]).strip()


def _request_header(name):
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


def _is_relay_sync_request():
    return bool(_request_header("X-Relay-Event-ID"))


def _require_operational_role_for_action(allowed_roles, action_label, allow_relay_sync=False):
    allowed_roles = tuple(cstr(r).strip() for r in (allowed_roles or []) if cstr(r).strip())

    if allow_relay_sync and _is_relay_sync_request():
        return "__relay_sync__"

    role = _get_single_operational_role()
    if not role:
        frappe.throw(
            _(
                "A single operational role is required to {0}. Assign exactly one cline-* role."
            ).format(action_label)
        )
    if allowed_roles and role not in allowed_roles:
        frappe.throw(
            _("Role {0} is not allowed to {1}.").format(role, action_label)
        )
    return role


@frappe.whitelist()
def bootstrap_pos_session(pos_profile, company=None):
    pos_profile = _require_user_default_pos_profile(pos_profile)
    company = cstr(company or "").strip()
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))

    pos_profile_doc = frappe.get_doc("POS Profile", pos_profile)
    target_company = cstr(company or pos_profile_doc.company or "").strip()
    if not target_company:
        frappe.throw(_("Company is required"))

    if target_company != cstr(pos_profile_doc.company or "").strip():
        frappe.throw(_("Selected Company does not match the POS Profile company."))

    role = _get_single_operational_role()
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
        frappe.throw(_("Role {0} is not allowed to start a non-cash POS session.").format(role))

    return _bootstrap_non_cash_pos_session(pos_profile, role)


@frappe.whitelist()
def get_items(
    pos_profile, price_list=None, item_group="", search_value="", customer=None
):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 30

    @redis_cache(ttl=ttl or 1800)
    def __get_items(pos_profile, price_list, item_group, search_value, customer=None):
        return _get_items(pos_profile, price_list, item_group, search_value, customer)

    def _get_items(pos_profile, price_list, item_group, search_value, customer=None):
        pos_profile = json.loads(pos_profile)
        today = nowdate()
        data = dict()
        posa_display_items_in_stock = pos_profile.get("posa_display_items_in_stock")
        search_serial_no = pos_profile.get("posa_search_serial_no")
        search_batch_no = pos_profile.get("posa_search_batch_no")
        posa_show_template_items = pos_profile.get("posa_show_template_items")
        warehouse = pos_profile.get("warehouse")
        use_limit_search = pos_profile.get("pose_use_limit_search")
        search_limit = 0

        if not price_list:
            price_list = pos_profile.get("selling_price_list")

        limit = ""

        condition = ""
        condition += get_item_group_condition(pos_profile.get("name"))

        if use_limit_search:
            search_limit = pos_profile.get("posa_search_limit") or 500
            if search_value:
                data = search_serial_or_batch_or_barcode_number(
                    search_value, search_serial_no
                )

            item_code = data.get("item_code") if data.get("item_code") else search_value
            serial_no = data.get("serial_no") if data.get("serial_no") else ""
            batch_no = data.get("batch_no") if data.get("batch_no") else ""
            barcode = data.get("barcode") if data.get("barcode") else ""

            condition += get_seearch_items_conditions(
                item_code, serial_no, batch_no, barcode
            )
            if item_group:
                condition += " AND item_group like '%{item_group}%'".format(
                    item_group=item_group
                )
            limit = " LIMIT {search_limit}".format(search_limit=search_limit)

        if not posa_show_template_items:
            condition += " AND has_variants = 0"

        result = []

        items_data = frappe.db.sql(
            """
            SELECT
                name AS item_code,
                item_name,
                description,
                stock_uom,
                image,
                is_stock_item,
                has_variants,
                variant_of,
                item_group,
                idx as idx,
                has_batch_no,
                has_serial_no,
                max_discount,
                brand
            FROM
                `tabItem`
            WHERE
                disabled = 0
                    AND is_sales_item = 1
                    AND is_fixed_asset = 0
                    {condition}
            ORDER BY
                item_name asc
            {limit}
                """.format(
                condition=condition, limit=limit
            ),
            as_dict=1,
        )

        if items_data:
            items = [d.item_code for d in items_data]
            item_prices_data = frappe.get_all(
                "Item Price",
                fields=["item_code", "price_list_rate", "currency", "uom"],
                filters={
                    "price_list": price_list,
                    "item_code": ["in", items],
                    "currency": pos_profile.get("currency"),
                    "selling": 1,
                    "valid_from": ["<=", today],
                    "customer": ["in", ["", None, customer]],
                },
                or_filters=[
                    ["valid_upto", ">=", today],
                    ["valid_upto", "in", ["", None]],
                ],
                order_by="valid_from ASC, valid_upto DESC",
            )

            item_prices = {}
            for d in item_prices_data:
                item_prices.setdefault(d.item_code, {})
                item_prices[d.item_code][d.get("uom") or "None"] = d

            for item in items_data:
                item_code = item.item_code
                item_price = {}
                if item_prices.get(item_code):
                    item_price = (
                        item_prices.get(item_code).get(item.stock_uom)
                        or item_prices.get(item_code).get("None")
                        or {}
                    )
                item_barcode = frappe.get_all(
                    "Item Barcode",
                    filters={"parent": item_code},
                    fields=["barcode", "posa_uom"],
                )
                batch_no_data = []
                if search_batch_no:
                    batch_list = get_batch_qty(warehouse=warehouse, item_code=item_code)
                    if batch_list:
                        for batch in batch_list:
                            if batch.qty > 0 and batch.batch_no:
                                batch_doc = frappe.get_cached_doc(
                                    "Batch", batch.batch_no
                                )
                                if (
                                    str(batch_doc.expiry_date) > str(today)
                                    or batch_doc.expiry_date in ["", None]
                                ) and batch_doc.disabled == 0:
                                    batch_no_data.append(
                                        {
                                            "batch_no": batch.batch_no,
                                            "batch_qty": batch.qty,
                                            "expiry_date": batch_doc.expiry_date,
                                            "batch_price": batch_doc.posa_batch_price,
                                            "manufacturing_date": batch_doc.manufacturing_date,
                                        }
                                    )
                serial_no_data = []
                if search_serial_no:
                    serial_no_data = frappe.get_all(
                        "Serial No",
                        filters={
                            "item_code": item_code,
                            "status": "Active",
                            "warehouse": warehouse,
                        },
                        fields=["name as serial_no"],
                    )
                item_stock_qty = 0
                if pos_profile.get("posa_display_items_in_stock") or use_limit_search:
                    item_stock_qty = get_stock_availability(
                        item_code, pos_profile.get("warehouse")
                    )
                attributes = ""
                if pos_profile.get("posa_show_template_items") and item.has_variants:
                    attributes = get_item_attributes(item.item_code)
                item_attributes = ""
                if pos_profile.get("posa_show_template_items") and item.variant_of:
                    item_attributes = frappe.get_all(
                        "Item Variant Attribute",
                        fields=["attribute", "attribute_value"],
                        filters={"parent": item.item_code, "parentfield": "attributes"},
                    )
                if posa_display_items_in_stock and (
                    not item_stock_qty or item_stock_qty < 0
                ):
                    pass
                else:
                    row = {}
                    row.update(item)
                    row.update(
                        {
                            "rate": item_price.get("price_list_rate") or 0,
                            "currency": item_price.get("currency")
                            or pos_profile.get("currency"),
                            "item_barcode": item_barcode or [],
                            "actual_qty": item_stock_qty or 0,
                            "serial_no_data": serial_no_data or [],
                            "batch_no_data": batch_no_data or [],
                            "attributes": attributes or "",
                            "item_attributes": item_attributes or "",
                        }
                    )
                    result.append(row)
        return result

    if _pos_profile.get("posa_use_server_cache"):
        return __get_items(pos_profile, price_list, item_group, search_value, customer)
    else:
        return _get_items(pos_profile, price_list, item_group, search_value, customer)


def get_item_group_condition(pos_profile):
    cond = " and 1=1"
    item_groups = get_item_groups(pos_profile)
    if item_groups:
        cond = " and item_group in (%s)" % (", ".join(["%s"] * len(item_groups)))

    return cond % tuple(item_groups)


def get_root_of(doctype):
    """Get root element of a DocType with a tree structure"""
    result = frappe.db.sql(
        """select t1.name from `tab{0}` t1 where
		(select count(*) from `tab{1}` t2 where
			t2.lft < t1.lft and t2.rgt > t1.rgt) = 0
		and t1.rgt > t1.lft""".format(
            doctype, doctype
        )
    )
    return result[0][0] if result else None


@frappe.whitelist()
def get_items_groups():
    return frappe.db.sql(
        """
        select name 
        from `tabItem Group`
        where is_group = 0
        order by name
        LIMIT 0, 200 """,
        as_dict=1,
    )


def get_customer_groups(pos_profile):
    customer_groups = []
    if pos_profile.get("customer_groups"):
        # Get items based on the item groups defined in the POS profile
        for data in pos_profile.get("customer_groups"):
            customer_groups.extend(
                [
                    "%s" % frappe.db.escape(d.get("name"))
                    for d in get_child_nodes(
                        "Customer Group", data.get("customer_group")
                    )
                ]
            )

    return list(set(customer_groups))


def get_child_nodes(group_type, root):
    lft, rgt = frappe.db.get_value(group_type, root, ["lft", "rgt"])
    return frappe.db.sql(
        """ Select name, lft, rgt from `tab{tab}` where
			lft >= {lft} and rgt <= {rgt} order by lft""".format(
            tab=group_type, lft=lft, rgt=rgt
        ),
        as_dict=1,
    )


def get_customer_group_condition(pos_profile):
    cond = "disabled = 0"
    customer_groups = get_customer_groups(pos_profile)
    if customer_groups:
        cond = " customer_group in (%s)" % (", ".join(["%s"] * len(customer_groups)))

    return cond % tuple(customer_groups)


@frappe.whitelist()
def get_customer_names(pos_profile):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 60

    @redis_cache(ttl=ttl or 1800)
    def __get_customer_names(pos_profile):
        return _get_customer_names(pos_profile)

    def _get_customer_names(pos_profile):
        pos_profile = json.loads(pos_profile)
        condition = ""
        condition += get_customer_group_condition(pos_profile)
        customers = frappe.db.sql(
            """
            SELECT name, mobile_no, email_id, tax_id, customer_name, primary_address
            FROM `tabCustomer`
            WHERE {0}
            ORDER by name
            """.format(
                condition
            ),
            as_dict=1,
        )
        return customers

    if _pos_profile.get("posa_use_server_cache"):
        return __get_customer_names(pos_profile)
    else:
        return _get_customer_names(pos_profile)


@frappe.whitelist()
def get_sales_person_names():
    sales_persons = frappe.get_list(
        "Sales Person",
        filters={"enabled": 1},
        fields=["name", "sales_person_name"],
        limit_page_length=100000,
    )
    return sales_persons

@frappe.whitelist()
def get_sales_partner_names():
    sales_partners = frappe.get_list(
        "Sales Partner",
        fields=["name", "partner_name"],
        limit_page_length=100000,
    )
    return sales_partners


RELAY_TOKEN_STATUSES = ("Draft", "Paid", "Expired", "Abandoned")
RELAY_PICKING_STATUSES = ("Not Started", "In Progress", "Picked", "Exception")
RELAY_DISPATCH_STATUSES = ("Pending", "Released", "On Hold")


def _relay_workflow_doctype_exists():
    return bool(frappe.db.exists("DocType", "POS Relay Workflow State"))


def _is_relay_workflow_enabled(pos_profile):
    if not pos_profile:
        return False

    return cint(
        frappe.get_cached_value("POS Profile", pos_profile, "custom_have_token") or 0
    ) == 1


def _resolve_relay_workflow_pos_profile(invoice_doc, *candidates):
    invoice_profile = cstr((invoice_doc.get("pos_profile") if invoice_doc else "") or "").strip()
    if invoice_profile:
        return invoice_profile

    for candidate in candidates:
        value = cstr(candidate or "").strip()
        if value:
            return value

    if invoice_doc and _relay_workflow_doctype_exists():
        try:
            state_name = frappe.db.exists("POS Relay Workflow State", {"sales_invoice": invoice_doc.name})
            if state_name:
                return cstr(
                    frappe.db.get_value("POS Relay Workflow State", state_name, "pos_profile") or ""
                ).strip()
        except Exception:
            pass

    return ""


def _relay_workflow_meta():
    if not _relay_workflow_doctype_exists():
        return None
    try:
        return frappe.get_meta("POS Relay Workflow State")
    except Exception:
        return None


def _relay_workflow_has_field(fieldname):
    meta = _relay_workflow_meta()
    return bool(meta and meta.has_field(fieldname))


def _set_state_field_if_exists(state_doc, fieldname, value):
    if value is None:
        return
    if _relay_workflow_has_field(fieldname):
        state_doc.set(fieldname, value)


def _get_relay_invoice_by_local_sale_ref(local_sale_ref):
    local_sale_ref = cstr(local_sale_ref or "").strip()
    if not local_sale_ref or not _relay_workflow_has_field("local_sale_ref"):
        return None

    state_name = frappe.db.exists(
        "POS Relay Workflow State", {"local_sale_ref": local_sale_ref}
    )
    if not state_name:
        return None

    sales_invoice = cstr(
        frappe.db.get_value("POS Relay Workflow State", state_name, "sales_invoice")
        or ""
    ).strip()
    if sales_invoice and frappe.db.exists("Sales Invoice", sales_invoice):
        return frappe.get_doc("Sales Invoice", sales_invoice)
    return None


def _set_relay_state_local_sale_ref(state_doc, local_sale_ref):
    local_sale_ref = cstr(local_sale_ref or "").strip()
    if not state_doc or not local_sale_ref or not _relay_workflow_has_field("local_sale_ref"):
        return state_doc

    state_doc.set("local_sale_ref", local_sale_ref)
    state_doc.flags.ignore_permissions = True
    state_doc.save()
    return state_doc


def _get_invoice_linked_sales_order_name(invoice_doc):
    if not invoice_doc:
        return ""
    for row in (invoice_doc.get("items") or []):
        so_name = cstr(
            (row.get("sales_order") if hasattr(row, "get") else getattr(row, "sales_order", ""))
            or ""
        ).strip()
        if so_name:
            return so_name
    return ""


def _get_relay_state_doc_for_sales_order(
    sales_order_name, pos_profile=None, pos_opening_shift=None, business_date=None
):
    if not sales_order_name or not _relay_workflow_has_field("sales_order"):
        return None

    state_name = frappe.db.exists(
        "POS Relay Workflow State", {"sales_order": sales_order_name}
    )
    if state_name:
        return frappe.get_doc("POS Relay Workflow State", state_name)

    payload = {
        "doctype": "POS Relay Workflow State",
        "token_id": cstr(sales_order_name),
        "token_status": "Draft",
        "picking_status": "Not Started",
        "dispatch_status": "Pending",
        "last_sync_status": "Not Applicable",
    }
    if pos_profile:
        payload["pos_profile"] = pos_profile
    if _relay_workflow_has_field("sales_order"):
        payload["sales_order"] = sales_order_name
    if _relay_workflow_has_field("pos_opening_shift") and pos_opening_shift:
        payload["pos_opening_shift"] = pos_opening_shift
    if _relay_workflow_has_field("business_date") and business_date:
        payload["business_date"] = cstr(business_date)
    return frappe.get_doc(payload)


def _apply_relay_workflow_state_updates(
    state_doc,
    token_status=None,
    picking_status=None,
    dispatch_status=None,
    exceptions_note=None,
    is_offline_recorded=None,
    last_sync_status=None,
    sync_error=None,
    pos_profile=None,
    token_id=None,
    sales_invoice=None,
    sales_order=None,
    pos_opening_shift=None,
    business_date=None,
    set_order_taken_at=False,
):
    if not state_doc:
        return None

    now_ts = now_datetime()
    prev_token_status = cstr(state_doc.get("token_status") or "")
    prev_picking_status = cstr(state_doc.get("picking_status") or "")
    prev_dispatch_status = cstr(state_doc.get("dispatch_status") or "")
    status_changed = False

    if pos_profile:
        state_doc.pos_profile = pos_profile

    if token_id:
        state_doc.token_id = cstr(token_id)

    if sales_invoice:
        state_doc.sales_invoice = sales_invoice

    _set_state_field_if_exists(state_doc, "sales_order", sales_order)
    _set_state_field_if_exists(state_doc, "pos_opening_shift", pos_opening_shift)
    _set_state_field_if_exists(state_doc, "business_date", cstr(business_date) if business_date else None)

    if set_order_taken_at and _relay_workflow_has_field("order_taken_at") and not state_doc.get("order_taken_at"):
        state_doc.set("order_taken_at", now_ts)

    if token_status in RELAY_TOKEN_STATUSES and token_status != prev_token_status:
        state_doc.token_status = token_status
        status_changed = True
        if token_status == "Paid" and _relay_workflow_has_field("paid_at") and not state_doc.get("paid_at"):
            state_doc.set("paid_at", now_ts)

    if picking_status in RELAY_PICKING_STATUSES and picking_status != prev_picking_status:
        state_doc.picking_status = picking_status
        status_changed = True
        if (
            picking_status == "In Progress"
            and _relay_workflow_has_field("pick_started_at")
            and not state_doc.get("pick_started_at")
        ):
            state_doc.set("pick_started_at", now_ts)
        if picking_status == "Picked" and _relay_workflow_has_field("picked_at"):
            state_doc.set("picked_at", now_ts)

    if dispatch_status in RELAY_DISPATCH_STATUSES and dispatch_status != prev_dispatch_status:
        state_doc.dispatch_status = dispatch_status
        status_changed = True
        if dispatch_status == "Released":
            if state_doc.get("released_by") in (None, ""):
                state_doc.released_by = frappe.session.user
            if not state_doc.get("released_at"):
                state_doc.released_at = now_ts

    if exceptions_note is not None:
        state_doc.exceptions_note = exceptions_note

    if is_offline_recorded is not None:
        state_doc.is_offline_recorded = cint(is_offline_recorded)

    if last_sync_status is not None:
        state_doc.last_sync_status = last_sync_status

    if sync_error is not None:
        state_doc.sync_error = sync_error

    if _relay_workflow_has_field("status_changed_at"):
        if status_changed:
            state_doc.set("status_changed_at", now_ts)
        elif state_doc.is_new() and not state_doc.get("status_changed_at"):
            state_doc.set("status_changed_at", now_ts)

    state_doc.flags.ignore_permissions = True
    state_doc.save()
    return state_doc


def _upsert_relay_workflow_state_for_sales_order(
    sales_order_doc,
    pos_profile=None,
    pos_opening_shift=None,
    token_status="Draft",
):
    if not sales_order_doc or not sales_order_doc.get("name"):
        return None
    if not _relay_workflow_doctype_exists():
        return None
    if pos_profile and not _is_relay_workflow_enabled(pos_profile):
        return None

    so_business_date = cstr(sales_order_doc.get("transaction_date") or nowdate())
    state_doc = _get_relay_state_doc_for_sales_order(
        sales_order_doc.name,
        pos_profile=pos_profile,
        pos_opening_shift=pos_opening_shift,
        business_date=so_business_date,
    )
    if not state_doc:
        return None

    return _apply_relay_workflow_state_updates(
        state_doc,
        pos_profile=pos_profile,
        token_id=sales_order_doc.name,
        sales_order=sales_order_doc.name,
        pos_opening_shift=pos_opening_shift,
        business_date=so_business_date,
        token_status=token_status if token_status in RELAY_TOKEN_STATUSES else None,
        picking_status="Not Started",
        dispatch_status="Pending",
        set_order_taken_at=True,
    )


def _get_edge_relay_base_url():
    relay_base_url = cstr(
        frappe.conf.get("posa_edge_relay_url")
        or frappe.conf.get("edge_relay_base_url")
        or ""
    ).strip()
    return relay_base_url.rstrip("/")


def _get_pos_profile_edge_relay_url(pos_profile):
    if not pos_profile:
        return ""
    relay_url = cstr(
        frappe.get_cached_value("POS Profile", pos_profile, "custom_edge_relay_url") or ""
    ).strip()
    return relay_url.rstrip("/")


def _get_pos_profile_field_if_exists(pos_profile, fieldname, default=None):
    if not pos_profile or not fieldname:
        return default

    try:
        meta = frappe.get_meta("POS Profile")
        if not meta or not meta.has_field(fieldname):
            return default
        return frappe.get_cached_value("POS Profile", pos_profile, fieldname)
    except Exception:
        return default


def _get_pos_profile_relay_connectivity_mode(pos_profile):
    mode = cstr(
        _get_pos_profile_field_if_exists(
            pos_profile, "posa_edge_relay_connectivity_mode", "cloud_checked"
        )
        or "cloud_checked"
    ).strip()
    if mode not in ("cloud_checked", "lan_only_browser_checked"):
        mode = "cloud_checked"
    return mode


def _get_pos_profile_allow_cloud_fallback_when_relay_down(pos_profile):
    return cint(
        _get_pos_profile_field_if_exists(
            pos_profile, "posa_allow_cloud_fallback_when_relay_down", 0
        )
        or 0
    ) == 1


def _is_private_lan_host(hostname):
    host = cstr(hostname or "").strip().lower()
    if not host:
        return False

    if host in ("localhost", "127.0.0.1"):
        return True

    return (
        host.startswith("10.")
        or host.startswith("192.168.")
        or host.startswith("172.16.")
        or host.startswith("172.17.")
        or host.startswith("172.18.")
        or host.startswith("172.19.")
        or host.startswith("172.2")
        or host.startswith("172.30.")
        or host.startswith("172.31.")
    )


@frappe.whitelist()
def get_relay_connectivity_status(pos_profile):
    pos_profile = cstr(pos_profile or "").strip()
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))

    connectivity_mode = _get_pos_profile_relay_connectivity_mode(pos_profile)
    allow_cloud_fallback_when_relay_down = (
        _get_pos_profile_allow_cloud_fallback_when_relay_down(pos_profile)
    )

    def attach_policy(payload):
        result = dict(payload or {})
        result["connectivity_mode"] = connectivity_mode
        result["allow_cloud_fallback_when_relay_down"] = bool(
            allow_cloud_fallback_when_relay_down
        )
        result["submit_gate_source"] = (
            "browser_lan"
            if connectivity_mode == "lan_only_browser_checked"
            else "cloud_backend"
        )
        result["cloud_connected"] = bool(result.get("connected"))
        result["cloud_status"] = cstr(result.get("status") or "")
        result["cloud_message"] = cstr(result.get("message") or "")
        result["cloud_http_status"] = result.get("http_status")
        result["cloud_checked_at"] = cstr(result.get("checked_at") or "")
        debug = result.get("debug") or {}
        if isinstance(debug, dict):
            debug = dict(debug)
            debug["connectivity_mode"] = connectivity_mode
            if connectivity_mode == "lan_only_browser_checked":
                debug["mode_note"] = _(
                    "LAN-only mode expects the POS browser to check relay /health over LAN HTTPS; cloud-side relay reachability remains diagnostic only."
                )
            result["debug"] = debug
        return result

    if not _is_relay_workflow_enabled(pos_profile):
        return attach_policy({
            "enabled": False,
            "configured": False,
            "connected": False,
            "status": "disabled",
            "message": _("Relay workflow is disabled for this POS Profile."),
            "checked_at": str(now_datetime()),
        })

    profile_relay_url = _get_pos_profile_edge_relay_url(pos_profile)
    site_relay_url = _get_edge_relay_base_url()
    relay_base_url = profile_relay_url or site_relay_url

    if not relay_base_url:
        return attach_policy({
            "enabled": True,
            "configured": False,
            "connected": False,
            "status": "not_configured",
            "relay_url": "",
            "relay_source": "none",
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _(
                "Edge Relay URL is not configured on this POS Profile. Set Edge Relay URL on POS Profile or fallback key 'posa_edge_relay_url' in site_config.json."
            ),
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": "",
                "hint": _(
                    "Open POS Profile and set 'Edge Relay URL', for example http://192.168.50.10:8787"
                ),
            },
        })

    timeout_seconds = max(1, cint(frappe.conf.get("posa_edge_relay_timeout") or 3))
    health_url = "{0}/health".format(relay_base_url)
    relay_source = "pos_profile" if profile_relay_url else "site_config"
    parsed_url = urlparse(relay_base_url)
    relay_host = parsed_url.hostname or ""
    is_private_lan = _is_private_lan_host(relay_host)

    try:
        response = requests.get(health_url, timeout=timeout_seconds)
        response.raise_for_status()

        health_payload = {}
        try:
            health_payload = response.json() or {}
        except Exception:
            health_payload = {}

        relay_ok = bool(health_payload.get("ok")) if isinstance(health_payload, dict) else True
        return attach_policy({
            "enabled": True,
            "configured": True,
            "connected": relay_ok,
            "status": "online" if relay_ok else "offline",
            "relay_url": relay_base_url,
            "relay_source": relay_source,
            "relay_host": relay_host,
            "relay_host_type": "private_lan" if is_private_lan else "public_or_routable",
            "relay_config_identified": True,
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _("Edge Relay reachable.")
            if relay_ok
            else _("Edge Relay responded, but reported unhealthy status."),
            "http_status": response.status_code,
            "queue": health_payload.get("queue", {}) if isinstance(health_payload, dict) else {},
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": health_url,
                "timeout_seconds": timeout_seconds,
                "cloud_reachability_note": _(
                    "Frappe Cloud checks reachability from cloud network, not from your local browser."
                ),
            },
        })
    except requests.exceptions.Timeout:
        return attach_policy({
            "enabled": True,
            "configured": True,
            "connected": False,
            "status": "timeout",
            "relay_url": relay_base_url,
            "relay_source": relay_source,
            "relay_host": relay_host,
            "relay_host_type": "private_lan" if is_private_lan else "public_or_routable",
            "relay_config_identified": True,
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _(
                "Timed out while connecting to Edge Relay. Check network route/firewall and relay service status."
            ),
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": health_url,
                "timeout_seconds": timeout_seconds,
                "hint": _("Try opening the relay URL from the ERP server network."),
                "cloud_reachability_note": _(
                    "If this is a LAN IP like 192.168.x.x, Frappe Cloud cannot reach it without VPN/tunnel/public routing."
                ),
            },
        })
    except requests.exceptions.ConnectionError:
        return attach_policy({
            "enabled": True,
            "configured": True,
            "connected": False,
            "status": "connection_error",
            "relay_url": relay_base_url,
            "relay_source": relay_source,
            "relay_host": relay_host,
            "relay_host_type": "private_lan" if is_private_lan else "public_or_routable",
            "relay_config_identified": True,
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _(
                "Connection to Edge Relay failed. Verify host/IP, port, and whether relay app is running."
            ),
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": health_url,
                "hint": _("Ensure relay machine allows inbound traffic on relay port."),
                "cloud_reachability_note": _(
                    "Configured relay is identified, but cloud reachability still requires network path from Frappe Cloud."
                ),
            },
        })
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if getattr(exc, "response", None) else None
        return attach_policy({
            "enabled": True,
            "configured": True,
            "connected": False,
            "status": "http_error",
            "relay_url": relay_base_url,
            "relay_source": relay_source,
            "relay_host": relay_host,
            "relay_host_type": "private_lan" if is_private_lan else "public_or_routable",
            "relay_config_identified": True,
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _("Edge Relay returned HTTP error status."),
            "http_status": status_code,
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": health_url,
                "hint": _("Check relay app logs and health endpoint response."),
                "cloud_reachability_note": _(
                    "Configured relay is identified; HTTP error means target responded but health endpoint returned non-2xx."
                ),
            },
        })
    except Exception:
        return attach_policy({
            "enabled": True,
            "configured": True,
            "connected": False,
            "status": "offline",
            "relay_url": relay_base_url,
            "relay_source": relay_source,
            "relay_host": relay_host,
            "relay_host_type": "private_lan" if is_private_lan else "public_or_routable",
            "relay_config_identified": True,
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _("Edge Relay is unreachable from this server."),
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": health_url,
                "cloud_reachability_note": _(
                    "Configured relay is identified, but no working route from Frappe Cloud to relay host."
                ),
            },
        })


def _get_relay_state_doc(invoice_doc):
    state_name = frappe.db.exists(
        "POS Relay Workflow State", {"sales_invoice": invoice_doc.name}
    )
    if state_name:
        return frappe.get_doc("POS Relay Workflow State", state_name)

    linked_sales_order = _get_invoice_linked_sales_order_name(invoice_doc)
    if linked_sales_order and _relay_workflow_has_field("sales_order"):
        state_name = frappe.db.exists(
            "POS Relay Workflow State", {"sales_order": linked_sales_order}
        )
        if state_name:
            return frappe.get_doc("POS Relay Workflow State", state_name)

    payload = {
        "doctype": "POS Relay Workflow State",
        "sales_invoice": invoice_doc.name,
        "pos_profile": invoice_doc.pos_profile,
        "token_id": cstr(linked_sales_order or invoice_doc.name),
        "token_status": "Draft",
        "picking_status": "Not Started",
        "dispatch_status": "Pending",
        "last_sync_status": "Not Applicable",
    }
    if linked_sales_order and _relay_workflow_has_field("sales_order"):
        payload["sales_order"] = linked_sales_order
    if _relay_workflow_has_field("pos_opening_shift") and invoice_doc.get("posa_pos_opening_shift"):
        payload["pos_opening_shift"] = invoice_doc.get("posa_pos_opening_shift")
    if _relay_workflow_has_field("business_date"):
        payload["business_date"] = cstr(invoice_doc.get("posting_date") or nowdate())
    return frappe.get_doc(payload)


def _upsert_relay_workflow_state(
    invoice_doc,
    token_status=None,
    picking_status=None,
    dispatch_status=None,
    exceptions_note=None,
    is_offline_recorded=None,
    last_sync_status=None,
    sync_error=None,
):
    if not invoice_doc or not invoice_doc.get("name") or not invoice_doc.get("pos_profile"):
        return None

    if not _relay_workflow_doctype_exists():
        return None

    if not _is_relay_workflow_enabled(invoice_doc.pos_profile):
        return None

    state_doc = _get_relay_state_doc(invoice_doc)
    linked_sales_order = _get_invoice_linked_sales_order_name(invoice_doc)
    pos_opening_shift = invoice_doc.get("posa_pos_opening_shift")
    token_id = linked_sales_order or cstr(invoice_doc.name)[-5:]
    business_date = cstr(invoice_doc.get("posting_date") or nowdate())
    if linked_sales_order:
        try:
            so_txn_date = frappe.get_cached_value("Sales Order", linked_sales_order, "transaction_date")
            if so_txn_date:
                business_date = cstr(so_txn_date)
        except Exception:
            pass

    return _apply_relay_workflow_state_updates(
        state_doc,
        token_status=token_status,
        picking_status=picking_status,
        dispatch_status=dispatch_status,
        exceptions_note=exceptions_note,
        is_offline_recorded=is_offline_recorded,
        last_sync_status=last_sync_status,
        sync_error=sync_error,
        pos_profile=invoice_doc.pos_profile,
        token_id=token_id,
        sales_invoice=invoice_doc.name,
        sales_order=linked_sales_order,
        pos_opening_shift=pos_opening_shift,
        business_date=business_date,
    )


@frappe.whitelist()
def get_relay_workflow_state(sales_invoice):
    if not _relay_workflow_doctype_exists():
        return {}

    invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    if not _is_relay_workflow_enabled(invoice_doc.pos_profile):
        return {}

    state_doc = _upsert_relay_workflow_state(invoice_doc)
    return state_doc.as_dict() if state_doc else {}


@frappe.whitelist()
def get_relay_fulfillment_detail(sales_invoice, pos_profile=None, pos_profile_id=None):
    if not _relay_workflow_doctype_exists():
        return {}

    invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    effective_pos_profile = _resolve_relay_workflow_pos_profile(
        invoice_doc, pos_profile, pos_profile_id
    )
    if not _is_relay_workflow_enabled(effective_pos_profile):
        frappe.throw(
            _("Relay workflow is not enabled for POS Profile {0}").format(
                effective_pos_profile or invoice_doc.pos_profile
            )
        )

    state_doc = _upsert_relay_workflow_state(invoice_doc, token_status="Paid")
    state = state_doc.as_dict() if state_doc else {}
    sale = {
        "local_sale_ref": invoice_doc.name,
        "token_id": state.get("token_id") or invoice_doc.name,
        "pos_profile_id": effective_pos_profile or invoice_doc.pos_profile,
        "customer_id": invoice_doc.customer,
        "customer_name": invoice_doc.customer_name,
        "currency": invoice_doc.currency,
        "grand_total": invoice_doc.grand_total,
        "paid": 1 if invoice_doc.docstatus == 1 else 0,
        "pick_status": _cloud_pick_to_relay_status(state.get("picking_status")),
        "dispatch_status": cstr(state.get("dispatch_status") or "Pending").upper(),
        "released_at": state.get("released_at"),
        "dispatch_proof": state.get("dispatch_proof") or state.get("dispatch_proof_payload") or {},
        "dispatch_proof_payload": state.get("dispatch_proof_payload") or state.get("dispatch_proof") or {},
        "cashier_adjustment_required": cint(state.get("cashier_adjustment_required") or 0),
        "created_at": invoice_doc.creation,
        "updated_at": state.get("modified") or invoice_doc.modified,
    }
    lines = []
    for row in invoice_doc.items:
        conversion_factor = flt(row.get("conversion_factor") or 1) or 1
        qty = flt(row.get("qty") or 0)
        stock_qty = flt(row.get("stock_qty") or (qty * conversion_factor))
        lines.append(
            {
                "id": row.idx,
                "item_code": row.item_code,
                "item_name": row.item_name,
                "qty": qty,
                "uom": row.uom,
                "rate": row.rate,
                "amount": row.amount,
                "pick_status": sale["pick_status"],
                "payload": {
                    "stock_uom": row.stock_uom,
                    "stock_qty": stock_qty,
                    "conversion_factor": conversion_factor,
                },
            }
        )
    return {
        "ok": True,
        "sale": sale,
        "lines": lines,
        "pick_events": [],
        "dispatch_events": [],
        "outbox_events": [],
        "workflow_state": state,
    }


def _cloud_pick_to_relay_status(picking_status):
    status = cstr(picking_status or "").strip()
    if status == "In Progress":
        return "PICK_IN_PROGRESS"
    if status == "Picked":
        return "PICKED_READY_FOR_RELEASE"
    if status == "Exception":
        return "PICK_EXCEPTION"
    return "PAID_PENDING_PICK"


@frappe.whitelist()
def get_relay_pick_queue(pos_profile=None, picking_status=None, dispatch_status=None, limit_page_length=50):
    if not _relay_workflow_doctype_exists():
        return []

    filters = {"token_status": "Paid"}
    if pos_profile:
        filters["pos_profile"] = pos_profile
    if picking_status:
        filters["picking_status"] = picking_status
    if dispatch_status:
        filters["dispatch_status"] = dispatch_status
    else:
        filters["dispatch_status"] = ["!=", "Released"]

    return frappe.get_all(
        "POS Relay Workflow State",
        filters=filters,
        fields=[
            "name",
            "sales_invoice",
            "pos_profile",
            "token_id",
            "token_status",
            "picking_status",
            "dispatch_status",
            "exceptions_note",
            "released_by",
            "released_at",
            "modified",
        ],
        order_by="modified asc",
        limit_page_length=cint(limit_page_length) or 50,
    )


def _normalize_monitor_display_status(row):
    token_status = cstr((row or {}).get("token_status") or "")
    picking_status = cstr((row or {}).get("picking_status") or "")
    dispatch_status = cstr((row or {}).get("dispatch_status") or "")

    if dispatch_status == "Released":
        return "Dispatched"
    if dispatch_status == "On Hold" or picking_status == "Exception":
        return "On Hold"
    if token_status != "Paid":
        return "Unpaid"
    if picking_status == "In Progress":
        return "Picking"
    if picking_status == "Picked":
        return "Picked"
    return "Paid"


@frappe.whitelist()
def get_relay_workflow_monitor_board(
    pos_profile=None,
    business_date=None,
    scope_mode=None,
    pos_opening_shift=None,
    mine_only=0,
    include_released=0,
    limit_page_length=200,
):
    if not _relay_workflow_doctype_exists():
        return {"summary": {"pending_count": 0, "server_time": str(now_datetime())}, "rows": []}

    state_fields = [
        "name",
        "sales_invoice",
        "pos_profile",
        "token_id",
        "token_status",
        "picking_status",
        "dispatch_status",
        "exceptions_note",
        "released_by",
        "released_at",
        "modified",
    ]
    for maybe_field in (
        "sales_order",
        "business_date",
        "pos_opening_shift",
        "status_changed_at",
        "order_taken_at",
        "paid_at",
        "pick_started_at",
        "picked_at",
        "dispatch_exception_state",
        "cashier_adjustment_required",
        "dispatch_proof",
        "dispatch_proof_payload",
    ):
        if _relay_workflow_has_field(maybe_field):
            state_fields.append(maybe_field)

    scope_mode = cstr(scope_mode or "business_date").strip().lower()
    if scope_mode not in ("business_date", "opening_shift"):
        scope_mode = "business_date"
    target_business_date = cstr(business_date or nowdate()).strip() or nowdate()

    filters = {}
    if pos_profile:
        filters["pos_profile"] = pos_profile
    if (
        scope_mode == "opening_shift"
        and _relay_workflow_has_field("pos_opening_shift")
        and pos_opening_shift
    ):
        filters["pos_opening_shift"] = pos_opening_shift
    if not cint(include_released):
        filters["dispatch_status"] = ["!=", "Released"]

    state_rows = frappe.get_all(
        "POS Relay Workflow State",
        filters=filters,
        fields=state_fields,
        order_by="modified asc",
        limit_page_length=max(1, cint(limit_page_length) or 200),
    )

    so_names = sorted(
        {cstr((row.get("sales_order") or "")).strip() for row in state_rows if row.get("sales_order")}
    )
    si_names = sorted(
        {cstr((row.get("sales_invoice") or "")).strip() for row in state_rows if row.get("sales_invoice")}
    )

    so_map = {}
    if so_names:
        for doc in frappe.get_all(
            "Sales Order",
            filters={"name": ["in", so_names]},
            fields=[
                "name",
                "customer",
                "customer_name",
                "grand_total",
                "currency",
                "owner",
                "transaction_date",
                "creation",
                "modified",
            ],
            limit_page_length=len(so_names),
        ):
            so_map[doc.name] = doc

    si_map = {}
    if si_names:
        for doc in frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", si_names]},
            fields=[
                "name",
                "customer",
                "customer_name",
                "grand_total",
                "currency",
                "owner",
                "posting_date",
                "posting_time",
                "creation",
                "modified",
                "posa_pos_opening_shift",
            ],
            limit_page_length=len(si_names),
        ):
            si_map[doc.name] = doc

    user_ids = set()
    for so in so_map.values():
        if so.get("owner"):
            user_ids.add(so.get("owner"))
    for si in si_map.values():
        if si.get("owner"):
            user_ids.add(si.get("owner"))

    user_map = {}
    if user_ids:
        for user in frappe.get_all(
            "User",
            filters={"name": ["in", list(user_ids)]},
            fields=["name", "full_name", "first_name", "last_name"],
            limit_page_length=len(user_ids),
        ):
            full_name = cstr(user.get("full_name") or "").strip()
            if not full_name:
                full_name = " ".join(
                    [cstr(user.get("first_name") or "").strip(), cstr(user.get("last_name") or "").strip()]
                ).strip()
            user_map[user.name] = full_name or user.name

    mine_only = cint(mine_only)
    current_user = frappe.session.user

    rows = []
    status_counts = {}

    def _derived_business_date(row_obj, so_doc_obj=None, si_doc_obj=None):
        if row_obj and row_obj.get("business_date"):
            return cstr(row_obj.get("business_date"))
        if so_doc_obj and so_doc_obj.get("transaction_date"):
            return cstr(so_doc_obj.get("transaction_date"))
        if si_doc_obj and si_doc_obj.get("posting_date"):
            return cstr(si_doc_obj.get("posting_date"))
        raw_dt = (row_obj or {}).get("order_taken_at") or (row_obj or {}).get("modified")
        if raw_dt:
            raw_text = cstr(raw_dt)
            if " " in raw_text:
                return raw_text.split(" ", 1)[0]
            if "T" in raw_text:
                return raw_text.split("T", 1)[0]
        return ""

    for row in state_rows:
        so_doc = so_map.get(row.get("sales_order")) if row.get("sales_order") else None
        si_doc = si_map.get(row.get("sales_invoice")) if row.get("sales_invoice") else None

        row_business_date = _derived_business_date(row, so_doc, si_doc)
        if scope_mode == "business_date" and target_business_date:
            if row_business_date and row_business_date != target_business_date:
                continue

        sales_associate_user = cstr((so_doc or {}).get("owner") or "").strip()
        if not sales_associate_user and si_doc and row.get("token_status") != "Paid":
            sales_associate_user = cstr(si_doc.get("owner") or "").strip()

        if mine_only and sales_associate_user != current_user:
            continue

        sales_associate_name = user_map.get(sales_associate_user, sales_associate_user)
        customer_name = (
            (so_doc or {}).get("customer_name")
            or (si_doc or {}).get("customer_name")
            or ""
        )
        grand_total = (so_doc or {}).get("grand_total")
        if grand_total in (None, ""):
            grand_total = (si_doc or {}).get("grand_total")
        currency = (so_doc or {}).get("currency") or (si_doc or {}).get("currency") or ""

        order_taken_at = row.get("order_taken_at") or (so_doc or {}).get("creation") or (si_doc or {}).get("creation")
        status_changed_at = row.get("status_changed_at") or row.get("modified")
        effective_shift = row.get("pos_opening_shift") or (si_doc or {}).get("posa_pos_opening_shift") or ""

        monitor_row = {
            "workflow_state": row.get("name"),
            "sales_order": row.get("sales_order") or "",
            "sales_invoice": row.get("sales_invoice") or "",
            "token_id": row.get("token_id") or "",
            "customer_name": customer_name,
            "grand_total": grand_total,
            "currency": currency,
            "sales_associate_user": sales_associate_user,
            "sales_associate_name": sales_associate_name,
            "business_date": row_business_date or target_business_date,
            "pos_opening_shift": effective_shift,
            "token_status": row.get("token_status"),
            "picking_status": row.get("picking_status"),
            "dispatch_status": row.get("dispatch_status"),
            "display_status": _normalize_monitor_display_status(row),
            "order_taken_at": order_taken_at,
            "paid_at": row.get("paid_at"),
            "pick_started_at": row.get("pick_started_at"),
            "picked_at": row.get("picked_at"),
            "released_at": row.get("released_at"),
            "status_changed_at": status_changed_at,
            "dispatch_exception_state": row.get("dispatch_exception_state") or "NONE",
            "cashier_adjustment_required": cint(row.get("cashier_adjustment_required") or 0),
            "dispatch_proof": row.get("dispatch_proof")
            or row.get("dispatch_proof_payload")
            or {},
        }
        rows.append(monitor_row)
        status_counts[monitor_row["display_status"]] = status_counts.get(monitor_row["display_status"], 0) + 1

    def _sort_key(item):
        return cstr(item.get("status_changed_at") or item.get("order_taken_at") or "")

    rows.sort(key=_sort_key)

    return {
        "summary": {
            "pending_count": len(rows),
            "status_counts": status_counts,
            "server_time": str(now_datetime()),
            "scope_mode": scope_mode,
            "business_date": target_business_date if scope_mode == "business_date" else "",
            "pos_profile": pos_profile or "",
        },
        "rows": rows,
    }


@frappe.whitelist()
def update_relay_picking_status(sales_invoice, picking_status, exceptions_note=None, pos_profile=None, pos_profile_id=None):
    _require_operational_role_for_action(
        ("cline-Picker", "cline-Supervisor"),
        "update relay picking status",
        allow_relay_sync=True,
    )

    if picking_status not in RELAY_PICKING_STATUSES:
        frappe.throw(_("Invalid picking status: {0}").format(picking_status))

    if not _relay_workflow_doctype_exists():
        frappe.throw(_("Relay workflow state DocType is missing. Please run migration."))

    invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    effective_pos_profile = _resolve_relay_workflow_pos_profile(
        invoice_doc, pos_profile, pos_profile_id
    )
    if effective_pos_profile and not cstr(invoice_doc.get("pos_profile") or "").strip():
        invoice_doc.pos_profile = effective_pos_profile

    if not _is_relay_workflow_enabled(effective_pos_profile):
        frappe.throw(
            _("Relay workflow is not enabled for POS Profile {0}").format(
                effective_pos_profile or invoice_doc.pos_profile
            )
        )

    current_state = _get_relay_state_doc(invoice_doc)
    if current_state.dispatch_status == "Released":
        next_dispatch_status = "Released"
    elif picking_status == "Exception":
        next_dispatch_status = "On Hold"
    else:
        next_dispatch_status = "Pending"

    state_doc = _upsert_relay_workflow_state(
        invoice_doc,
        token_status="Paid" if invoice_doc.docstatus == 1 else "Draft",
        picking_status=picking_status,
        dispatch_status=next_dispatch_status,
        exceptions_note=exceptions_note,
    )
    return state_doc.as_dict() if state_doc else {}


@frappe.whitelist()
def release_relay_dispatch(sales_invoice, allow_exception_release=0, pos_profile=None, pos_profile_id=None):
    _require_operational_role_for_action(
        ("cline-Dispatch", "cline-Supervisor"),
        "release relay dispatch",
        allow_relay_sync=True,
    )

    if not _relay_workflow_doctype_exists():
        frappe.throw(_("Relay workflow state DocType is missing. Please run migration."))

    invoice_doc = frappe.get_doc("Sales Invoice", sales_invoice)
    effective_pos_profile = _resolve_relay_workflow_pos_profile(
        invoice_doc, pos_profile, pos_profile_id
    )
    if effective_pos_profile and not cstr(invoice_doc.get("pos_profile") or "").strip():
        invoice_doc.pos_profile = effective_pos_profile

    if not _is_relay_workflow_enabled(effective_pos_profile):
        frappe.throw(
            _("Relay workflow is not enabled for POS Profile {0}").format(
                effective_pos_profile or invoice_doc.pos_profile
            )
        )

    if invoice_doc.docstatus != 1:
        frappe.throw(_("Only submitted Sales Invoices can be released for dispatch."))

    state_doc = _upsert_relay_workflow_state(invoice_doc, token_status="Paid")
    if not state_doc:
        frappe.throw(_("Unable to create relay workflow state."))

    if state_doc.dispatch_status == "Released":
        return state_doc.as_dict()

    allow_exception_release = cint(allow_exception_release)
    can_release = state_doc.picking_status == "Picked" or (
        allow_exception_release and state_doc.picking_status == "Exception"
    )

    if not can_release:
        frappe.throw(
            _(
                "Dispatch release requires Picking status 'Picked'. Use supervisor override for exceptions."
            )
        )

    state_doc = _upsert_relay_workflow_state(invoice_doc, dispatch_status="Released")
    return state_doc.as_dict() if state_doc else {}

def add_taxes_from_tax_template(item, parent_doc):
    accounts_settings = frappe.get_cached_doc("Accounts Settings")
    add_taxes_from_item_tax_template = (
        accounts_settings.add_taxes_from_item_tax_template
    )
    if item.get("item_tax_template") and add_taxes_from_item_tax_template:
        item_tax_template = item.get("item_tax_template")
        taxes_template_details = frappe.get_all(
            "Item Tax Template Detail",
            filters={"parent": item_tax_template},
            fields=["tax_type"],
        )

        for tax_detail in taxes_template_details:
            tax_type = tax_detail.get("tax_type")

            found = any(tax.account_head == tax_type for tax in parent_doc.taxes)
            if not found:
                tax_row = parent_doc.append("taxes", {})
                tax_row.update(
                    {
                        "description": str(tax_type).split(" - ")[0],
                        "charge_type": "On Net Total",
                        "account_head": tax_type,
                    }
                )

                if parent_doc.doctype == "Purchase Order":
                    tax_row.update({"category": "Total", "add_deduct_tax": "Add"})
                tax_row.db_insert()


@frappe.whitelist()
def update_invoice_from_order(data):
    data = json.loads(data)
    invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
    invoice_doc.update(data)
    invoice_doc.save()
    return invoice_doc


@frappe.whitelist()
def create_sales_order_token(data):
    role = _require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "create sales order tokens",
        allow_relay_sync=True,
    )

    if isinstance(data, str):
        data = json.loads(data or "{}")
    data = data or {}

    pos_profile = cstr(data.get("pos_profile") or "").strip()
    pos_opening_shift = cstr(data.get("pos_opening_shift") or "").strip()
    company = cstr(data.get("company") or "").strip()
    customer = cstr(data.get("customer") or "").strip()
    order_name = cstr(data.get("order_name") or data.get("posa_order_name") or "").strip()
    items = data.get("items") or []

    if not pos_profile:
        frappe.throw(_("POS Profile is required to create Sales Order token."))
    if not company:
        frappe.throw(_("Company is required to create Sales Order token."))
    if not customer:
        frappe.throw(_("Customer is required to create Sales Order token."))
    if role == "cline-Sales Associate" and not order_name:
        frappe.throw(_("Order Name is required to create Sales Order token."))
    if not items:
        frappe.throw(_("At least one item is required to create Sales Order token."))

    if not cint(frappe.get_cached_value("POS Profile", pos_profile, "posa_allow_sales_order") or 0):
        frappe.throw(
            _("POS Profile {0} is not configured to allow Sales Orders.").format(pos_profile)
        )

    transaction_date = cstr(data.get("posting_date") or nowdate())
    sales_order_doc = frappe.new_doc("Sales Order")
    sales_order_doc.company = company
    sales_order_doc.customer = customer
    sales_order_doc.transaction_date = transaction_date
    sales_order_doc.ignore_pricing_rule = 1

    # Standard optional fields that may be present on POS payload
    if data.get("currency"):
        sales_order_doc.currency = data.get("currency")
    if data.get("campaign"):
        sales_order_doc.campaign = data.get("campaign")

    selling_price_list = frappe.get_cached_value("POS Profile", pos_profile, "selling_price_list")
    profile_warehouse = frappe.get_cached_value("POS Profile", pos_profile, "warehouse")
    profile_so_naming_series = cstr(
        frappe.get_cached_value("POS Profile", pos_profile, "posa_sales_order_naming_series")
        or ""
    ).strip()
    if selling_price_list and getattr(sales_order_doc, "selling_price_list", None) in (None, ""):
        sales_order_doc.selling_price_list = selling_price_list
    if profile_warehouse and sales_order_doc.meta.has_field("set_warehouse"):
        sales_order_doc.set_warehouse = profile_warehouse
    if profile_so_naming_series and sales_order_doc.meta.has_field("naming_series"):
        sales_order_doc.naming_series = profile_so_naming_series

    # POSAwesome custom fields on Sales Order (if migrated)
    if sales_order_doc.meta.has_field("posa_notes"):
        sales_order_doc.posa_notes = data.get("posa_notes") or ""
    if sales_order_doc.meta.has_field("posa_order_name"):
        sales_order_doc.posa_order_name = order_name
    if sales_order_doc.meta.has_field("posa_offers") and data.get("posa_offers") is not None:
        sales_order_doc.set("posa_offers", data.get("posa_offers") or [])
    if sales_order_doc.meta.has_field("posa_coupons") and data.get("posa_coupons") is not None:
        sales_order_doc.set("posa_coupons", data.get("posa_coupons") or [])
    if sales_order_doc.meta.has_field("posa_delivery_charges") and data.get("posa_delivery_charges"):
        sales_order_doc.posa_delivery_charges = data.get("posa_delivery_charges")
    if sales_order_doc.meta.has_field("posa_delivery_charges_rate") and data.get("posa_delivery_charges_rate") is not None:
        sales_order_doc.posa_delivery_charges_rate = data.get("posa_delivery_charges_rate")

    so_item_meta = frappe.get_meta("Sales Order Item")
    for raw in items:
        item_code = cstr((raw or {}).get("item_code") or "").strip()
        if not item_code:
            continue

        row = sales_order_doc.append("items", {})
        row.item_code = item_code
        row.qty = flt((raw or {}).get("qty") or 0)
        row.uom = (raw or {}).get("uom")
        row_warehouse = cstr(
            (raw or {}).get("delivery_warehouse")
            or (raw or {}).get("warehouse")
            or profile_warehouse
            or ""
        ).strip()
        if row_warehouse and so_item_meta.has_field("delivery_warehouse"):
            row.delivery_warehouse = row_warehouse
        if row_warehouse and so_item_meta.has_field("warehouse"):
            row.warehouse = row_warehouse
        if (raw or {}).get("rate") is not None:
            row.rate = flt((raw or {}).get("rate"))
        if (raw or {}).get("conversion_factor") is not None:
            row.conversion_factor = flt((raw or {}).get("conversion_factor") or 1) or 1
        if so_item_meta.has_field("serial_no") and (raw or {}).get("serial_no"):
            row.serial_no = (raw or {}).get("serial_no")
        if so_item_meta.has_field("batch_no") and (raw or {}).get("batch_no"):
            row.batch_no = (raw or {}).get("batch_no")
        if so_item_meta.has_field("discount_percentage") and (raw or {}).get("discount_percentage") is not None:
            row.discount_percentage = flt((raw or {}).get("discount_percentage") or 0)
        if so_item_meta.has_field("discount_amount") and (raw or {}).get("discount_amount") is not None:
            row.discount_amount = flt((raw or {}).get("discount_amount") or 0)
        if so_item_meta.has_field("price_list_rate") and (raw or {}).get("price_list_rate") is not None:
            row.price_list_rate = flt((raw or {}).get("price_list_rate") or 0)
        if so_item_meta.has_field("posa_notes") and (raw or {}).get("posa_notes") is not None:
            row.posa_notes = (raw or {}).get("posa_notes") or ""
        if so_item_meta.has_field("posa_delivery_date") and (raw or {}).get("posa_delivery_date"):
            row.posa_delivery_date = (raw or {}).get("posa_delivery_date")
        # Sales Order requires item delivery date; use row-level if provided, otherwise transaction date.
        if so_item_meta.has_field("delivery_date"):
            row.delivery_date = (raw or {}).get("posa_delivery_date") or transaction_date

    if not sales_order_doc.get("items"):
        frappe.throw(_("No valid items were provided for Sales Order token creation."))

    if data.get("discount_amount") is not None and hasattr(sales_order_doc, "discount_amount"):
        sales_order_doc.discount_amount = flt(data.get("discount_amount") or 0)
    if data.get("additional_discount_percentage") is not None and hasattr(sales_order_doc, "additional_discount_percentage"):
        sales_order_doc.additional_discount_percentage = flt(data.get("additional_discount_percentage") or 0)

    sales_order_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    sales_order_doc.run_method("set_missing_values")
    if hasattr(sales_order_doc, "calculate_taxes_and_totals"):
        sales_order_doc.calculate_taxes_and_totals()
    sales_order_doc.save()
    sales_order_doc.submit()

    workflow_state = _upsert_relay_workflow_state_for_sales_order(
        sales_order_doc,
        pos_profile=pos_profile,
        pos_opening_shift=pos_opening_shift or None,
        token_status="Draft",
    )

    sales_associate_user = frappe.session.user
    sales_associate_name = (
        frappe.get_cached_value("User", sales_associate_user, "full_name")
        or sales_associate_user
    )
    order_taken_at = (workflow_state.get("order_taken_at") if workflow_state else None) or now_datetime()

    return {
        "sales_order_name": sales_order_doc.name,
        "token_id": sales_order_doc.name,
        "token_last4": cstr(sales_order_doc.name)[-4:],
        "order_name": order_name,
        "posa_order_name": order_name,
        "customer": sales_order_doc.customer,
        "customer_name": sales_order_doc.customer_name,
        "grand_total": sales_order_doc.grand_total,
        "currency": sales_order_doc.currency,
        "business_date": cstr(sales_order_doc.get("transaction_date") or nowdate()),
        "order_taken_at": str(order_taken_at),
        "sales_associate_user": sales_associate_user,
        "sales_associate_name": sales_associate_name,
        "sales_order": sales_order_doc.as_dict(),
        "workflow_state": workflow_state.as_dict() if workflow_state else None,
    }


@frappe.whitelist()
def update_invoice(data):
    data = json.loads(data)

    if data.get("name"):
        invoice_doc = frappe.get_doc("Sales Invoice", data.get("name"))
        invoice_doc.update(data)
    else:
        invoice_doc = frappe.get_doc(data)

    invoice_doc.set_missing_values()
    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True

    # Handle returns
    if invoice_doc.is_return and invoice_doc.return_against:
        ref_doc = frappe.get_doc("Sales Invoice", invoice_doc.return_against)

        if not ref_doc.update_stock:
            invoice_doc.update_stock = 0

        if len(invoice_doc.payments) == 0:
            invoice_doc.payments = ref_doc.payments

        for return_item in invoice_doc.items:
            match_found = False
            for original_item in ref_doc.items:
                if return_item.item_code == original_item.item_code:
                    return_item.sales_invoice = ref_doc.name
                    return_item.sales_invoice_item = original_item.name
                    return_item.rate = original_item.rate
                    return_item.uom = original_item.uom
                    return_item.income_account = original_item.income_account
                    return_item.cost_center = original_item.cost_center
                    return_item.warehouse = original_item.warehouse
                    match_found = True
                    break
            if not match_found:
                frappe.throw(
                    _("Row # {0}: Returned Item {1} does not exist in Sales Invoice {2}").format(
                        return_item.idx, return_item.item_code, ref_doc.name
                    )
                )

    # Validate zero-rated items
    allow_zero_rated_items = frappe.get_cached_value(
        "POS Profile", invoice_doc.pos_profile, "posa_allow_zero_rated_items"
    )

    for item in invoice_doc.items:
        if not item.rate or item.rate == 0:
            if allow_zero_rated_items:
                item.price_list_rate = 0.00
                item.is_free_item = 1
            else:
                frappe.throw(
                    _("Rate cannot be zero for item {0}").format(item.item_code)
                )
        else:
            item.is_free_item = 0

        add_taxes_from_tax_template(item, invoice_doc)

    # Tax inclusion flag
    if frappe.get_cached_value(
        "POS Profile", invoice_doc.pos_profile, "posa_tax_inclusive"
    ):
        if invoice_doc.get("taxes"):
            for tax in invoice_doc.taxes:
                tax.included_in_print_rate = 1

    # Set posting time if backdated
    today_date = getdate()
    if (
        invoice_doc.get("posting_date")
        and getdate(invoice_doc.posting_date) != today_date
    ):
        invoice_doc.set_posting_time = 1

    # Enforce payment reset
    if invoice_doc.is_return:
        invoice_doc.paid_amount = 0.0
        invoice_doc.write_off_amount = 0.0
        for payment in invoice_doc.payments:
            payment.amount = 0.0

        # ✅ Show message (not throw) if no payment selected
        has_payment = any(flt(p.amount) > 0 for p in invoice_doc.payments)
        if not has_payment:
            frappe.msgprint(_("Please select a Mode of Payment before submitting the document."))

    invoice_doc.save()

    _upsert_relay_workflow_state(
        invoice_doc,
        token_status="Draft" if invoice_doc.docstatus == 0 else None,
    )

    return invoice_doc





@frappe.whitelist()
def submit_invoice(invoice, data):
    data = json.loads(data or "{}")
    if not isinstance(data, dict):
        data = {}

    invoice = json.loads(invoice or "{}")
    if not isinstance(invoice, dict):
        invoice = {}

    invoice_doc = frappe.get_doc("Sales Invoice", invoice.get("name"))
    invoice_doc.update(invoice)

    _set_invoice_cashier_attribution(invoice_doc, data=data, invoice_payload=invoice)

    if _is_relay_workflow_enabled(cstr(invoice_doc.get("pos_profile") or "").strip()):
        _require_operational_role_for_action(
            ("cline-Cashier", "cline-Supervisor"),
            "submit invoices",
            allow_relay_sync=True,
        )

    if invoice.get("posa_delivery_date"):
        invoice_doc.update_stock = 0
    mop_cash_list = [
        i.mode_of_payment
        for i in invoice_doc.payments
        if "cash" in i.mode_of_payment.lower() and i.type == "Cash"
    ]
    if len(mop_cash_list) > 0:
        cash_account = get_bank_cash_account(mop_cash_list[0], invoice_doc.company)
    else:
        cash_account = {
            "account": frappe.get_value(
                "Company", invoice_doc.company, "default_cash_account"
            )
        }

    # creating advance payment
    if data.get("credit_change"):
        advance_payment_entry = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "mode_of_payment": "Cash",
                "paid_to": cash_account["account"],
                "payment_type": "Receive",
                "party_type": "Customer",
                "party": invoice_doc.get("customer"),
                "paid_amount": invoice_doc.get("credit_change"),
                "received_amount": invoice_doc.get("credit_change"),
                "company": invoice_doc.get("company"),
            }
        )

        advance_payment_entry.flags.ignore_permissions = True
        frappe.flags.ignore_account_permission = True
        advance_payment_entry.save()
        advance_payment_entry.submit()

    # calculating cash
    total_cash = 0
    if data.get("redeemed_customer_credit"):
        total_cash = invoice_doc.total - float(data.get("redeemed_customer_credit"))

    is_payment_entry = 0
    if data.get("redeemed_customer_credit"):
        for row in data.get("customer_credit_dict"):
            if row["type"] == "Advance" and row["credit_to_redeem"]:
                advance = frappe.get_doc("Payment Entry", row["credit_origin"])

                advance_payment = {
                    "reference_type": "Payment Entry",
                    "reference_name": advance.name,
                    "remarks": advance.remarks,
                    "advance_amount": advance.unallocated_amount,
                    "allocated_amount": row["credit_to_redeem"],
                }

                invoice_doc.append("advances", advance_payment)
                invoice_doc.is_pos = 0
                is_payment_entry = 1

    payments = invoice_doc.payments

    if frappe.get_value("POS Profile", invoice_doc.pos_profile, "posa_auto_set_batch"):
        set_batch_nos(invoice_doc, "warehouse", throw=True)
    set_batch_nos_for_bundels(invoice_doc, "warehouse", throw=True)

    invoice_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    invoice_doc.posa_is_printed = 1
    invoice_doc.save()

    if data.get("due_date"):
        frappe.db.set_value(
            "Sales Invoice",
            invoice_doc.name,
            "due_date",
            data.get("due_date"),
            update_modified=False,
        )

    if frappe.get_value(
        "POS Profile",
        invoice_doc.pos_profile,
        "posa_allow_submissions_in_background_job",
    ):
        invoices_list = frappe.get_all(
            "Sales Invoice",
            filters={
                "posa_pos_opening_shift": invoice_doc.posa_pos_opening_shift,
                "docstatus": 0,
                "posa_is_printed": 1,
            },
        )
        for invoice in invoices_list:
            enqueue(
                method=submit_in_background_job,
                queue="short",
                timeout=1000,
                is_async=True,
                kwargs={
                    "invoice": invoice.name,
                    "data": data,
                    "is_payment_entry": is_payment_entry,
                    "total_cash": total_cash,
                    "cash_account": cash_account,
                    "payments": payments,
                },
            )
    else:
        invoice_doc.submit()
        redeeming_customer_credit(
            invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
        )
        _upsert_relay_workflow_state(
            invoice_doc,
            token_status="Paid",
            picking_status="Not Started",
            dispatch_status="Pending",
        )

    return {"name": invoice_doc.name, "status": invoice_doc.docstatus}


def _set_invoice_cashier_attribution(invoice_doc, data=None, invoice_payload=None):
    if not invoice_doc:
        return ""

    data = data or {}
    invoice_payload = invoice_payload or {}
    invoice_meta = None
    try:
        invoice_meta = frappe.get_meta("Sales Invoice")
    except Exception:
        invoice_meta = None

    def _read(mapping, key):
        if isinstance(mapping, dict):
            return cstr(mapping.get(key) or "").strip()
        return ""

    cashier_user = ""
    for candidate in (
        _read(data, "cashier_user_id"),
        _read(data, "cashier"),
        _read(invoice_payload, "cashier_user_id"),
        _read(invoice_payload, "cashier"),
        cstr(invoice_doc.get("custom_cashier") or "").strip(),
        cstr(invoice_doc.get("cashier_user_id") or "").strip(),
        cstr(invoice_doc.get("owner") or "").strip(),
        cstr(frappe.session.user or "").strip(),
    ):
        if candidate:
            cashier_user = candidate
            break

    if not cashier_user or not invoice_meta:
        return cashier_user

    for fieldname in ("custom_cashier", "cashier_user_id", "cashier"):
        if invoice_meta.has_field(fieldname):
            invoice_doc.set(fieldname, cashier_user)
            break

    cashier_name = cstr(
        frappe.get_cached_value("User", cashier_user, "full_name") or cashier_user
    ).strip()
    for name_field in ("custom_cashier_name", "cashier_name"):
        if cashier_name and invoice_meta.has_field(name_field):
            invoice_doc.set(name_field, cashier_name)
            break

    return cashier_user


def set_batch_nos_for_bundels(doc, warehouse_field, throw=False):
    """Automatically select `batch_no` for outgoing items in item table"""
    for d in doc.packed_items:
        qty = d.get("stock_qty") or d.get("transfer_qty") or d.get("qty") or 0
        has_batch_no = frappe.db.get_value("Item", d.item_code, "has_batch_no")
        warehouse = d.get(warehouse_field, None)
        if has_batch_no and warehouse and qty > 0:
            if not d.batch_no:
                d.batch_no = get_batch_no(
                    d.item_code, warehouse, qty, throw, d.serial_no
                )
            else:
                batch_qty = get_batch_qty(batch_no=d.batch_no, warehouse=warehouse)
                if flt(batch_qty, d.precision("qty")) < flt(qty, d.precision("qty")):
                    frappe.throw(
                        _(
                            "Row #{0}: The batch {1} has only {2} qty. Please select another batch which has {3} qty available or split the row into multiple rows, to deliver/issue from multiple batches"
                        ).format(d.idx, d.batch_no, batch_qty, qty)
                    )


def redeeming_customer_credit(
    invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
):
    # redeeming customer credit with journal voucher
    today = nowdate()
    if data.get("redeemed_customer_credit"):
        cost_center = frappe.get_value(
            "POS Profile", invoice_doc.pos_profile, "cost_center"
        )
        if not cost_center:
            cost_center = frappe.get_value(
                "Company", invoice_doc.company, "cost_center"
            )
        if not cost_center:
            frappe.throw(
                _("Cost Center is not set in pos profile {}").format(
                    invoice_doc.pos_profile
                )
            )
        for row in data.get("customer_credit_dict"):
            if row["type"] == "Invoice" and row["credit_to_redeem"]:
                outstanding_invoice = frappe.get_doc(
                    "Sales Invoice", row["credit_origin"]
                )

                jv_doc = frappe.get_doc(
                    {
                        "doctype": "Journal Entry",
                        "voucher_type": "Journal Entry",
                        "posting_date": today,
                        "company": invoice_doc.company,
                    }
                )

                jv_debit_entry = {
                    "account": outstanding_invoice.debit_to,
                    "party_type": "Customer",
                    "party": invoice_doc.customer,
                    "reference_type": "Sales Invoice",
                    "reference_name": outstanding_invoice.name,
                    "debit_in_account_currency": row["credit_to_redeem"],
                    "cost_center": cost_center,
                }

                jv_credit_entry = {
                    "account": invoice_doc.debit_to,
                    "party_type": "Customer",
                    "party": invoice_doc.customer,
                    "reference_type": "Sales Invoice",
                    "reference_name": invoice_doc.name,
                    "credit_in_account_currency": row["credit_to_redeem"],
                    "cost_center": cost_center,
                }

                jv_doc.append("accounts", jv_debit_entry)
                jv_doc.append("accounts", jv_credit_entry)

                jv_doc.flags.ignore_permissions = True
                frappe.flags.ignore_account_permission = True
                jv_doc.set_missing_values()
                jv_doc.save()
                jv_doc.submit()

    if is_payment_entry and total_cash > 0:
        for payment in payments:
            if not payment.amount:
                continue
            payment_entry_doc = frappe.get_doc(
                {
                    "doctype": "Payment Entry",
                    "posting_date": today,
                    "payment_type": "Receive",
                    "party_type": "Customer",
                    "party": invoice_doc.customer,
                    "paid_amount": payment.amount,
                    "received_amount": payment.amount,
                    "paid_from": invoice_doc.debit_to,
                    "paid_to": payment.account,
                    "company": invoice_doc.company,
                    "mode_of_payment": payment.mode_of_payment,
                    "reference_no": invoice_doc.posa_pos_opening_shift,
                    "reference_date": today,
                }
            )

            payment_reference = {
                "allocated_amount": payment.amount,
                "due_date": data.get("due_date"),
                "reference_doctype": "Sales Invoice",
                "reference_name": invoice_doc.name,
            }

            payment_entry_doc.append("references", payment_reference)
            payment_entry_doc.flags.ignore_permissions = True
            frappe.flags.ignore_account_permission = True
            payment_entry_doc.save()
            payment_entry_doc.submit()


def submit_in_background_job(kwargs):
    invoice = kwargs.get("invoice")
    invoice_doc = kwargs.get("invoice_doc")
    data = kwargs.get("data")
    is_payment_entry = kwargs.get("is_payment_entry")
    total_cash = kwargs.get("total_cash")
    cash_account = kwargs.get("cash_account")
    payments = kwargs.get("payments")

    invoice_doc = frappe.get_doc("Sales Invoice", invoice)
    invoice_doc.submit()
    redeeming_customer_credit(
        invoice_doc, data, is_payment_entry, total_cash, cash_account, payments
    )
    _upsert_relay_workflow_state(
        invoice_doc,
        token_status="Paid",
        picking_status="Not Started",
        dispatch_status="Pending",
    )


@frappe.whitelist()
def get_available_credit(customer, company):
    total_credit = []

    outstanding_invoices = frappe.get_all(
        "Sales Invoice",
        {
            "outstanding_amount": ["<", 0],
            "docstatus": 1,
            "is_return": 0,
            "customer": customer,
            "company": company,
        },
        ["name", "outstanding_amount"],
    )

    for row in outstanding_invoices:
        outstanding_amount = -(row.outstanding_amount)
        row = {
            "type": "Invoice",
            "credit_origin": row.name,
            "total_credit": outstanding_amount,
            "credit_to_redeem": 0,
        }

        total_credit.append(row)

    advances = frappe.get_all(
        "Payment Entry",
        {
            "unallocated_amount": [">", 0],
            "party_type": "Customer",
            "party": customer,
            "company": company,
            "docstatus": 1,
        },
        ["name", "unallocated_amount"],
    )

    for row in advances:
        row = {
            "type": "Advance",
            "credit_origin": row.name,
            "total_credit": row.unallocated_amount,
            "credit_to_redeem": 0,
        }

        total_credit.append(row)

    return total_credit


@frappe.whitelist()
def get_draft_invoices(pos_opening_shift):
    invoices_list = frappe.get_list(
        "Sales Invoice",
        filters={
            "posa_pos_opening_shift": pos_opening_shift,
            "docstatus": 0,
            "posa_is_printed": 0,
        },
        fields=["name"],
        limit_page_length=0,
        order_by="modified desc",
    )
    data = []
    for invoice in invoices_list:
        data.append(frappe.get_cached_doc("Sales Invoice", invoice["name"]))
    return data


@frappe.whitelist()
def delete_invoice(invoice):
    if frappe.get_value("Sales Invoice", invoice, "posa_is_printed"):
        frappe.throw(_("This invoice {0} cannot be deleted").format(invoice))
    _delete_sales_invoice_with_retry(invoice, force=1)
    return _("Invoice {0} Deleted").format(invoice)


@frappe.whitelist()
def get_items_details(pos_profile, items_data):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 60

    @redis_cache(ttl=ttl or 1800)
    def __get_items_details(pos_profile, items_data):
        return _get_items_details(pos_profile, items_data)

    def _get_items_details(pos_profile, items_data):
        today = nowdate()
        pos_profile = json.loads(pos_profile)
        items_data = json.loads(items_data)
        warehouse = pos_profile.get("warehouse")
        result = []

        if len(items_data) > 0:
            for item in items_data:
                item_code = item.get("item_code")
                item_stock_qty = get_stock_availability(item_code, warehouse)
                has_batch_no, has_serial_no = frappe.get_value(
                    "Item", item_code, ["has_batch_no", "has_serial_no"]
                )

                uoms = frappe.get_all(
                    "UOM Conversion Detail",
                    filters={"parent": item_code},
                    fields=["uom", "conversion_factor"],
                )

                serial_no_data = frappe.get_all(
                    "Serial No",
                    filters={
                        "item_code": item_code,
                        "status": "Active",
                        "warehouse": warehouse,
                    },
                    fields=["name as serial_no"],
                )

                batch_no_data = []

                batch_list = get_batch_qty(warehouse=warehouse, item_code=item_code)

                if batch_list:
                    for batch in batch_list:
                        if batch.qty > 0 and batch.batch_no:
                            batch_doc = frappe.get_cached_doc("Batch", batch.batch_no)
                            if (
                                str(batch_doc.expiry_date) > str(today)
                                or batch_doc.expiry_date in ["", None]
                            ) and batch_doc.disabled == 0:
                                batch_no_data.append(
                                    {
                                        "batch_no": batch.batch_no,
                                        "batch_qty": batch.qty,
                                        "expiry_date": batch_doc.expiry_date,
                                        "batch_price": batch_doc.posa_batch_price,
                                        "manufacturing_date": batch_doc.manufacturing_date,
                                    }
                                )

                row = {}
                row.update(item)
                row.update(
                    {
                        "item_uoms": uoms or [],
                        "serial_no_data": serial_no_data or [],
                        "batch_no_data": batch_no_data or [],
                        "actual_qty": item_stock_qty or 0,
                        "has_batch_no": has_batch_no,
                        "has_serial_no": has_serial_no,
                    }
                )

                result.append(row)

        return result

    if _pos_profile.get("posa_use_server_cache"):
        return __get_items_details(pos_profile, items_data)
    else:
        return _get_items_details(pos_profile, items_data)


@frappe.whitelist()
def get_item_detail(item, doc=None, warehouse=None, price_list=None):
    item = json.loads(item)
    today = nowdate()
    item_code = item.get("item_code")
    batch_no_data = []
    if warehouse and item.get("has_batch_no"):
        batch_list = get_batch_qty(warehouse=warehouse, item_code=item_code)
        if batch_list:
            for batch in batch_list:
                if batch.qty > 0 and batch.batch_no:
                    batch_doc = frappe.get_cached_doc("Batch", batch.batch_no)
                    if (
                        str(batch_doc.expiry_date) > str(today)
                        or batch_doc.expiry_date in ["", None]
                    ) and batch_doc.disabled == 0:
                        batch_no_data.append(
                            {
                                "batch_no": batch.batch_no,
                                "batch_qty": batch.qty,
                                "expiry_date": batch_doc.expiry_date,
                                "batch_price": batch_doc.posa_batch_price,
                                "manufacturing_date": batch_doc.manufacturing_date,
                            }
                        )

    item["selling_price_list"] = price_list

    max_discount = frappe.get_value("Item", item_code, "max_discount")
    res = get_item_details(
        item,
        doc,
        overwrite_warehouse=False,
    )
    if item.get("is_stock_item") and warehouse:
        res["actual_qty"] = get_stock_availability(item_code, warehouse)
    res["max_discount"] = max_discount
    res["batch_no_data"] = batch_no_data
    return res


def get_stock_availability(item_code, warehouse):
    actual_qty = (
        frappe.db.get_value(
            "Stock Ledger Entry",
            filters={
                "item_code": item_code,
                "warehouse": warehouse,
                "is_cancelled": 0,
            },
            fieldname="qty_after_transaction",
            order_by="posting_date desc, posting_time desc, creation desc",
        )
        or 0.0
    )
    return actual_qty


@frappe.whitelist()
def create_customer(
    customer_id,
    customer_name,
    company,
    pos_profile_doc,
    tax_id=None,
    mobile_no=None,
    email_id=None,
    referral_code=None,
    birthday=None,
    customer_group=None,
    territory=None,
    customer_type=None,
    gender=None,
    method="create",
):
    pos_profile = json.loads(pos_profile_doc)
    if method == "create":
        is_exist = frappe.db.exists("Customer", {"customer_name": customer_name})
        if pos_profile.get("posa_allow_duplicate_customer_names") or not is_exist:
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": customer_name,
                    "posa_referral_company": company,
                    "tax_id": tax_id,
                    "mobile_no": mobile_no,
                    "email_id": email_id,
                    "posa_referral_code": referral_code,
                    "posa_birthday": birthday,
                    "customer_type": customer_type,
                    "gender": gender,
                }
            )
            if customer_group:
                customer.customer_group = customer_group
            else:
                customer.customer_group = "All Customer Groups"
            if territory:
                customer.territory = territory
            else:
                customer.territory = "All Territories"
            customer.save()
            return customer
        else:
            frappe.throw(_("Customer already exists"))

    elif method == "update":
        customer_doc = frappe.get_doc("Customer", customer_id)
        customer_doc.customer_name = customer_name
        customer_doc.posa_referral_company = company
        customer_doc.tax_id = tax_id
        customer_doc.posa_referral_code = referral_code
        customer_doc.posa_birthday = birthday
        customer_doc.customer_type = customer_type
        customer_doc.territory = territory
        customer_doc.customer_group = customer_group
        customer_doc.gender = gender
        customer_doc.save()
        if mobile_no != customer_doc.mobile_no:
            set_customer_info(customer_doc.name, "mobile_no", mobile_no)
        if email_id != customer_doc.email_id:
            set_customer_info(customer_doc.name, "email_id", email_id)
        return customer_doc


@frappe.whitelist()
def get_items_from_barcode(selling_price_list, currency, barcode):
    search_item = frappe.get_all(
        "Item Barcode",
        filters={"barcode": barcode},
        fields=["parent", "barcode", "posa_uom"],
    )
    if len(search_item) == 0:
        return ""
    item_code = search_item[0].parent
    item_list = frappe.get_all(
        "Item",
        filters={"name": item_code},
        fields=[
            "name",
            "item_name",
            "description",
            "stock_uom",
            "image",
            "is_stock_item",
            "has_variants",
            "variant_of",
            "item_group",
            "has_batch_no",
            "has_serial_no",
        ],
    )

    if item_list[0]:
        item = item_list[0]
        filters = {"price_list": selling_price_list, "item_code": item_code}
        prices_with_uom = frappe.db.count(
            "Item Price",
            filters={
                "price_list": selling_price_list,
                "item_code": item_code,
                "uom": item.stock_uom,
            },
        )

        if prices_with_uom > 0:
            filters["uom"] = item.stock_uom
        else:
            filters["uom"] = ["in", ["", None, item.stock_uom]]

        item_prices_data = frappe.get_all(
            "Item Price",
            fields=["item_code", "price_list_rate", "currency"],
            filters=filters,
        )

        item_price = 0
        if len(item_prices_data):
            item_price = item_prices_data[0].get("price_list_rate")
            currency = item_prices_data[0].get("currency")

        item.update(
            {
                "rate": item_price,
                "currency": currency,
                "item_code": item_code,
                "barcode": barcode,
                "actual_qty": 0,
                "item_barcode": search_item,
            }
        )
        return item


@frappe.whitelist()
def set_customer_info(customer, fieldname, value=""):
    if fieldname == "loyalty_program":
        frappe.db.set_value("Customer", customer, "loyalty_program", value)

    contact = (
        frappe.get_cached_value("Customer", customer, "customer_primary_contact") or ""
    )

    if contact:
        contact_doc = frappe.get_doc("Contact", contact)
        if fieldname == "email_id":
            contact_doc.set("email_ids", [{"email_id": value, "is_primary": 1}])
            frappe.db.set_value("Customer", customer, "email_id", value)
        elif fieldname == "mobile_no":
            contact_doc.set("phone_nos", [{"phone": value, "is_primary_mobile_no": 1}])
            frappe.db.set_value("Customer", customer, "mobile_no", value)
        contact_doc.save()

    else:
        contact_doc = frappe.new_doc("Contact")
        contact_doc.first_name = customer
        contact_doc.is_primary_contact = 1
        contact_doc.is_billing_contact = 1
        if fieldname == "mobile_no":
            contact_doc.add_phone(value, is_primary_mobile_no=1, is_primary_phone=1)

        if fieldname == "email_id":
            contact_doc.add_email(value, is_primary=1)

        contact_doc.append("links", {"link_doctype": "Customer", "link_name": customer})

        contact_doc.flags.ignore_mandatory = True
        contact_doc.save()
        frappe.set_value(
            "Customer", customer, "customer_primary_contact", contact_doc.name
        )


@frappe.whitelist()
def search_invoices_for_return(invoice_name, company):
    invoices_list = frappe.get_list(
        "Sales Invoice",
        filters={
            "name": ["like", f"%{invoice_name}%"],
            "company": company,
            "docstatus": 1,
            "is_return": 0,
        },
        fields=["name"],
        order_by="customer",
    )

    data = []

    for invoice in invoices_list:
        original = frappe.get_doc("Sales Invoice", invoice["name"])

        # Get all return invoices for this invoice
        return_invoices = frappe.get_all(
            "Sales Invoice",
            filters={"return_against": original.name, "docstatus": 1},
            fields=["name"]
        )

        # Build map: item_code -> total returned qty
        returned_qty_map = {}
        for ret in return_invoices:
            ret_doc = frappe.get_doc("Sales Invoice", ret.name)
            for item in ret_doc.items:
                returned_qty_map[item.item_code] = returned_qty_map.get(item.item_code, 0) + abs(item.qty)

        has_returnable_items = False
        updated_items = []

        for item in original.items:
            returned_qty = returned_qty_map.get(item.item_code, 0)
            remaining_qty = item.qty - returned_qty

            # Copy item
            new_item = copy.deepcopy(item)

            if remaining_qty > 0:
                # Mark item for return (negate qty & recalc amounts)
                new_item.qty = -remaining_qty
                new_item.stock_qty = -(item.stock_qty / item.qty) * remaining_qty if item.qty else 0
                new_item.amount = -(item.amount / item.qty) * remaining_qty if item.qty else 0
                has_returnable_items = True
            else:
                new_item.qty = 0
                new_item.stock_qty = 0
                new_item.amount = 0

            updated_items.append(new_item)

        if has_returnable_items:
            original.set("items", updated_items)
            data.append(original)

    return data


def _age_days_from_date(raw_date):
    try:
        d = getdate(raw_date)
        return max(0, (getdate(nowdate()) - d).days)
    except Exception:
        return 0


def _resolve_pos_profile_for_lookup(pos_profile, company):
    pos_profile = cstr(pos_profile or "").strip()
    if pos_profile:
        return pos_profile

    # Fallback for older/stale frontend assets that do not send `pos_profile` yet.
    active_shift = frappe.db.get_all(
        "POS Opening Shift",
        filters={
            "user": frappe.session.user,
            "pos_closing_shift": ["in", ["", None]],
            "docstatus": 1,
            "status": "Open",
            "company": company,
        },
        fields=["pos_profile"],
        order_by="period_start_date desc",
        limit_page_length=1,
    )
    if active_shift:
        return cstr(active_shift[0].get("pos_profile") or "").strip()
    return ""


def _profile_so_policy(pos_profile):
    max_age_days = 1
    allow_stale = 0
    history_days = 30
    naming_series = ""
    if pos_profile:
        max_age_days = max(
            0,
            cint(
                frappe.get_cached_value(
                    "POS Profile", pos_profile, "posa_sales_order_lookup_max_age_days"
                )
                or 1
            ),
        )
        allow_stale = 1 if cint(
            frappe.get_cached_value(
                "POS Profile", pos_profile, "posa_allow_stale_sales_order_fetch"
            )
            or 0
        ) else 0
        history_days = max(
            max_age_days,
            cint(
                frappe.get_cached_value(
                    "POS Profile", pos_profile, "posa_stale_sales_order_history_days"
                )
                or 30
            ),
        )
        naming_series = cstr(
            frappe.get_cached_value("POS Profile", pos_profile, "posa_sales_order_naming_series")
            or ""
        ).strip()
    return {
        "max_age_days": max_age_days,
        "allow_stale": allow_stale,
        "history_days": history_days,
        "naming_series": naming_series,
    }


def _resolve_allow_stale(arg_allow_stale, default_allow_stale):
    if arg_allow_stale in (None, ""):
        return 1 if cint(default_allow_stale) else 0
    return 1 if cint(arg_allow_stale) else 0


def _require_quotation_permission(pos_profile, role):
    role = cstr(role or "").strip()
    if role not in ("cline-Sales Associate", "cline-Cashier"):
        return
    if not pos_profile:
        frappe.throw(_("POS Profile is required for quotation permission checks."))
    if role == "cline-Sales Associate":
        allowed = cint(frappe.get_cached_value("POS Profile", pos_profile, "posa_allow_sa_quotation") or 1)
        if not allowed:
            frappe.throw(_("Sales Associate quotation is disabled in POS Profile {0}.").format(pos_profile))
    if role == "cline-Cashier":
        allowed = cint(
            frappe.get_cached_value("POS Profile", pos_profile, "posa_allow_cashier_quotation") or 1
        )
        if not allowed:
            frappe.throw(_("Cashier quotation is disabled in POS Profile {0}.").format(pos_profile))


def _latest_item_rate_for_profile(item_code, pos_profile, company=None, customer=None, currency=None):
    item_code = cstr(item_code or "").strip()
    if not item_code:
        return 0
    price_list = cstr(frappe.get_cached_value("POS Profile", pos_profile, "selling_price_list") or "").strip()
    if not price_list:
        return 0

    filters = {
        "item_code": item_code,
        "price_list": price_list,
        "selling": 1,
    }
    if currency:
        filters["currency"] = currency
    row = frappe.get_all(
        "Item Price",
        filters=filters,
        fields=["price_list_rate", "valid_from", "creation"],
        order_by="valid_from desc, creation desc",
        limit_page_length=1,
    )
    if row:
        return flt(row[0].get("price_list_rate") or 0)
    return 0


@frappe.whitelist()
def search_orders(
    company,
    currency,
    order_name=None,
    pos_profile=None,
    days_back=None,
    allow_stale=None,
    history_days=None,
):
    pos_profile = _resolve_pos_profile_for_lookup(pos_profile, company)
    policy = _profile_so_policy(pos_profile)

    try:
        if days_back in (None, ""):
            days_back = policy["max_age_days"]
        days_back = max(0, cint(days_back or 1))
    except Exception:
        days_back = max(0, cint(policy["max_age_days"] or 1))

    allow_stale = _resolve_allow_stale(allow_stale, policy["allow_stale"])
    try:
        if history_days in (None, ""):
            history_days = policy["history_days"]
        history_days = max(days_back, cint(history_days or policy["history_days"] or 30))
    except Exception:
        history_days = max(days_back, cint(policy["history_days"] or 30))

    lookback_days = history_days if allow_stale else days_back
    filters = {
        "billing_status": ["in", ["Not Billed", "Partly Billed"]],
        "docstatus": 1,
        "company": company,
        "currency": currency,
        "transaction_date": [">=", add_days(nowdate(), -lookback_days)],
    }
    if policy["naming_series"]:
        filters["naming_series"] = policy["naming_series"]
    order_name = cstr(order_name or "").strip()
    or_filters = None
    if order_name:
        if frappe.get_meta("Sales Order").has_field("posa_order_name"):
            or_filters = [
                ["Sales Order", "name", "like", f"%{order_name}%"],
                ["Sales Order", "posa_order_name", "like", f"%{order_name}%"],
            ]
        else:
            filters["name"] = ["like", f"%{order_name}%"]

    orders_list = frappe.get_list(
        "Sales Order",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "transaction_date"],
        limit_page_length=0,
        order_by="transaction_date desc, creation desc",
    )
    data = []
    for order in orders_list:
        age_days = _age_days_from_date(order.get("transaction_date"))
        is_stale = 1 if age_days > days_back else 0
        if not allow_stale and is_stale:
            continue
        doc = frappe.get_doc("Sales Order", order["name"]).as_dict()
        doc["order_age_days"] = age_days
        doc["is_stale"] = is_stale
        doc["stale_policy_allow"] = 1 if allow_stale else 0
        doc["stale_policy_max_age_days"] = days_back
        doc["stale_policy_history_days"] = history_days
        data.append(doc)
    return data


@frappe.whitelist()
def create_quotation_token(data):
    role = _require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "create quotations",
        allow_relay_sync=True,
    )

    if isinstance(data, str):
        data = json.loads(data or "{}")
    data = data or {}

    pos_profile = cstr(data.get("pos_profile") or data.get("pos_profile_id") or "").strip()
    relay_quote_id = cstr(data.get("quote_id") or data.get("relay_quote_id") or "").strip()
    company = cstr(data.get("company") or "").strip()
    customer = cstr(data.get("customer") or data.get("customer_id") or "").strip()
    items = data.get("items") or data.get("lines") or []

    if not pos_profile:
        frappe.throw(_("POS Profile is required to create quotation."))
    if role != "__relay_sync__":
        _require_quotation_permission(pos_profile, role)

    if not company:
        company = cstr(frappe.get_cached_value("POS Profile", pos_profile, "company") or "").strip()
    if not company:
        frappe.throw(_("Company is required to create quotation."))
    if not customer:
        frappe.throw(_("Customer is required to create quotation."))
    if not items:
        frappe.throw(_("At least one item is required to create quotation."))

    quotation_meta = frappe.get_meta("Quotation")
    relay_quote_fieldname = ""
    for fieldname in ("custom_relay_quote_id", "relay_quote_id", "posa_relay_quote_id"):
        if quotation_meta.has_field(fieldname):
            relay_quote_fieldname = fieldname
            break

    if relay_quote_id and relay_quote_fieldname:
        existing_quote_name = frappe.db.get_value(
            "Quotation",
            {relay_quote_fieldname: relay_quote_id},
            "name",
        )
        if existing_quote_name:
            existing_doc = frappe.get_doc("Quotation", existing_quote_name)
            existing_valid_till = cstr(existing_doc.get("valid_till") or "")
            existing_is_expired = (
                1 if (existing_valid_till and getdate(existing_valid_till) < getdate(nowdate())) else 0
            )
            return {
                "quote_name": existing_doc.name,
                "quote_id": relay_quote_id,
                "valid_till": existing_valid_till,
                "is_expired": existing_is_expired,
                "age_days": _age_days_from_date(existing_doc.get("transaction_date")),
                "grand_total": existing_doc.grand_total,
                "currency": existing_doc.currency,
                "customer": cstr(existing_doc.get("customer") or existing_doc.get("party_name") or ""),
                "quotation": existing_doc.as_dict(),
                "idempotent_replay": 1,
            }

    validity_days = max(
        1, cint(frappe.get_cached_value("POS Profile", pos_profile, "posa_quotation_validity_days") or 7)
    )
    transaction_date = cstr(data.get("posting_date") or nowdate())
    valid_till = cstr(
        data.get("valid_till") or data.get("valid_until") or add_days(transaction_date, validity_days)
    )

    quotation_doc = frappe.new_doc("Quotation")
    quotation_doc.company = company
    quotation_doc.transaction_date = transaction_date
    if quotation_doc.meta.has_field("valid_till"):
        quotation_doc.valid_till = valid_till
    if quotation_doc.meta.has_field("quotation_to"):
        quotation_doc.quotation_to = "Customer"
    if quotation_doc.meta.has_field("party_name"):
        quotation_doc.party_name = customer
    if quotation_doc.meta.has_field("customer"):
        quotation_doc.customer = customer
    if data.get("currency"):
        quotation_doc.currency = data.get("currency")
    if data.get("campaign") and quotation_doc.meta.has_field("campaign"):
        quotation_doc.campaign = data.get("campaign")
    if relay_quote_id and relay_quote_fieldname and quotation_doc.meta.has_field(relay_quote_fieldname):
        quotation_doc.set(relay_quote_fieldname, relay_quote_id)

    selling_price_list = frappe.get_cached_value("POS Profile", pos_profile, "selling_price_list")
    if selling_price_list and quotation_doc.meta.has_field("selling_price_list"):
        quotation_doc.selling_price_list = selling_price_list

    q_item_meta = frappe.get_meta("Quotation Item")
    for raw in items:
        item_code = cstr((raw or {}).get("item_code") or "").strip()
        if not item_code:
            continue
        row = quotation_doc.append("items", {})
        row.item_code = item_code
        row.qty = flt((raw or {}).get("qty") or 0)
        row.uom = (raw or {}).get("uom")
        if (raw or {}).get("rate") is not None:
            row.rate = flt((raw or {}).get("rate"))
        if (raw or {}).get("conversion_factor") is not None:
            row.conversion_factor = flt((raw or {}).get("conversion_factor") or 1) or 1
        if q_item_meta.has_field("discount_percentage") and (raw or {}).get("discount_percentage") is not None:
            row.discount_percentage = flt((raw or {}).get("discount_percentage") or 0)
        if q_item_meta.has_field("discount_amount") and (raw or {}).get("discount_amount") is not None:
            row.discount_amount = flt((raw or {}).get("discount_amount") or 0)
        if q_item_meta.has_field("price_list_rate") and (raw or {}).get("price_list_rate") is not None:
            row.price_list_rate = flt((raw or {}).get("price_list_rate") or 0)
        if q_item_meta.has_field("warehouse") and (raw or {}).get("warehouse"):
            row.warehouse = (raw or {}).get("warehouse")
        if q_item_meta.has_field("delivery_date"):
            row.delivery_date = (raw or {}).get("posa_delivery_date") or valid_till

    if not quotation_doc.get("items"):
        frappe.throw(_("No valid items were provided for quotation creation."))

    if data.get("discount_amount") is not None and quotation_doc.meta.has_field("discount_amount"):
        quotation_doc.discount_amount = flt(data.get("discount_amount") or 0)
    if (
        data.get("additional_discount_percentage") is not None
        and quotation_doc.meta.has_field("additional_discount_percentage")
    ):
        quotation_doc.additional_discount_percentage = flt(data.get("additional_discount_percentage") or 0)

    quotation_doc.flags.ignore_permissions = True
    frappe.flags.ignore_account_permission = True
    quotation_doc.run_method("set_missing_values")
    if hasattr(quotation_doc, "calculate_taxes_and_totals"):
        quotation_doc.calculate_taxes_and_totals()
    quotation_doc.save()
    quotation_doc.submit()

    return {
        "quote_name": quotation_doc.name,
        "quote_id": relay_quote_id or quotation_doc.name,
        "valid_till": cstr(quotation_doc.get("valid_till") or valid_till),
        "is_expired": 0,
        "age_days": _age_days_from_date(quotation_doc.get("transaction_date")),
        "grand_total": quotation_doc.grand_total,
        "currency": quotation_doc.currency,
        "customer": customer,
        "quotation": quotation_doc.as_dict(),
    }


@frappe.whitelist()
def search_quotations(
    company=None,
    currency=None,
    pos_profile=None,
    quote_name=None,
    allow_stale=None,
    history_days=None,
):
    pos_profile = cstr(pos_profile or "").strip()
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))
    role = _require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "search quotations",
    )
    _require_quotation_permission(pos_profile, role)

    company = cstr(company or frappe.get_cached_value("POS Profile", pos_profile, "company") or "").strip()
    currency = cstr(currency or frappe.get_cached_value("POS Profile", pos_profile, "currency") or "").strip()

    so_policy = _profile_so_policy(pos_profile)
    validity_days = max(
        1, cint(frappe.get_cached_value("POS Profile", pos_profile, "posa_quotation_validity_days") or 7)
    )
    max_age_days = max(validity_days, cint(so_policy["max_age_days"] or 1))
    allow_stale = _resolve_allow_stale(allow_stale, so_policy["allow_stale"])
    if history_days in (None, ""):
        history_days = max(cint(so_policy["history_days"] or 30), max_age_days)
    history_days = max(max_age_days, cint(history_days or 30))

    lookback_days = history_days if allow_stale else max_age_days
    filters = {
        "docstatus": 1,
        "company": company,
        "transaction_date": [">=", add_days(nowdate(), -lookback_days)],
    }
    if currency:
        filters["currency"] = currency
    if quote_name:
        filters["name"] = ["like", f"%{quote_name}%"]

    rows = frappe.get_list(
        "Quotation",
        filters=filters,
        fields=["name", "transaction_date", "valid_till"],
        limit_page_length=0,
        order_by="transaction_date desc, creation desc",
    )
    out = []
    for row in rows:
        age_days = _age_days_from_date(row.get("transaction_date"))
        is_stale = 1 if age_days > max_age_days else 0
        if not allow_stale and is_stale:
            continue
        doc = frappe.get_doc("Quotation", row.get("name")).as_dict()
        valid_till = cstr(doc.get("valid_till") or row.get("valid_till") or "")
        is_expired = 1 if (valid_till and getdate(valid_till) < getdate(nowdate())) else 0
        doc["quote_name"] = doc.get("name")
        doc["order_age_days"] = age_days
        doc["age_days"] = age_days
        doc["is_stale"] = is_stale
        doc["is_expired"] = is_expired
        doc["stale_policy_allow"] = 1 if allow_stale else 0
        doc["stale_policy_max_age_days"] = max_age_days
        doc["stale_policy_history_days"] = history_days
        out.append(doc)
    return out


@frappe.whitelist()
def quotation_reprice_preview(quotation_name, pos_profile):
    quotation_name = cstr(quotation_name or "").strip()
    pos_profile = cstr(pos_profile or "").strip()
    if not quotation_name:
        frappe.throw(_("Quotation name is required"))
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))

    role = _require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "preview quotation repricing",
    )
    _require_quotation_permission(pos_profile, role)

    doc = frappe.get_doc("Quotation", quotation_name)
    repriced_lines = []
    old_total = 0.0
    new_total = 0.0
    for row in (doc.items or []):
        qty = flt(row.qty or 0)
        old_rate = flt(row.rate or 0)
        old_amount = flt(row.amount or (qty * old_rate))
        latest_rate = _latest_item_rate_for_profile(
            row.item_code, pos_profile, company=doc.company, customer=doc.party_name, currency=doc.currency
        )
        if latest_rate <= 0:
            latest_rate = old_rate
        new_amount = flt(qty * latest_rate)
        old_total += old_amount
        new_total += new_amount
        repriced_lines.append(
            {
                "item_code": row.item_code,
                "item_name": row.item_name,
                "qty": qty,
                "uom": row.uom,
                "old_rate": old_rate,
                "new_rate": latest_rate,
                "delta_rate": flt(latest_rate - old_rate),
                "old_amount": old_amount,
                "new_amount": new_amount,
                "delta_amount": flt(new_amount - old_amount),
            }
        )

    valid_till = cstr(doc.get("valid_till") or "")
    is_expired = 1 if (valid_till and getdate(valid_till) < getdate(nowdate())) else 0
    return {
        "quote_name": doc.name,
        "valid_till": valid_till,
        "is_expired": is_expired,
        "age_days": _age_days_from_date(doc.get("transaction_date")),
        "old_total": flt(old_total),
        "new_total": flt(new_total),
        "delta_total": flt(new_total - old_total),
        "repriced_lines": repriced_lines,
    }


@frappe.whitelist()
def convert_quotation_to_sales_order_token(quotation_name, pos_profile, confirm_reprice=1):
    quotation_name = cstr(quotation_name or "").strip()
    pos_profile = cstr(pos_profile or "").strip()
    if not quotation_name:
        frappe.throw(_("Quotation name is required"))
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))

    role = _require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "convert quotation to sales order token",
    )
    _require_quotation_permission(pos_profile, role)

    doc = frappe.get_doc("Quotation", quotation_name)
    validity_days = max(
        1, cint(frappe.get_cached_value("POS Profile", pos_profile, "posa_quotation_validity_days") or 7)
    )
    valid_till = cstr(doc.get("valid_till") or add_days(doc.get("transaction_date") or nowdate(), validity_days))
    if valid_till and getdate(valid_till) < getdate(nowdate()):
        frappe.throw(_("Quotation {0} is expired and cannot be converted.").format(quotation_name))

    preview = quotation_reprice_preview(quotation_name=quotation_name, pos_profile=pos_profile)
    if flt(preview.get("delta_total")) != 0 and not cint(confirm_reprice):
        frappe.throw(_("Price changed since quotation. Confirmation is required for conversion."))

    line_rate_map = {}
    for i, row in enumerate(preview.get("repriced_lines") or []):
        line_rate_map[(cstr(row.get("item_code") or ""), i)] = flt(row.get("new_rate") or 0)

    so_items = []
    for i, row in enumerate(doc.items or []):
        item_code = cstr(row.item_code or "").strip()
        new_rate = line_rate_map.get((item_code, i), flt(row.rate or 0))
        so_items.append(
            {
                "item_code": item_code,
                "item_name": row.item_name,
                "qty": flt(row.qty or 0),
                "uom": row.uom,
                "rate": new_rate,
                "amount": flt(flt(row.qty or 0) * new_rate),
                "conversion_factor": flt(row.conversion_factor or 1) or 1,
                "discount_percentage": flt(row.discount_percentage or 0),
                "discount_amount": flt(row.discount_amount or 0),
                "price_list_rate": flt(row.price_list_rate or new_rate),
                "warehouse": row.get("warehouse") if hasattr(row, "get") else None,
                "posa_delivery_date": cstr(row.get("delivery_date") if hasattr(row, "get") else "") or "",
            }
        )

    token = create_sales_order_token(
        {
            "pos_profile": pos_profile,
            "company": cstr(doc.get("company") or ""),
            "customer": cstr(doc.get("customer") or doc.get("party_name") or ""),
            "currency": cstr(doc.get("currency") or ""),
            "posting_date": cstr(nowdate()),
            "items": so_items,
            "discount_amount": flt(doc.get("discount_amount") or 0),
            "additional_discount_percentage": flt(doc.get("additional_discount_percentage") or 0),
        }
    )
    token["quote_name"] = quotation_name
    token["quote_valid_till"] = valid_till
    token["quote_reprice_preview"] = preview
    return token


def get_version():
    branch_name = get_app_branch("erpnext")
    if "12" in branch_name:
        return 12
    elif "13" in branch_name:
        return 13
    else:
        return 13


def get_app_branch(app):
    """Returns branch of an app"""
    import subprocess

    try:
        branch = subprocess.check_output(
            "cd ../apps/{0} && git rev-parse --abbrev-ref HEAD".format(app), shell=True
        )
        branch = branch.decode("utf-8")
        branch = branch.strip()
        return branch
    except Exception:
        return ""


@frappe.whitelist()
def get_offers(profile):
    pos_profile = frappe.get_doc("POS Profile", profile)
    company = pos_profile.company
    warehouse = pos_profile.warehouse
    date = nowdate()

    values = {
        "company": company,
        "pos_profile": profile,
        "warehouse": warehouse,
        "valid_from": date,
        "valid_upto": date,
    }
    data = frappe.db.sql(
        """
        SELECT *
        FROM `tabPOS Offer`
        WHERE 
        disable = 0 AND
        company = %(company)s AND
        (pos_profile is NULL OR pos_profile  = '' OR  pos_profile = %(pos_profile)s) AND
        (warehouse is NULL OR warehouse  = '' OR  warehouse = %(warehouse)s) AND
        (valid_from is NULL OR valid_from  = '' OR  valid_from <= %(valid_from)s) AND
        (valid_upto is NULL OR valid_from  = '' OR  valid_upto >= %(valid_upto)s)
    """,
        values=values,
        as_dict=1,
    )
    return data


@frappe.whitelist()
def get_customer_addresses(customer):
    return frappe.db.sql(
        """
        SELECT 
            address.name,
            address.address_line1,
            address.address_line2,
            address.address_title,
            address.city,
            address.state,
            address.country,
            address.address_type
        FROM `tabAddress` as address
        INNER JOIN `tabDynamic Link` AS link
				ON address.name = link.parent
        WHERE link.link_doctype = 'Customer'
            AND link.link_name = '{0}'
            AND address.disabled = 0
        ORDER BY address.name
        """.format(
            customer
        ),
        as_dict=1,
    )


@frappe.whitelist()
def make_address(args):
    args = json.loads(args)
    address = frappe.get_doc(
        {
            "doctype": "Address",
            "address_title": args.get("name"),
            "address_line1": args.get("address_line1"),
            "address_line2": args.get("address_line2"),
            "city": args.get("city"),
            "state": args.get("state"),
            "pincode": args.get("pincode"),
            "country": args.get("country"),
            "address_type": "Shipping",
            "links": [
                {"link_doctype": args.get("doctype"), "link_name": args.get("customer")}
            ],
        }
    ).insert()

    return address


def build_item_cache(item_code):
    parent_item_code = item_code

    attributes = [
        a.attribute
        for a in frappe.db.get_all(
            "Item Variant Attribute",
            {"parent": parent_item_code},
            ["attribute"],
            order_by="idx asc",
        )
    ]

    item_variants_data = frappe.db.get_all(
        "Item Variant Attribute",
        {"variant_of": parent_item_code},
        ["parent", "attribute", "attribute_value"],
        order_by="name",
        as_list=1,
    )

    disabled_items = set([i.name for i in frappe.db.get_all("Item", {"disabled": 1})])

    attribute_value_item_map = frappe._dict({})
    item_attribute_value_map = frappe._dict({})

    item_variants_data = [r for r in item_variants_data if r[0] not in disabled_items]
    for row in item_variants_data:
        item_code, attribute, attribute_value = row
        # (attr, value) => [item1, item2]
        attribute_value_item_map.setdefault((attribute, attribute_value), []).append(
            item_code
        )
        # item => {attr1: value1, attr2: value2}
        item_attribute_value_map.setdefault(item_code, {})[attribute] = attribute_value

    optional_attributes = set()
    for item_code, attr_dict in item_attribute_value_map.items():
        for attribute in attributes:
            if attribute not in attr_dict:
                optional_attributes.add(attribute)

    frappe.cache().hset(
        "attribute_value_item_map", parent_item_code, attribute_value_item_map
    )
    frappe.cache().hset(
        "item_attribute_value_map", parent_item_code, item_attribute_value_map
    )
    frappe.cache().hset("item_variants_data", parent_item_code, item_variants_data)
    frappe.cache().hset("optional_attributes", parent_item_code, optional_attributes)


def get_item_optional_attributes(item_code):
    val = frappe.cache().hget("optional_attributes", item_code)

    if not val:
        build_item_cache(item_code)

    return frappe.cache().hget("optional_attributes", item_code)


@frappe.whitelist()
def get_item_attributes(item_code):
    attributes = frappe.db.get_all(
        "Item Variant Attribute",
        fields=["attribute"],
        filters={"parenttype": "Item", "parent": item_code},
        order_by="idx asc",
    )

    optional_attributes = get_item_optional_attributes(item_code)

    for a in attributes:
        values = frappe.db.get_all(
            "Item Attribute Value",
            fields=["attribute_value", "abbr"],
            filters={"parenttype": "Item Attribute", "parent": a.attribute},
            order_by="idx asc",
        )
        a.values = values
        if a.attribute in optional_attributes:
            a.optional = True

    return attributes


@frappe.whitelist()
def create_payment_request(doc):
    doc = json.loads(doc)
    for pay in doc.get("payments"):
        if pay.get("type") == "Phone":
            if pay.get("amount") <= 0:
                frappe.throw(_("Payment amount cannot be less than or equal to 0"))

            if not doc.get("contact_mobile"):
                frappe.throw(_("Please enter the phone number first"))

            pay_req = get_existing_payment_request(doc, pay)
            if not pay_req:
                pay_req = get_new_payment_request(doc, pay)
                pay_req.submit()
            else:
                pay_req.request_phone_payment()

            return pay_req


def get_new_payment_request(doc, mop):
    payment_gateway_account = frappe.db.get_value(
        "Payment Gateway Account",
        {
            "payment_account": mop.get("account"),
        },
        ["name"],
    )

    args = {
        "dt": "Sales Invoice",
        "dn": doc.get("name"),
        "recipient_id": doc.get("contact_mobile"),
        "mode_of_payment": mop.get("mode_of_payment"),
        "payment_gateway_account": payment_gateway_account,
        "payment_request_type": "Inward",
        "party_type": "Customer",
        "party": doc.get("customer"),
        "return_doc": True,
    }
    return make_payment_request(**args)


def get_payment_gateway_account(args):
    return frappe.db.get_value(
        "Payment Gateway Account",
        args,
        ["name", "payment_gateway", "payment_account", "message"],
        as_dict=1,
    )


def get_existing_payment_request(doc, pay):
    payment_gateway_account = frappe.db.get_value(
        "Payment Gateway Account",
        {
            "payment_account": pay.get("account"),
        },
        ["name"],
    )

    args = {
        "doctype": "Payment Request",
        "reference_doctype": "Sales Invoice",
        "reference_name": doc.get("name"),
        "payment_gateway_account": payment_gateway_account,
        "email_to": doc.get("contact_mobile"),
    }
    pr = frappe.db.exists(args)
    if pr:
        return frappe.get_doc("Payment Request", pr)


def make_payment_request(**args):
    """Make payment request"""

    args = frappe._dict(args)

    ref_doc = frappe.get_doc(args.dt, args.dn)
    gateway_account = get_payment_gateway_account(args.get("payment_gateway_account"))
    if not gateway_account:
        frappe.throw(_("Payment Gateway Account not found"))

    grand_total = get_amount(ref_doc, gateway_account.get("payment_account"))
    if args.loyalty_points and args.dt == "Sales Order":
        from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
            validate_loyalty_points,
        )

        loyalty_amount = validate_loyalty_points(ref_doc, int(args.loyalty_points))
        frappe.db.set_value(
            "Sales Order",
            args.dn,
            "loyalty_points",
            int(args.loyalty_points),
            update_modified=False,
        )
        frappe.db.set_value(
            "Sales Order",
            args.dn,
            "loyalty_amount",
            loyalty_amount,
            update_modified=False,
        )
        grand_total = grand_total - loyalty_amount

    bank_account = (
        get_party_bank_account(args.get("party_type"), args.get("party"))
        if args.get("party_type")
        else ""
    )

    existing_payment_request = None
    if args.order_type == "Shopping Cart":
        existing_payment_request = frappe.db.get_value(
            "Payment Request",
            {
                "reference_doctype": args.dt,
                "reference_name": args.dn,
                "docstatus": ("!=", 2),
            },
        )

    if existing_payment_request:
        frappe.db.set_value(
            "Payment Request",
            existing_payment_request,
            "grand_total",
            grand_total,
            update_modified=False,
        )
        pr = frappe.get_doc("Payment Request", existing_payment_request)
    else:
        if args.order_type != "Shopping Cart":
            existing_payment_request_amount = get_existing_payment_request_amount(
                args.dt, args.dn
            )

            if existing_payment_request_amount:
                grand_total -= existing_payment_request_amount

        pr = frappe.new_doc("Payment Request")
        pr.update(
            {
                "payment_gateway_account": gateway_account.get("name"),
                "payment_gateway": gateway_account.get("payment_gateway"),
                "payment_account": gateway_account.get("payment_account"),
                "payment_channel": gateway_account.get("payment_channel"),
                "payment_request_type": args.get("payment_request_type"),
                "currency": ref_doc.currency,
                "grand_total": grand_total,
                "mode_of_payment": args.mode_of_payment,
                "email_to": args.recipient_id or ref_doc.owner,
                "subject": _("Payment Request for {0}").format(args.dn),
                "message": gateway_account.get("message") or get_dummy_message(ref_doc),
                "reference_doctype": args.dt,
                "reference_name": args.dn,
                "party_type": args.get("party_type") or "Customer",
                "party": args.get("party") or ref_doc.get("customer"),
                "bank_account": bank_account,
            }
        )

        if args.order_type == "Shopping Cart" or args.mute_email:
            pr.flags.mute_email = True

        pr.insert(ignore_permissions=True)
        if args.submit_doc:
            pr.submit()

    if args.order_type == "Shopping Cart":
        frappe.db.commit()
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = pr.get_payment_url()

    if args.return_doc:
        return pr

    return pr.as_dict()


def get_amount(ref_doc, payment_account=None):
    """get amount based on doctype"""
    grand_total = 0
    for pay in ref_doc.payments:
        if pay.type == "Phone" and pay.account == payment_account:
            grand_total = pay.amount
            break

    if grand_total > 0:
        return grand_total

    else:
        frappe.throw(
            _("Payment Entry is already created or payment account is not matched")
        )


@frappe.whitelist()
def get_pos_coupon(coupon, customer, company):
    res = check_coupon_code(coupon, customer, company)
    return res


@frappe.whitelist()
def get_active_gift_coupons(customer, company):
    coupons = []
    coupons_data = frappe.get_all(
        "POS Coupon",
        filters={
            "company": company,
            "coupon_type": "Gift Card",
            "customer": customer,
            "used": 0,
        },
        fields=["coupon_code"],
    )
    if len(coupons_data):
        coupons = [i.coupon_code for i in coupons_data]
    return coupons


@frappe.whitelist()
def get_customer_info(customer):
    customer = frappe.get_doc("Customer", customer)

    res = {"loyalty_points": None, "conversion_factor": None}

    res["email_id"] = customer.email_id
    res["mobile_no"] = customer.mobile_no
    res["image"] = customer.image
    res["loyalty_program"] = customer.loyalty_program
    res["customer_price_list"] = customer.default_price_list
    res["customer_group"] = customer.customer_group
    res["customer_type"] = customer.customer_type
    res["territory"] = customer.territory
    res["birthday"] = customer.posa_birthday
    res["gender"] = customer.gender
    res["tax_id"] = customer.tax_id
    res["posa_discount"] = customer.posa_discount
    res["name"] = customer.name
    res["customer_name"] = customer.customer_name
    res["customer_group_price_list"] = frappe.get_value(
        "Customer Group", customer.customer_group, "default_price_list"
    )

    if customer.loyalty_program:
        lp_details = get_loyalty_program_details_with_points(
            customer.name,
            customer.loyalty_program,
            silent=True,
            include_expired_entry=False,
        )
        res["loyalty_points"] = lp_details.get("loyalty_points")
        res["conversion_factor"] = lp_details.get("conversion_factor")

    return res


def get_company_domain(company):
    return frappe.get_cached_value("Company", cstr(company), "domain")


@frappe.whitelist()
def get_applicable_delivery_charges(
    company, pos_profile, customer, shipping_address_name=None
):
    return _get_applicable_delivery_charges(
        company, pos_profile, customer, shipping_address_name
    )


def auto_create_items():
    # create 20000 items
    for i in range(20000):
        item_code = "AUTO-ITEM-{}".format(i)
        item = frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "description": item_code,
                "item_group": "Auto Items",
                "is_stock_item": 0,
                "stock_uom": "Nos",
                "is_sales_item": 1,
                "is_purchase_item": 0,
                "is_fixed_asset": 0,
                "is_sub_contracted_item": 0,
                "is_pro_applicable": 0,
                "is_manufactured_item": 0,
                "is_service_item": 0,
                "is_non_stock_item": 0,
                "is_batch_item": 0,
                "is_table_item": 0,
                "is_variant_item": 0,
                "is_stock_item": 1,
                "opening_stock": 1000,
                "valuation_rate": 50 + i,
                "standard_rate": 100 + i,
            }
        )
        print("Creating Item: {}".format(item_code))
        item.insert(ignore_permissions=True)
        frappe.db.commit()


@frappe.whitelist()
def search_serial_or_batch_or_barcode_number(search_value, search_serial_no):
    # search barcode no
    barcode_data = frappe.db.get_value(
        "Item Barcode",
        {"barcode": search_value},
        ["barcode", "parent as item_code"],
        as_dict=True,
    )
    if barcode_data:
        return barcode_data
    # search serial no
    if search_serial_no:
        serial_no_data = frappe.db.get_value(
            "Serial No", search_value, ["name as serial_no", "item_code"], as_dict=True
        )
        if serial_no_data:
            return serial_no_data
    # search batch no
    batch_no_data = frappe.db.get_value(
        "Batch", search_value, ["name as batch_no", "item as item_code"], as_dict=True
    )
    if batch_no_data:
        return batch_no_data
    return {}


def get_seearch_items_conditions(item_code, serial_no, batch_no, barcode):
    if serial_no or batch_no or barcode:
        return " and name = {0}".format(frappe.db.escape(item_code))
    return """ and (name like {item_code} or item_name like {item_code})""".format(
        item_code=frappe.db.escape("%" + item_code + "%")
    )


@frappe.whitelist()
def create_sales_invoice_from_order(sales_order):
    sales_invoice = make_sales_invoice(sales_order, ignore_permissions=True)
    return sales_invoice.as_dict()


@frappe.whitelist()
def delete_sales_invoice(sales_invoice):
    _delete_sales_invoice_with_retry(sales_invoice)


def _delete_sales_invoice_with_retry(sales_invoice, force=0, attempts=3):
    last_error = None
    for attempt in range(attempts):
        try:
            frappe.delete_doc("Sales Invoice", sales_invoice, force=force)
            return
        except frappe.QueryDeadlockError as exc:
            last_error = exc
            frappe.db.rollback()
            if attempt >= attempts - 1:
                break
            time.sleep(0.2 * (attempt + 1))
    raise last_error


@frappe.whitelist()
def get_sales_invoice_child_table(sales_invoice, sales_invoice_item=None):
    parent_doc = frappe.get_doc("Sales Invoice", sales_invoice)

    if sales_invoice_item:
        # fetch specific item row
        return frappe.get_doc(
            "Sales Invoice Item", {"parent": parent_doc.name, "name": sales_invoice_item}
        )
    else:
        # fetch all child rows for that invoice
        return frappe.get_all(
            "Sales Invoice Item",
            filters={"parent": parent_doc.name},
            fields=["*"]
        )

# @frappe.whitelist()
# def get_sales_invoice_child_table(sales_invoice, sales_invoice_item):
#     parent_doc = frappe.get_doc("Sales Invoice", sales_invoice)
#     child_doc = frappe.get_doc(
#         "Sales Invoice Item", {"parent": parent_doc.name, "name": sales_invoice_item}
#     )
#     return child_doc
