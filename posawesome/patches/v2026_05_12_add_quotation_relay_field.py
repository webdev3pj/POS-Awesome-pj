import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields(
        {
            "Quotation": [
                {
                    "fieldname": "custom_relay_quote_id",
                    "fieldtype": "Data",
                    "label": "Relay Quote ID",
                    "insert_after": "valid_till",
                    "read_only": 1,
                    "hidden": 1,
                    "description": "Stores the local relay quote identifier so offline quotation sync is idempotent.",
                    "module": "POSAwesome",
                }
            ]
        },
        update=True,
    )
    frappe.clear_cache(doctype="Quotation")
