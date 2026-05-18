# -*- coding: utf-8 -*-
import subprocess

import frappe
from frappe import _
from frappe.utils import cstr

from posawesome.posawesome.api.pos import payment_request as pos_payment_request
from posawesome.posawesome.api.pos.catalog import (
    auto_create as catalog_auto_create,
    details as catalog_details,
    groups as catalog_groups,
    items as catalog_items,
    references as catalog_references,
    returns as catalog_returns,
    stock as catalog_stock,
)
from posawesome.posawesome.api.pos.customer import create as customer_create
from posawesome.posawesome.api.pos.customer import lookup as customer_lookup
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
from posawesome.posawesome.api.pos.invoice import (
    batch as invoice_batch,
    credit as invoice_credit,
    lookup as invoice_lookup,
    submit as invoice_submit,
    taxes as invoice_taxes,
)
from posawesome.posawesome.api.pos.invoice.document import update_invoice as update_pos_invoice
from posawesome.posawesome.api.pos.invoice.submit import submit_invoice as submit_pos_invoice
from posawesome.posawesome.api.pos.item.attributes import (
    build_item_cache as build_pos_item_cache,
    get_item_attributes as get_pos_item_attributes,
    get_item_optional_attributes as get_pos_item_optional_attributes,
)
from posawesome.posawesome.api.pos.item.lookup import (
    get_seearch_items_conditions as get_pos_search_items_conditions,
    search_serial_or_batch_or_barcode_number as search_pos_serial_or_batch_or_barcode_number,
)
from posawesome.posawesome.api.pos.offers.lookup import get_pos_offers
from posawesome.posawesome.api.pos.quotation.convert import (
    convert_quotation_to_sales_order_token as convert_pos_quotation_to_sales_order_token,
)
from posawesome.posawesome.api.pos.quotation.create import create_pos_quotation_token
from posawesome.posawesome.api.pos.quotation.lookup import (
    require_quotation_permission as _require_quotation_permission,
    search_pos_quotations,
)
from posawesome.posawesome.api.pos.quotation.reprice import get_quotation_reprice_preview
from posawesome.posawesome.api.pos.relay import (
    actions as relay_actions,
    connectivity as relay_connectivity,
    fulfillment as relay_fulfillment,
    monitor as relay_monitor,
    state as relay_state,
)
from posawesome.posawesome.api.pos.sales_invoice.from_sales_order import (
    make_or_get_sales_invoice_from_order,
    update_invoice_from_order_data,
)
from posawesome.posawesome.api.pos.sales_order.create import (
    create_sales_order_token as create_pos_sales_order_token,
)
from posawesome.posawesome.api.pos.sales_order.lookup import (
    get_sales_order_for_pos as get_pos_sales_order_for_pos,
    search_sales_orders,
)
from posawesome.posawesome.api.pos.session import opening as session_opening
from posawesome.posawesome.api.pos.session import roles as session_roles


def _whitelist(fn):
    return frappe.whitelist()(fn)
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
_set_invoice_cashier_attribution = invoice_submit._set_invoice_cashier_attribution
_delete_sales_invoice_with_retry = invoice_lookup._delete_sales_invoice_with_retry

get_item_group_condition = catalog_groups.get_item_group_condition
get_root_of = catalog_groups.get_root_of
get_customer_groups = catalog_groups.get_customer_groups
get_child_nodes = catalog_groups.get_child_nodes
get_customer_group_condition = catalog_groups.get_customer_group_condition
get_stock_availability = catalog_stock.get_stock_availability
add_taxes_from_tax_template = invoice_taxes.add_taxes_from_tax_template
set_batch_nos_for_bundels = invoice_batch.set_batch_nos_for_bundels
redeeming_customer_credit = invoice_credit.redeeming_customer_credit
submit_in_background_job = invoice_submit.submit_in_background_job
get_new_payment_request = pos_payment_request.get_new_payment_request
get_payment_gateway_account = pos_payment_request.get_payment_gateway_account
get_existing_payment_request = pos_payment_request.get_existing_payment_request
make_payment_request = pos_payment_request.make_payment_request
get_amount = pos_payment_request.get_amount
auto_create_items = catalog_auto_create.auto_create_items
build_item_cache = build_pos_item_cache
get_item_optional_attributes = get_pos_item_optional_attributes
get_company_domain = get_pos_company_domain
get_seearch_items_conditions = get_pos_search_items_conditions

check_opening_shift = _whitelist(session_opening.check_opening_shift)
bootstrap_pos_session = _whitelist(session_opening.bootstrap_pos_session)
get_items = _whitelist(catalog_items.get_items)
get_items_groups = _whitelist(catalog_groups.get_items_groups)
get_customer_names = _whitelist(customer_lookup.get_customer_names)
get_sales_person_names = _whitelist(catalog_references.get_sales_person_names)
get_sales_partner_names = _whitelist(catalog_references.get_sales_partner_names)
get_relay_connectivity_status = _whitelist(relay_connectivity.get_relay_connectivity_status)
get_relay_workflow_state = _whitelist(relay_fulfillment.get_relay_workflow_state)
get_relay_fulfillment_detail = _whitelist(relay_fulfillment.get_relay_fulfillment_detail)
get_relay_pick_queue = _whitelist(relay_fulfillment.get_relay_pick_queue)
get_relay_workflow_monitor_board = _whitelist(relay_monitor.get_relay_workflow_monitor_board)
update_relay_picking_status = _whitelist(relay_actions.update_relay_picking_status)
release_relay_dispatch = _whitelist(relay_actions.release_relay_dispatch)
update_invoice_from_order = _whitelist(update_invoice_from_order_data)
create_sales_order_token = _whitelist(create_pos_sales_order_token)
update_invoice = _whitelist(update_pos_invoice)
submit_invoice = _whitelist(submit_pos_invoice)
get_available_credit = _whitelist(invoice_credit.get_available_credit)
get_draft_invoices = _whitelist(invoice_lookup.get_draft_invoices)
delete_invoice = _whitelist(invoice_lookup.delete_invoice)
get_items_details = _whitelist(catalog_details.get_items_details)
get_item_detail = _whitelist(catalog_details.get_item_detail)
create_customer = _whitelist(customer_create.create_customer)
get_items_from_barcode = _whitelist(catalog_details.get_items_from_barcode)
set_customer_info = _whitelist(customer_create.set_customer_info)
search_invoices_for_return = _whitelist(catalog_returns.search_invoices_for_return)
search_orders = _whitelist(search_sales_orders)
get_sales_order_for_pos = _whitelist(get_pos_sales_order_for_pos)
get_offers = _whitelist(get_pos_offers)
get_customer_addresses = _whitelist(get_pos_customer_addresses)
make_address = _whitelist(make_pos_address)
get_item_attributes = _whitelist(get_pos_item_attributes)
create_payment_request = _whitelist(pos_payment_request.create_payment_request)
get_pos_coupon = _whitelist(get_pos_coupon_code)
get_active_gift_coupons = _whitelist(get_pos_active_gift_coupons)
get_customer_info = _whitelist(get_pos_customer_info)
get_applicable_delivery_charges = _whitelist(get_pos_delivery_charges)
search_serial_or_batch_or_barcode_number = _whitelist(search_pos_serial_or_batch_or_barcode_number)
create_sales_invoice_from_order = _whitelist(make_or_get_sales_invoice_from_order)
delete_sales_invoice = _whitelist(invoice_lookup._delete_sales_invoice_with_retry)
get_sales_invoice_child_table = _whitelist(invoice_lookup.get_sales_invoice_child_table)


@frappe.whitelist()
def get_opening_dialog_data():
    return session_opening.get_opening_dialog_data(erpnext_version=get_version())


@frappe.whitelist()
def create_opening_voucher(pos_profile, company, balance_details):
    return session_opening.create_opening_voucher(
        pos_profile,
        company,
        balance_details,
        relay_workflow_enabled_fn=_is_relay_workflow_enabled,
    )


@frappe.whitelist()
def create_quotation_token(data):
    role = session_roles.require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "create quotations",
        allow_relay_sync=True,
    )
    return create_pos_quotation_token(data, role=role)


@frappe.whitelist()
def search_quotations(company=None, currency=None, pos_profile=None, quote_name=None, allow_stale=None, history_days=None):
    pos_profile = cstr(pos_profile or "").strip()
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))
    role = session_roles.require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "search quotations",
    )
    _require_quotation_permission(pos_profile, role)
    return search_pos_quotations(company, currency, pos_profile, quote_name, allow_stale, history_days)


@frappe.whitelist()
def quotation_reprice_preview(quotation_name, pos_profile):
    role = session_roles.require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "preview quotation repricing",
    )
    return get_quotation_reprice_preview(quotation_name, pos_profile, role=role)


@frappe.whitelist()
def convert_quotation_to_sales_order_token(quotation_name, pos_profile, confirm_reprice=1, order_name=None):
    role = session_roles.require_operational_role_for_action(
        ("cline-Sales Associate", "cline-Cashier", "cline-Supervisor"),
        "convert quotation to sales order token",
    )
    return convert_pos_quotation_to_sales_order_token(
        quotation_name,
        pos_profile,
        confirm_reprice,
        role,
        quotation_reprice_preview,
        create_sales_order_token,
        order_name=order_name,
    )


def get_version():
    branch_name = get_app_branch("erpnext")
    if "12" in branch_name:
        return 12
    return 13


def get_app_branch(app):
    try:
        branch = subprocess.check_output(
            "cd ../apps/{0} && git rev-parse --abbrev-ref HEAD".format(app),
            shell=True,
        )
        return branch.decode("utf-8").strip()
    except Exception:
        return ""
