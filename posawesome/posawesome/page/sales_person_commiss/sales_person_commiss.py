import frappe
from frappe import _
from frappe.utils import now_datetime, flt


@frappe.whitelist()
def get_commission_data(sales_person=None, payment_status="Pending"):
    filters = {}
    if sales_person:
        filters["sales_person"] = sales_person

    data = frappe.get_all(
        "Sales Commission Payment",
        filters=filters,
        fields=["name", "sales_person", "commission", "mode_of_payment", "reference_sales_invoice"],
        order_by="creation desc"
    )

    # Filter by custom_commission_paid in linked Sales Invoice
    filtered_data = []
    for row in data:
        si = frappe.get_doc("Sales Invoice", row["reference_sales_invoice"])
        if (payment_status == "Pending" and not si.custom_commission_paid) or \
           (payment_status == "Paid" and si.custom_commission_paid):
            row["commission"] = float(row["commission"])
            filtered_data.append(row)

    return filtered_data





@frappe.whitelist()
def create_bulk_payout(data):
	import json
	if isinstance(data, str):
		data = json.loads(data)

	if not data:
		frappe.throw(_("No data received for bulk payout"))

	sales_person = data[0].get("sales_person")
	total_commission = 0

	doc = frappe.new_doc("Sales Person Commission Bulk Pay Out")
	doc.sales_person = sales_person
	doc.posting_datetime = now_datetime()

	for row in data:
		commission = flt(row.get("commission") or 0)
		total_commission += commission

		doc.append("items", {
			"reference_sales_invoice": row.get("reference_sales_invoice"),
			"commission": commission,
			"mode_of_payment": row.get("mode_of_payment")
		})

	doc.total_commission = total_commission
	doc.insert()

	# Generate clickable link (optional)
	link = f'<a href="/app/sales-person-commission-bulk-pay-out/{doc.name}" target="_blank">{doc.name}</a>'
	frappe.msgprint(_("Sales Person Commission Bulk Pay Out created: {0}").format(link))

	return doc.name
