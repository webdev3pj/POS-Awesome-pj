# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import json



import frappe

from frappe import _

from frappe.utils import cint, cstr, flt, now_datetime, nowdate



from posawesome.posawesome.api.pos.relay.state import _upsert_relay_workflow_state_for_sales_order

from posawesome.posawesome.api.pos.session.roles import require_operational_role_for_action



def create_sales_order_token(data):
    role = require_operational_role_for_action(
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
