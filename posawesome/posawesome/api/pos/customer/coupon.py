# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe

from posawesome.posawesome.doctype.pos_coupon.pos_coupon import check_coupon_code


def get_pos_coupon(coupon, customer, company):
    return check_coupon_code(coupon, customer, company)


def get_active_gift_coupons(customer, company):
    coupons = []
    coupons_data = frappe.get_all(
        "POS Coupon",
        filters={
            "company": company,
            "coupon_type": "Gift Card",
            "customer": customer,
            "used": 0,
        },
        fields=["coupon_code"],
    )
    if len(coupons_data):
        coupons = [i.coupon_code for i in coupons_data]
    return coupons

