import frappe
from frappe import _
from frappe.utils import flt

def custom_calculate_commission(self):
    # ✅ Run only if Sales Partner is set
    if not self.sales_partner:
        return  

    if not self.meta.get_field("commission_rate") or self.docstatus.is_submitted():
        return

    self.round_floats_in(self, ("amount_eligible_for_commission", "commission_rate"))

    if not (0 <= flt(self.commission_rate) <= 100.0):
        frappe.throw(
            "{} {}".format(
                _(self.meta.get_label("commission_rate")),
                _("must be between 0 and 100"),
            )
        )

    partner_rate = flt(self.commission_rate)
    total_commission = 0
    eligible_amount = 0

    # clear breakdown
    self.set("custom_commission_breakdown", [])

    for item in self.items:
        if not item.grant_commission:
            continue

        item_cap_rate = flt(item.custom_max_commission_rate) or partner_rate
        applied_rate = partner_rate if partner_rate < item_cap_rate else item_cap_rate

        commission_amount = (item.base_net_amount or 0) * applied_rate / 100
        total_commission += commission_amount
        eligible_amount += item.base_net_amount or 0

        self.append("custom_commission_breakdown", {
            "item_code": item.item_code,
            "base_net_amount": item.base_net_amount,
            "applied_rate": applied_rate,
            "commission_amount": commission_amount
        })

    self.amount_eligible_for_commission = eligible_amount
    self.total_commission = flt(total_commission, self.precision("total_commission"))



def run_custom_commission(doc, method):
    """Hook wrapper so it works in POS + Manual Invoices"""
    custom_calculate_commission(doc)


def custom_calculate_contribution(self):
    if not self.meta.get_field("sales_team"):
        return

    total = 0.0
    sales_team = self.get("sales_team")

    self.validate_sales_team(sales_team)

    # clear breakdown table
    self.set("custom_sales_person_commission_breakdown", [])
    self.amount_eligible_for_commission = sum(
			item.base_net_amount for item in self.items if item.grant_commission
		)

    for sales_person in sales_team:
        self.round_floats_in(sales_person)

        sales_person.allocated_amount = flt(
            flt(self.amount_eligible_for_commission) * sales_person.allocated_percentage / 100.0,
            self.precision("allocated_amount", sales_person),
        )

        total_commission = 0

        if sales_person.commission_rate:
            for item in self.items:
                if not item.grant_commission:
                    continue

                # ensure numeric values
                partner_rate = flt(sales_person.commission_rate)
                item_cap_rate = flt(item.custom_sales_person_max_commission_rate) or partner_rate

                applied_rate = partner_rate if partner_rate < item_cap_rate else item_cap_rate

                commission_amount = (flt(item.base_net_amount) or 0) * applied_rate / 100
                total_commission += commission_amount

                self.append("custom_sales_person_commission_breakdown", {
                    "sales_person": sales_person.sales_person,
                    "item_code": item.item_code,
                    "base_net_amount": flt(item.base_net_amount),
                    "applied_rate": applied_rate,
                    "commission_amount": commission_amount
                })


            sales_person.incentives = flt(
                total_commission,
                self.precision("incentives", sales_person),
            )

        total += sales_person.allocated_percentage

    if sales_team and total != 100.0:
        frappe.throw(_("Total allocated percentage for sales team should be 100"))
 

def run_custom_contribution(doc, method):
    """Hook wrapper so it works in POS + Manual Invoices"""
    custom_calculate_contribution(doc)