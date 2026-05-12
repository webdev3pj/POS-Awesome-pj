import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields(
        {
            "POS Profile": [
                {
                    "fieldname": "custom_pos_order_lookup_section",
                    "fieldtype": "Section Break",
                    "label": "POS Sales Order Lookup",
                    "insert_after": "posa_quotation_validity_days",
                    "depends_on": "eval:doc.custom_have_token==1",
                    "description": "Controls how Cashier users find Sales Associate orders from POS.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "posa_sales_order_naming_series",
                    "fieldtype": "Data",
                    "label": "Sales Order Naming Series",
                    "insert_after": "custom_pos_order_lookup_section",
                    "description": "Optional Sales Order naming series for this POS Profile; blank uses the ERPNext default series.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "posa_sales_order_lookup_max_age_days",
                    "fieldtype": "Int",
                    "label": "Select S.O Max Age (Days)",
                    "insert_after": "posa_sales_order_naming_series",
                    "default": "1",
                    "description": "Cashier Select S.O shows Sales Orders newer than this many days by default.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "custom_pos_stale_order_column",
                    "fieldtype": "Column Break",
                    "insert_after": "posa_sales_order_lookup_max_age_days",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "posa_allow_stale_sales_order_fetch",
                    "fieldtype": "Check",
                    "label": "Allow Stale Select S.O Fetch",
                    "insert_after": "custom_pos_stale_order_column",
                    "default": "0",
                    "description": "Allows older Sales Orders to be searched and selected with a warning.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "posa_stale_sales_order_history_days",
                    "fieldtype": "Int",
                    "label": "Stale Select S.O History (Days)",
                    "insert_after": "posa_allow_stale_sales_order_fetch",
                    "default": "30",
                    "depends_on": "eval:doc.posa_allow_stale_sales_order_fetch==1",
                    "description": "Maximum search window when stale Sales Order lookup is allowed.",
                    "module": "POSAwesome",
                },
            ]
        },
        update=True,
    )
    frappe.clear_cache(doctype="POS Profile")
