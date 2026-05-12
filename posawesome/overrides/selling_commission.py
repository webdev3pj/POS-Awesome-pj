import frappe
from frappe import _
from frappe.utils import flt


def _safe_get_doc_precision(doc, fieldname, child=None, fallback=2):
    try:
        if child is not None:
            value = doc.precision(fieldname, child)
        else:
            value = doc.precision(fieldname)
        return int(value) if value is not None else fallback
    except Exception:
        return fallback


def _item_base_amount(item):
    # prefer explicit base_net_amount if available and non-zero
    base_net_amount = flt(getattr(item, "base_net_amount", 0) or 0)
    if base_net_amount:
        return base_net_amount

    qty = flt(getattr(item, "qty", 0) or 0)
    # fallback to price_list_rate path used by this customization
    price_list_rate = flt(getattr(item, "price_list_rate", 0) or 0)
    return qty * price_list_rate


def custom_calculate_commission(self):
    # ✅ Run only if Sales Partner is set
    if not self.sales_partner:
        return  

    if not self.meta.get_field("commission_rate") or int(getattr(self, "docstatus", 0) or 0) == 1:
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
    customer_rate = flt(self.custom_discount_ or 0)   # ✅ take customer share
    effective_rate = max(partner_rate - customer_rate, 0)  # ✅ ensure not negative

    total_commission = 0
    eligible_amount = 0

    # clear breakdown
    self.set("custom_commission_breakdown", [])

    applied_rate = 0
    for item in (self.items or []):
        if not getattr(item, "grant_commission", 0):
            continue

        tax_rate = 0
        if self.taxes_and_charges:
            tax_rows = frappe.get_all(
                "Sales Taxes and Charges",
                filters={"parent": self.taxes_and_charges},
                fields=["rate"]
            )
            if tax_rows:
                tax_rate = flt(tax_rows[0].rate)  # or sum if multiple

        # ✅ Exclude tax from Price List Rate
        item_amount = _item_base_amount(item)
        if tax_rate:
            item_amount = flt(item_amount) / (1 + (tax_rate / 100))

        item_cap_rate = flt(getattr(item, "custom_max_commission_rate", 0) or 0) or effective_rate
        applied_rate = min(effective_rate, item_cap_rate)

        commission_amount = item_amount * applied_rate / 100
        total_commission += commission_amount
        eligible_amount += item_amount

        self.append("custom_commission_breakdown", {
            "item_code": item.item_code,
            "base_net_amount": item_amount,
            "applied_rate": applied_rate,
            "commission_amount": commission_amount
        })


    self.amount_eligible_for_commission = eligible_amount
    self.total_commission = flt(total_commission, _safe_get_doc_precision(self, "total_commission"))

    # ✅ Set the additional fields
    self.custom_effective_commission_rate = applied_rate
    self.custom_effective_commission = eligible_amount




def run_custom_commission(doc, method):
    """Hook wrapper so it works in POS + Manual Invoices"""
    custom_calculate_commission(doc)



def custom_calculate_contribution(self):
    if not self.meta.get_field("sales_team"):
        return

    total = 0.0
    sales_team = self.get("sales_team") or []

    self.validate_sales_team(sales_team)

    # clear breakdown table
    self.set("custom_sales_person_commission_breakdown", [])
    self.amount_eligible_for_commission = sum(
        _item_base_amount(item) for item in (self.items or []) if getattr(item, "grant_commission", 0)
    )

    for sales_person in sales_team:
        self.round_floats_in(sales_person)

        sales_person.allocated_amount = flt(
            flt(self.amount_eligible_for_commission) * sales_person.allocated_percentage / 100.0,
            _safe_get_doc_precision(self, "allocated_amount", sales_person),
        )

        total_commission = 0

        if sales_person.commission_rate:
            for item in (self.items or []):
                if not getattr(item, "grant_commission", 0):
                    continue

                # ensure numeric values
                partner_rate = flt(sales_person.commission_rate)
                item_cap_rate = flt(getattr(item, "custom_sales_person_max_commission_rate", 0) or 0) or partner_rate

                applied_rate = partner_rate if partner_rate < item_cap_rate else item_cap_rate

                commission_amount = flt(_item_base_amount(item)) * applied_rate / 100
                total_commission += commission_amount

                self.append("custom_sales_person_commission_breakdown", {
                    "sales_person": sales_person.sales_person,
                    "item_code": item.item_code,
                    "base_net_amount": flt(_item_base_amount(item)),
                    "applied_rate": applied_rate,
                    "commission_amount": commission_amount
                })


            sales_person.incentives = flt(
                total_commission,
                _safe_get_doc_precision(self, "incentives", sales_person),
            )

        total += sales_person.allocated_percentage

    if sales_team and total != 100.0:
        frappe.throw(_("Total allocated percentage for sales team should be 100"))
 

def run_custom_contribution(doc, method):
    """Hook wrapper so it works in POS + Manual Invoices"""
    custom_calculate_contribution(doc)


def run_all_commissions(doc, method):
    """Single hook entrypoint to ensure both partner and sales-person commission calculations run."""
    run_custom_commission(doc, method)
    run_custom_contribution(doc, method)
