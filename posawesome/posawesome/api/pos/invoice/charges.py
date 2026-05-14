import frappe

from posawesome.posawesome.doctype.delivery_charges.delivery_charges import (
    get_applicable_delivery_charges,
)


def auto_set_delivery_charges(doc):
    if not doc.pos_profile:
        return
    if not frappe.get_cached_value(
        "POS Profile", doc.pos_profile, "posa_auto_set_delivery_charges"
    ):
        return

    delivery_charges = get_applicable_delivery_charges(
        doc.company,
        doc.pos_profile,
        doc.customer,
        doc.shipping_address_name,
        doc.posa_delivery_charges,
        restrict=True,
    )

    if doc.posa_delivery_charges:
        if not doc.posa_delivery_charges_rate and delivery_charges:
            doc.posa_delivery_charges_rate = delivery_charges[0].rate
        return

    if delivery_charges:
        doc.posa_delivery_charges = delivery_charges[0].name
        doc.posa_delivery_charges_rate = delivery_charges[0].rate
    else:
        doc.posa_delivery_charges = None
        doc.posa_delivery_charges_rate = None


def calc_delivery_charges(doc):
    if not doc.pos_profile:
        return

    old_doc = None
    calculate_taxes_and_totals = False
    if not doc.is_new():
        old_doc = doc.get_doc_before_save()
        if not doc.posa_delivery_charges and not old_doc.posa_delivery_charges:
            return
    elif not doc.posa_delivery_charges:
        return

    if not doc.posa_delivery_charges:
        doc.posa_delivery_charges_rate = 0

    charges_doc = _set_delivery_rate_from_charge(doc)
    calculate_taxes_and_totals = _remove_old_delivery_tax(doc, old_doc)

    if doc.posa_delivery_charges:
        doc.append(
            "taxes",
            {
                "charge_type": "Actual",
                "description": doc.posa_delivery_charges,
                "tax_amount": doc.posa_delivery_charges_rate,
                "cost_center": charges_doc.cost_center,
                "account_head": charges_doc.shipping_account,
            },
        )
        calculate_taxes_and_totals = True

    if calculate_taxes_and_totals:
        doc.calculate_taxes_and_totals()


def _set_delivery_rate_from_charge(doc):
    if not doc.posa_delivery_charges:
        return None

    charges_doc = frappe.get_cached_doc("Delivery Charges", doc.posa_delivery_charges)
    doc.posa_delivery_charges_rate = charges_doc.default_rate
    charges_profile = next(
        (row for row in charges_doc.profiles if row.pos_profile == doc.pos_profile),
        None,
    )
    if charges_profile:
        doc.posa_delivery_charges_rate = charges_profile.rate
    return charges_doc


def _remove_old_delivery_tax(doc, old_doc):
    if not (old_doc and old_doc.posa_delivery_charges):
        return False
    old_charges = next(
        (
            row
            for row in doc.taxes
            if row.charge_type == "Actual"
            and row.description == old_doc.posa_delivery_charges
        ),
        None,
    )
    if not old_charges:
        return False
    doc.taxes.remove(old_charges)
    return True
