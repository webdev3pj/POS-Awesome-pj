import frappe
from frappe import _
from frappe.utils import flt

def custom_calculate_commission(self):
    if not self.meta.get_field("commission_rate") or self.docstatus.is_submitted():
        return

    self.round_floats_in(self, ("amount_eligible_for_commission", "commission_rate"))

    if not (0 <= self.commission_rate <= 100.0):
        frappe.throw(
            "{} {}".format(
                _(self.meta.get_label("commission_rate")),
                _("must be between 0 and 100"),
            )
        )

    partner_rate = self.commission_rate
    total_commission = 0
    eligible_amount = 0

    # clear breakdown
    self.set("custom_commission_breakdown", [])

    for item in self.items:
        if not item.grant_commission:
            continue

        item_cap_rate = item.custom_max_commission_rate or partner_rate
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
