from posawesome.posawesome.api.pos.invoice.charges import (
    auto_set_delivery_charges,
    calc_delivery_charges,
)
from posawesome.posawesome.api.pos.invoice.coupons import update_coupon
from posawesome.posawesome.api.pos.invoice.loyalty import add_loyalty_point
from posawesome.posawesome.api.pos.invoice.patient import set_patient
from posawesome.posawesome.api.pos.invoice.sales_order import create_sales_order
from posawesome.posawesome.api.pos.invoice.validation import validate_shift


def validate(doc, method):
    validate_shift(doc)
    set_patient(doc)
    auto_set_delivery_charges(doc)
    calc_delivery_charges(doc)


def before_submit(doc, method):
    add_loyalty_point(doc)
    create_sales_order(doc)
    update_coupon(doc, "used")


def before_cancel(doc, method):
    update_coupon(doc, "cancelled")
