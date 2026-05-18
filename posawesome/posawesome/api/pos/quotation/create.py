# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, cstr, flt, getdate, nowdate

from posawesome.posawesome.api.pos.quotation.lookup import require_quotation_permission
from posawesome.posawesome.api.pos.sales_order.lookup import _age_days_from_date


def create_pos_quotation_token(data, role):
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
        require_quotation_permission(pos_profile, role)

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
        existing_payload = _get_existing_quotation_payload(relay_quote_fieldname, relay_quote_id)
        if existing_payload:
            return existing_payload

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

    _append_quotation_items(quotation_doc, items, valid_till)

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


def _get_existing_quotation_payload(relay_quote_fieldname, relay_quote_id):
    existing_quote_name = frappe.db.get_value(
        "Quotation",
        {relay_quote_fieldname: relay_quote_id},
        "name",
    )
    if not existing_quote_name:
        return None

    existing_doc = frappe.get_doc("Quotation", existing_quote_name)
    existing_doc.flags.ignore_permissions = True
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


def _append_quotation_items(quotation_doc, items, valid_till):
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
