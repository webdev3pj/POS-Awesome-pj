import json

import frappe


RELAY_FIELD_ORDER = [
    "custom_pos_relay_section",
    "custom_have_token",
    "custom_edge_relay_url",
    "posa_edge_relay_connectivity_mode",
    "posa_allow_cloud_fallback_when_relay_down",
    "custom_pos_role_workflow_section",
    "posa_simplified_sa_cashier_ui",
    "custom_pos_quotation_column",
    "posa_allow_sa_quotation",
    "posa_allow_cashier_quotation",
    "posa_quotation_validity_days",
    "custom_pos_order_lookup_section",
    "posa_sales_order_naming_series",
    "posa_sales_order_lookup_max_age_days",
    "custom_pos_stale_order_column",
    "posa_allow_stale_sales_order_fetch",
    "posa_stale_sales_order_history_days",
]


def execute():
    setter_name = "POS Profile-main-field_order"
    if not frappe.db.exists("Property Setter", setter_name):
        frappe.clear_cache(doctype="POS Profile")
        return

    setter = frappe.get_doc("Property Setter", setter_name)
    try:
        field_order = json.loads(setter.value or "[]")
    except ValueError:
        frappe.clear_cache(doctype="POS Profile")
        return

    relay_fields = set(RELAY_FIELD_ORDER)
    cleaned = [field for field in field_order if field not in relay_fields]
    if "disabled" in cleaned:
        insert_at = cleaned.index("disabled") + 1
    else:
        insert_at = 0
    next_order = cleaned[:insert_at] + RELAY_FIELD_ORDER + cleaned[insert_at:]

    if next_order != field_order:
        setter.value = json.dumps(next_order)
        setter.save(ignore_permissions=True)

    frappe.clear_cache(doctype="POS Profile")
