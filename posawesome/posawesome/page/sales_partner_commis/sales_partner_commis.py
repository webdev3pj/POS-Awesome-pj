import frappe
from frappe import _
from frappe.utils import now_datetime, flt


@frappe.whitelist()
def get_commission_data(sales_partner=None, payment_status="Pending"):
    filters = {}
    if sales_partner:
        filters["sales_partner"] = sales_partner

    data = frappe.get_all(
        "Sales Partner Commission Payment",
        filters=filters,
        fields=["name", "sales_partner", "commission", "mode_of_payment", "reference_sales_invoice"],
        order_by="creation desc"
    )

    filtered_data = []
    for row in data:
        si = frappe.get_doc("Sales Invoice", row["reference_sales_invoice"])
        if (payment_status == "Pending" and not si.custom_partner_commission_paid) or \
           (payment_status == "Paid" and si.custom_partner_commission_paid):
            row["commission"] = float(row["commission"])

            # For Paid, find the BPO record containing this invoice
            if payment_status == "Paid":
                # First find the parent BPO linked to this invoice
                bpo = frappe.db.sql("""
                    SELECT parent
                    FROM `tabSales Partner Commission Bulk Pay Out Items`
                    WHERE reference_sales_invoice = %s
                    LIMIT 1
                """, row["reference_sales_invoice"], as_dict=True)

                if bpo:
                    row["bpo_name"] = bpo[0].parent
                    # Now fetch posting_datetime from the parent doctype
                    row["bpo_datetime"] = frappe.db.get_value(
                        "Sales Partner Commission Bulk Pay Out",
                        bpo[0].parent,
                        "posting_datetime"
                    )
                else:
                    row["bpo_name"] = ""
                    row["bpo_datetime"] = ""


            filtered_data.append(row)

    return filtered_data







@frappe.whitelist()
def create_bulk_payout(data):
	import json
	if isinstance(data, str):
		data = json.loads(data)

	if not data:
		frappe.throw(_("No data received for bulk payout"))

	sales_partner = data[0].get("sales_partner")
	total_commission = 0

	doc = frappe.new_doc("Sales Partner Commission Bulk Pay Out")
	doc.sales_partner = sales_partner
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
	link = f'<a href="/app/sales-partner-commission-bulk-pay-out/{doc.name}" target="_blank">{doc.name}</a>'
	frappe.msgprint(_("Sales Partner Commission Bulk Pay Out created: {0}").format(link))

	return doc.name
