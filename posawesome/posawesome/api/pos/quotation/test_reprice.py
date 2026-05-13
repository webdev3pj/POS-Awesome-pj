# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.quotation import reprice


class TestQuotationReprice(FrappeTestCase):
    @patch.object(reprice, "require_quotation_permission")
    @patch.object(reprice, "latest_item_rate_for_profile", return_value=15)
    @patch.object(reprice.frappe, "get_doc")
    def test_get_quotation_reprice_preview_returns_delta(self, get_doc, _latest_rate, require_permission):
        doc = SimpleNamespace(
            name="SAL-QTN-1",
            company="Portland Jewellers",
            party_name="CUST-1",
            currency="JMD",
            transaction_date="2026-05-13",
            valid_till="2026-05-20",
            items=[
                frappe._dict(
                    {
                        "item_code": "ITEM-1",
                        "item_name": "Item 1",
                        "qty": 2,
                        "uom": "Nos",
                        "rate": 10,
                        "amount": 20,
                    }
                )
            ],
        )
        doc.get = Mock(side_effect=lambda fieldname, default=None: getattr(doc, fieldname, default))
        get_doc.return_value = doc

        with patch.object(reprice, "nowdate", return_value="2026-05-13"):
            result = reprice.get_quotation_reprice_preview(
                "SAL-QTN-1", "POS TEST SA CASHIER", role="cline-Cashier"
            )

        require_permission.assert_called_once_with("POS TEST SA CASHIER", "cline-Cashier")
        self.assertEqual(result["old_total"], 20)
        self.assertEqual(result["new_total"], 30)
        self.assertEqual(result["delta_total"], 10)
        self.assertEqual(result["repriced_lines"][0]["new_rate"], 15)

    @patch.object(reprice.frappe, "get_all")
    @patch.object(reprice.frappe, "get_cached_value", return_value="SELLING PJ7")
    def test_latest_item_rate_for_profile_uses_profile_price_list(self, get_cached_value, get_all):
        get_all.return_value = [frappe._dict({"price_list_rate": 25})]

        result = reprice.latest_item_rate_for_profile(
            "ITEM-1", "POS TEST SA CASHIER", currency="JMD"
        )

        self.assertEqual(result, 25)
        self.assertEqual(get_all.call_args.kwargs["filters"]["price_list"], "SELLING PJ7")
        self.assertEqual(get_all.call_args.kwargs["filters"]["currency"], "JMD")

    @patch.object(reprice.frappe, "get_cached_value", return_value="")
    def test_latest_item_rate_for_profile_returns_zero_without_price_list(self, _get_cached_value):
        self.assertEqual(reprice.latest_item_rate_for_profile("ITEM-1", "POS TEST SA CASHIER"), 0)
