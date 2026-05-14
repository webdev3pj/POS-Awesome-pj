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

from posawesome.posawesome.api.pos.sales_order.lookup import search_sales_orders
from posawesome.posawesome.api.pos.sales_order.create import (
    create_sales_order_token as create_pos_sales_order_token,
)
from posawesome.posawesome.api.pos.invoice import (
    batch as invoice_batch,
    credit as invoice_credit,
    document as invoice_document,
    submit as invoice_submit,
    lookup as invoice_lookup,
    taxes as invoice_taxes,
)
from posawesome.posawesome.api.pos.invoice.document import update_invoice as update_pos_invoice
from posawesome.posawesome.api.pos.invoice.submit import submit_invoice as submit_pos_invoice
from posawesome.posawesome.api.pos.quotation.lookup import (
    require_quotation_permission as _require_quotation_permission,
    search_pos_quotations,
)
from posawesome.posawesome.api.pos.quotation.create import create_pos_quotation_token
from posawesome.posawesome.api.pos.quotation.convert import (
    convert_quotation_to_sales_order_token as convert_pos_quotation_to_sales_order_token,
)
from posawesome.posawesome.api.pos.quotation.reprice import get_quotation_reprice_preview
from posawesome.posawesome.api.pos.sales_invoice.from_sales_order import (
    make_or_get_sales_invoice_from_order,
    update_invoice_from_order_data,
)
from posawesome.posawesome.api.pos.offers.lookup import get_pos_offers
from posawesome.posawesome.api.pos.catalog import (
    auto_create as catalog_auto_create,
    details as catalog_details,
    groups as catalog_groups,
    items as catalog_items,
    references as catalog_references,
    returns as catalog_returns,
    stock as catalog_stock,
)
from posawesome.posawesome.api.pos.customer import (
    create as customer_create,
    lookup as customer_lookup,
)
from posawesome.posawesome.api.pos import payment_request as pos_payment_request
from posawesome.posawesome.api.pos.relay import (
    actions as relay_actions,
    connectivity as relay_connectivity,
    fulfillment as relay_fulfillment,
    monitor as relay_monitor,
    state as relay_state,
)
from posawesome.posawesome.api.pos.customer.address import (
    get_customer_addresses as get_pos_customer_addresses,
    make_address as make_pos_address,
)
from posawesome.posawesome.api.pos.customer.coupon import (
    get_active_gift_coupons as get_pos_active_gift_coupons,
    get_pos_coupon as get_pos_coupon_code,
)
from posawesome.posawesome.api.pos.customer.info import (
    get_company_domain as get_pos_company_domain,
    get_customer_info as get_pos_customer_info,
)
from posawesome.posawesome.api.pos.delivery.charges import (
    get_applicable_delivery_charges as get_pos_delivery_charges,
)
from posawesome.posawesome.api.pos.item.attributes import (
    build_item_cache as build_pos_item_cache,
    get_item_attributes as get_pos_item_attributes,
    get_item_optional_attributes as get_pos_item_optional_attributes,
)
from posawesome.posawesome.api.pos.item.lookup import (
    get_seearch_items_conditions as get_pos_search_items_conditions,
    search_serial_or_batch_or_barcode_number as search_pos_serial_or_batch_or_barcode_number,
)
from posawesome.posawesome.api.pos.session.profile import (
    get_default_pos_profile_for_user as _get_default_pos_profile_for_user,
    require_user_default_pos_profile as _require_user_default_pos_profile,
)
from posawesome.posawesome.api.pos.session.roles import (
    OPERATIONAL_ROLES,
    admin_requested_test_role as _admin_requested_test_role,
    get_single_operational_role as _get_single_operational_role,
    is_admin_role_testing_enabled as _is_admin_role_testing_enabled,
    is_relay_sync_request as _is_relay_sync_request,
    require_operational_role_for_action as _require_operational_role_for_action,
    request_header as _request_header,
)
from posawesome.posawesome.api.pos.session.opening import (
    bootstrap_non_cash_pos_session as _bootstrap_non_cash_pos_session,
    bootstrap_pos_session as bootstrap_pos_session_data,
    check_opening_shift as check_pos_opening_shift,
    create_opening_voucher as create_pos_opening_voucher,
    get_opening_dialog_data as get_pos_opening_dialog_data,
    update_opening_shift_data,
)
from frappe.utils.caching import redis_cache

@frappe.whitelist()
def get_opening_dialog_data():
    return get_pos_opening_dialog_data(erpnext_version=get_version())


@frappe.whitelist()
def create_opening_voucher(pos_profile, company, balance_details):
    return create_pos_opening_voucher(
        pos_profile,
        company,
        balance_details,
        relay_workflow_enabled_fn=_is_relay_workflow_enabled,
    )


@frappe.whitelist()
def check_opening_shift(user):
    return check_pos_opening_shift(user)


@frappe.whitelist()
def bootstrap_pos_session(pos_profile, company=None):
    return bootstrap_pos_session_data(pos_profile, company=company)


@frappe.whitelist()
def get_items(pos_profile, price_list=None, item_group="", search_value="", customer=None):
    return catalog_items.get_items(pos_profile, price_list=price_list, item_group=item_group, search_value=search_value, customer=customer)


get_item_group_condition = catalog_groups.get_item_group_condition


get_root_of = catalog_groups.get_root_of


@frappe.whitelist()
def get_items_groups():
    return catalog_groups.get_items_groups()


get_customer_groups = catalog_groups.get_customer_groups


get_child_nodes = catalog_groups.get_child_nodes


get_customer_group_condition = catalog_groups.get_customer_group_condition


@frappe.whitelist()
def get_customer_names(pos_profile):
    return customer_lookup.get_customer_names(pos_profile)


@frappe.whitelist()
def get_sales_person_names():
    return catalog_references.get_sales_person_names()

@frappe.whitelist()
def get_sales_partner_names():
    return catalog_references.get_sales_partner_names()


RELAY_TOKEN_STATUSES = relay_state.RELAY_TOKEN_STATUSES
RELAY_PICKING_STATUSES = relay_state.RELAY_PICKING_STATUSES
RELAY_DISPATCH_STATUSES = relay_state.RELAY_DISPATCH_STATUSES

_relay_workflow_doctype_exists = relay_state._relay_workflow_doctype_exists
_is_relay_workflow_enabled = relay_state._is_relay_workflow_enabled
_resolve_relay_workflow_pos_profile = relay_state._resolve_relay_workflow_pos_profile
_relay_workflow_meta = relay_state._relay_workflow_meta
_relay_workflow_has_field = relay_state._relay_workflow_has_field
_set_state_field_if_exists = relay_state._set_state_field_if_exists
_get_relay_invoice_by_local_sale_ref = relay_state._get_relay_invoice_by_local_sale_ref
_set_relay_state_local_sale_ref = relay_state._set_relay_state_local_sale_ref
_get_invoice_linked_sales_order_name = relay_state._get_invoice_linked_sales_order_name
_get_relay_state_doc_for_sales_order = relay_state._get_relay_state_doc_for_sales_order
_apply_relay_workflow_state_updates = relay_state._apply_relay_workflow_state_updates
_upsert_relay_workflow_state_for_sales_order = relay_state._upsert_relay_workflow_state_for_sales_order
_get_relay_state_doc = relay_state._get_relay_state_doc
_upsert_relay_workflow_state = relay_state._upsert_relay_workflow_state

_get_edge_relay_base_url = relay_connectivity._get_edge_relay_base_url
_get_pos_profile_edge_relay_url = relay_connectivity._get_pos_profile_edge_relay_url
_get_pos_profile_field_if_exists = relay_connectivity._get_pos_profile_field_if_exists
_get_pos_profile_relay_connectivity_mode = relay_connectivity._get_pos_profile_relay_connectivity_mode
_get_pos_profile_allow_cloud_fallback_when_relay_down = relay_connectivity._get_pos_profile_allow_cloud_fallback_when_relay_down
_is_private_lan_host = relay_connectivity._is_private_lan_host

_cloud_pick_to_relay_status = relay_fulfillment._cloud_pick_to_relay_status
_normalize_monitor_display_status = relay_monitor._normalize_monitor_display_status


@frappe.whitelist()
def get_relay_connectivity_status(pos_profile):
    return relay_connectivity.get_relay_connectivity_status(pos_profile)


@frappe.whitelist()
def get_relay_workflow_state(sales_invoice):
    return relay_fulfillment.get_relay_workflow_state(sales_invoice)


@frappe.whitelist()
def get_relay_fulfillment_detail(sales_invoice, pos_profile=None, pos_profile_id=None):
    return relay_fulfillment.get_relay_fulfillment_detail(
        sales_invoice, pos_profile=pos_profile, pos_profile_id=pos_profile_id
    )


@frappe.whitelist()
def get_relay_pick_queue(pos_profile=None, picking_status=None, dispatch_status=None, limit_page_length=50):
    return relay_fulfillment.get_relay_pick_queue(
        pos_profile=pos_profile,
        picking_status=picking_status,
        dispatch_status=dispatch_status,
        limit_page_length=limit_page_length,
    )


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
    return relay_monitor.get_relay_workflow_monitor_board(
        pos_profile=pos_profile,
        business_date=business_date,
        scope_mode=scope_mode,
        pos_opening_shift=pos_opening_shift,
        mine_only=mine_only,
        include_released=include_released,
        limit_page_length=limit_page_length,
    )


@frappe.whitelist()
def update_relay_picking_status(sales_invoice, picking_status, exceptions_note=None, pos_profile=None, pos_profile_id=None):
    return relay_actions.update_relay_picking_status(
        sales_invoice,
        picking_status,
        exceptions_note=exceptions_note,
        pos_profile=pos_profile,
        pos_profile_id=pos_profile_id,
    )


@frappe.whitelist()
def release_relay_dispatch(sales_invoice, allow_exception_release=0, pos_profile=None, pos_profile_id=None):
    return relay_actions.release_relay_dispatch(
        sales_invoice,
        allow_exception_release=allow_exception_release,
        pos_profile=pos_profile,
        pos_profile_id=pos_profile_id,
    )

add_taxes_from_tax_template = invoice_taxes.add_taxes_from_tax_template


@frappe.whitelist()
def update_invoice_from_order(data):
    return update_invoice_from_order_data(data)


@frappe.whitelist()
def create_sales_order_token(data):
    return create_pos_sales_order_token(data)


@frappe.whitelist()
def update_invoice(data):
    return update_pos_invoice(data)





@frappe.whitelist()
def submit_invoice(invoice, data):
    return submit_pos_invoice(invoice, data)


_set_invoice_cashier_attribution = invoice_submit._set_invoice_cashier_attribution


set_batch_nos_for_bundels = invoice_batch.set_batch_nos_for_bundels


redeeming_customer_credit = invoice_credit.redeeming_customer_credit


submit_in_background_job = invoice_submit.submit_in_background_job


@frappe.whitelist()
def get_available_credit(customer, company):
    return invoice_credit.get_available_credit(customer, company)


@frappe.whitelist()
def get_draft_invoices(pos_opening_shift):
    return invoice_lookup.get_draft_invoices(pos_opening_shift)


@frappe.whitelist()
def delete_invoice(invoice):
    return invoice_lookup.delete_invoice(invoice)


@frappe.whitelist()
def get_items_details(pos_profile, items_data):
    return catalog_details.get_items_details(pos_profile, items_data)


@frappe.whitelist()
def get_item_detail(item, doc=None, warehouse=None, price_list=None):
    return catalog_details.get_item_detail(item, doc=doc, warehouse=warehouse, price_list=price_list)


get_stock_availability = catalog_stock.get_stock_availability


@frappe.whitelist()
def create_customer(customer_id, customer_name, company, pos_profile_doc, tax_id=None, mobile_no=None, email_id=None, referral_code=None, birthday=None, customer_group=None, territory=None, customer_type=None, gender=None, method="create"):
    return customer_create.create_customer(customer_id, customer_name, company, pos_profile_doc, tax_id=tax_id, mobile_no=mobile_no, email_id=email_id, referral_code=referral_code, birthday=birthday, customer_group=customer_group, territory=territory, customer_type=customer_type, gender=gender, method=method)


@frappe.whitelist()
def get_items_from_barcode(selling_price_list, currency, barcode):
    return catalog_details.get_items_from_barcode(selling_price_list, currency, barcode)


@frappe.whitelist()
def set_customer_info(customer, fieldname, value=""):
    return customer_create.set_customer_info(customer, fieldname, value=value)


@frappe.whitelist()
def search_invoices_for_return(invoice_name, company):
    return catalog_returns.search_invoices_for_return(invoice_name, company)


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
    return search_sales_orders(
        company=company,
        currency=currency,
        order_name=order_name,
        pos_profile=pos_profile,
        days_back=days_back,
        allow_stale=allow_stale,
        history_days=history_days,
    )


@frappe.whitelist()
def create_quotation_token(data):
    role = _require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "create quotations",
        allow_relay_sync=True,
    )
    return create_pos_quotation_token(data, role=role)


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
    return search_pos_quotations(
        company=company,
        currency=currency,
        pos_profile=pos_profile,
        quote_name=quote_name,
        allow_stale=allow_stale,
        history_days=history_days,
    )


@frappe.whitelist()
def quotation_reprice_preview(quotation_name, pos_profile):
    role = _require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "preview quotation repricing",
    )
    return get_quotation_reprice_preview(quotation_name, pos_profile, role=role)


@frappe.whitelist()
def convert_quotation_to_sales_order_token(quotation_name, pos_profile, confirm_reprice=1):
    role = _require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "convert quotation to sales order token",
    )
    return convert_pos_quotation_to_sales_order_token(
        quotation_name=quotation_name,
        pos_profile=pos_profile,
        confirm_reprice=confirm_reprice,
        role=role,
        reprice_preview_fn=quotation_reprice_preview,
        create_sales_order_token_fn=create_sales_order_token,
    )


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
    return get_pos_offers(profile)


@frappe.whitelist()
def get_customer_addresses(customer):
    return get_pos_customer_addresses(customer)


@frappe.whitelist()
def make_address(args):
    return make_pos_address(args)


def build_item_cache(item_code):
    return build_pos_item_cache(item_code)


def get_item_optional_attributes(item_code):
    return get_pos_item_optional_attributes(item_code)


@frappe.whitelist()
def get_item_attributes(item_code):
    return get_pos_item_attributes(item_code)


@frappe.whitelist()
def create_payment_request(doc):
    return pos_payment_request.create_payment_request(doc)


get_new_payment_request = pos_payment_request.get_new_payment_request


get_payment_gateway_account = pos_payment_request.get_payment_gateway_account


get_existing_payment_request = pos_payment_request.get_existing_payment_request


make_payment_request = pos_payment_request.make_payment_request


get_amount = pos_payment_request.get_amount


@frappe.whitelist()
def get_pos_coupon(coupon, customer, company):
    return get_pos_coupon_code(coupon, customer, company)


@frappe.whitelist()
def get_active_gift_coupons(customer, company):
    return get_pos_active_gift_coupons(customer, company)


@frappe.whitelist()
def get_customer_info(customer):
    return get_pos_customer_info(customer)


def get_company_domain(company):
    return get_pos_company_domain(company)


@frappe.whitelist()
def get_applicable_delivery_charges(
    company, pos_profile, customer, shipping_address_name=None
):
    return get_pos_delivery_charges(company, pos_profile, customer, shipping_address_name)


auto_create_items = catalog_auto_create.auto_create_items


@frappe.whitelist()
def search_serial_or_batch_or_barcode_number(search_value, search_serial_no):
    return search_pos_serial_or_batch_or_barcode_number(search_value, search_serial_no)


def get_seearch_items_conditions(item_code, serial_no, batch_no, barcode):
    return get_pos_search_items_conditions(item_code, serial_no, batch_no, barcode)


@frappe.whitelist()
def create_sales_invoice_from_order(sales_order, pos_profile=None, pos_opening_shift=None):
    return make_or_get_sales_invoice_from_order(
        sales_order, pos_profile=pos_profile, pos_opening_shift=pos_opening_shift
    )


@frappe.whitelist()
def delete_sales_invoice(sales_invoice):
    return invoice_lookup._delete_sales_invoice_with_retry(sales_invoice)


_delete_sales_invoice_with_retry = invoice_lookup._delete_sales_invoice_with_retry


@frappe.whitelist()
def get_sales_invoice_child_table(sales_invoice, sales_invoice_item=None):
    return invoice_lookup.get_sales_invoice_child_table(sales_invoice, sales_invoice_item=sales_invoice_item)

# @frappe.whitelist()
# def get_sales_invoice_child_table(sales_invoice, sales_invoice_item):
#     parent_doc = frappe.get_doc("Sales Invoice", sales_invoice)
#     child_doc = frappe.get_doc(
#         "Sales Invoice Item", {"parent": parent_doc.name, "name": sales_invoice_item}
#     )
#     return child_doc
