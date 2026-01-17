import frappe

def console(*data):
    frappe.publish_realtime(
        "toconsole",
        data,
        user=frappe.session.user
    )
