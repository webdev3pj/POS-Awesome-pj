import frappe


def execute():
    fieldname = "posa_order_name"
    name = f"Sales Order-{fieldname}"
    values = {
        "doctype": "Custom Field",
        "dt": "Sales Order",
        "fieldname": fieldname,
        "fieldtype": "Data",
        "label": "Order Name",
        "insert_after": "customer_name",
        "length": 140,
        "description": (
            "Customer-facing order nickname entered in POS, for example Nick, "
            "Table 3, or Walk-in."
        ),
        "in_global_search": 1,
        "in_standard_filter": 1,
        "search_index": 1,
        "module": "POSAwesome",
    }

    if frappe.db.exists("Custom Field", name):
        custom_field = frappe.get_doc("Custom Field", name)
        changed = False
        for key, value in values.items():
            if key == "doctype":
                continue
            if custom_field.get(key) != value:
                custom_field.set(key, value)
                changed = True
        if changed:
            custom_field.save(ignore_permissions=True)
    else:
        frappe.get_doc(values).insert(ignore_permissions=True)

    frappe.clear_cache(doctype="Sales Order")
