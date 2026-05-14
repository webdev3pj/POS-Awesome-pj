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
