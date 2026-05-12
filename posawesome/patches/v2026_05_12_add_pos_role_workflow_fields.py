import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields(
        {
            "POS Profile": [
                {
                    "fieldname": "custom_pos_role_workflow_section",
                    "fieldtype": "Section Break",
                    "label": "POS Role Workflow",
                    "insert_after": "posa_allow_cloud_fallback_when_relay_down",
                    "depends_on": "eval:doc.custom_have_token==1",
                    "description": "Controls role-specific POS screens and actions for Sales Associate and Cashier users.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "posa_simplified_sa_cashier_ui",
                    "fieldtype": "Check",
                    "label": "Simplified SA and Cashier UI",
                    "insert_after": "custom_pos_role_workflow_section",
                    "default": "0",
                    "depends_on": "eval:doc.custom_have_token==1",
                    "description": "Simplifies role screens; Sales Associate hides Held, Return, and PAY buttons while Cashier handles payment.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "custom_pos_quotation_column",
                    "fieldtype": "Column Break",
                    "insert_after": "posa_simplified_sa_cashier_ui",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "posa_allow_sa_quotation",
                    "fieldtype": "Check",
                    "label": "Allow SA Quotation",
                    "insert_after": "custom_pos_quotation_column",
                    "default": "1",
                    "depends_on": "eval:doc.custom_have_token==1",
                    "description": "Allows Sales Associate users to create and select Quotations from POS.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "posa_allow_cashier_quotation",
                    "fieldtype": "Check",
                    "label": "Allow Cashier Quotation",
                    "insert_after": "posa_allow_sa_quotation",
                    "default": "1",
                    "depends_on": "eval:doc.custom_have_token==1",
                    "description": "Allows Cashier users to create and select Quotations from POS.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "posa_quotation_validity_days",
                    "fieldtype": "Int",
                    "label": "Quotation Validity (Days)",
                    "insert_after": "posa_allow_cashier_quotation",
                    "default": "7",
                    "depends_on": "eval:doc.custom_have_token==1",
                    "description": "Number of days POS Quotations remain valid before expiry.",
                    "module": "POSAwesome",
                },
            ]
        },
        update=True,
    )
    frappe.clear_cache(doctype="POS Profile")
