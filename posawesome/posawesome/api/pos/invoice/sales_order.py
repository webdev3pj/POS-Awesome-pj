import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt


def create_sales_order(doc):
    # Cashier SO to SI flow already links items to a Sales Order.
    if any(getattr(row, "sales_order", None) for row in (doc.items or [])):
        return

    if not _should_create_sales_order(doc):
        return

    sales_order_doc = make_sales_order(doc.name)
    if not sales_order_doc:
        return

    profile_so_naming_series = frappe.get_value(
        "POS Profile", doc.pos_profile, "posa_sales_order_naming_series"
    )
    if profile_so_naming_series and hasattr(sales_order_doc, "naming_series"):
        sales_order_doc.naming_series = profile_so_naming_series
    sales_order_doc.posa_notes = doc.posa_notes
    sales_order_doc.flags.ignore_permissions = True
    sales_order_doc.flags.ignore_account_permission = True
    sales_order_doc.save()
    sales_order_doc.submit()
    _show_sales_order_created(sales_order_doc)
    _link_invoice_items_to_sales_order(doc, sales_order_doc)


def _should_create_sales_order(doc):
    return (
        doc.posa_pos_opening_shift
        and doc.pos_profile
        and doc.is_pos
        and doc.posa_delivery_date
        and not doc.update_stock
        and frappe.get_value("POS Profile", doc.pos_profile, "posa_allow_sales_order")
    )


def make_sales_order(source_name, target_doc=None, ignore_permissions=True):
    def set_missing_values(source, target):
        target.ignore_pricing_rule = 1
        target.flags.ignore_permissions = ignore_permissions
        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

    def update_item(obj, target, source_parent):
        target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)
        target.delivery_date = (
            obj.posa_delivery_date or source_parent.posa_delivery_date
        )

    return get_mapped_doc(
        "Sales Invoice",
        source_name,
        {
            "Sales Invoice": {"doctype": "Sales Order"},
            "Sales Invoice Item": {
                "doctype": "Sales Order Item",
                "field_map": {
                    "cost_center": "cost_center",
                    "Warehouse": "warehouse",
                    "delivery_date": "posa_delivery_date",
                    "posa_notes": "posa_notes",
                },
                "postprocess": update_item,
            },
            "Sales Taxes and Charges": {
                "doctype": "Sales Taxes and Charges",
                "add_if_empty": True,
            },
            "Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
            "Payment Schedule": {"doctype": "Payment Schedule", "add_if_empty": True},
        },
        target_doc,
        set_missing_values,
        ignore_permissions=ignore_permissions,
    )


def _show_sales_order_created(sales_order_doc):
    url = frappe.utils.get_url_to_form(sales_order_doc.doctype, sales_order_doc.name)
    msgprint = "Sales Order Created at <a href='{0}'>{1}</a>".format(
        url, sales_order_doc.name
    )
    frappe.msgprint(_(msgprint), title="Sales Order Created", indicator="green", alert=True)


def _link_invoice_items_to_sales_order(doc, sales_order_doc):
    for index, item in enumerate(sales_order_doc.items):
        doc.items[index].sales_order = sales_order_doc.name
        doc.items[index].so_detail = item.name
