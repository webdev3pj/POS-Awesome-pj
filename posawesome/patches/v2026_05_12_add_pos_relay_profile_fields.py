import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields(
        {
            "POS Profile": [
                {
                    "fieldname": "custom_pos_relay_section",
                    "fieldtype": "Section Break",
                    "label": "POS Relay",
                    "insert_after": "disabled",
                    "description": "Configuration for routing POS token and payment work through the local edge relay.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "custom_have_token",
                    "fieldtype": "Check",
                    "label": "Enable Token Workflow",
                    "insert_after": "custom_pos_relay_section",
                    "default": "0",
                    "description": "Enables Sales Associate token creation and Cashier/Pick/Dispatch relay workflow for this POS Profile.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "custom_edge_relay_url",
                    "fieldtype": "Data",
                    "label": "Edge Relay URL",
                    "insert_after": "custom_have_token",
                    "depends_on": "eval:doc.custom_have_token==1",
                    "description": "LAN URL for the local POS relay service used by this POS Profile, for example http://192.168.50.10:8787.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "posa_edge_relay_connectivity_mode",
                    "fieldtype": "Select",
                    "label": "Relay Connectivity Mode",
                    "insert_after": "custom_edge_relay_url",
                    "options": "cloud_checked\nlan_only_browser_checked",
                    "default": "cloud_checked",
                    "depends_on": "eval:doc.custom_have_token==1",
                    "description": "Chooses how POS verifies relay health: backend cloud check or browser LAN health check.",
                    "module": "POSAwesome",
                },
                {
                    "fieldname": "posa_allow_cloud_fallback_when_relay_down",
                    "fieldtype": "Check",
                    "label": "Allow Cloud Fallback When Relay Down",
                    "insert_after": "posa_edge_relay_connectivity_mode",
                    "default": "0",
                    "depends_on": "eval:doc.custom_have_token==1",
                    "description": "Allows Cashier submit through the cloud when the local relay is unavailable but Frappe is reachable.",
                    "module": "POSAwesome",
                },
            ]
        },
        update=True,
    )
    frappe.clear_cache(doctype="POS Profile")
