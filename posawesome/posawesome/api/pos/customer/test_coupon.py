# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.customer import coupon


class TestCustomerCoupon(FrappeTestCase):
    @patch.object(coupon, "check_coupon_code", return_value={"coupon": "PROMO"})
    def test_get_pos_coupon_delegates_to_coupon_doctype(self, check_coupon_code):
        self.assertEqual(
            coupon.get_pos_coupon("PROMO", "CUST-1", "Test Company"),
            {"coupon": "PROMO"},
        )
        check_coupon_code.assert_called_once_with("PROMO", "CUST-1", "Test Company")

    @patch.object(coupon.frappe, "get_all")
    def test_get_active_gift_coupons_returns_codes(self, get_all):
        get_all.return_value = [
            frappe._dict({"coupon_code": "GIFT-1"}),
            frappe._dict({"coupon_code": "GIFT-2"}),
        ]

        self.assertEqual(
            coupon.get_active_gift_coupons("CUST-1", "Test Company"),
            ["GIFT-1", "GIFT-2"],
        )
        self.assertEqual(get_all.call_args.kwargs["filters"]["used"], 0)

