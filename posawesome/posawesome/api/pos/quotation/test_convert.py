# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.quotation import convert


class TestQuotationConvert(FrappeTestCase):
    def test_build_sales_order_items_uses_repriced_rates(self):
        doc = SimpleNamespace(
            items=[
                frappe._dict(
                    {
                        "item_code": "ITEM-1",
                        "item_name": "Item 1",
                        "qty": 2,
                        "uom": "Nos",
                        "rate": 10,
                        "conversion_factor": 1,
                        "discount_percentage": 0,
                        "discount_amount": 0,
                        "price_list_rate": 10,
                        "warehouse": "Stores - PJ",
                        "delivery_date": "2026-05-20",
                    }
                )
            ]
        )
        preview = {"repriced_lines": [{"item_code": "ITEM-1", "new_rate": 15}]}

        items = convert._build_sales_order_items_from_quotation(doc, preview)

        self.assertEqual(items[0]["rate"], 15)
        self.assertEqual(items[0]["amount"], 30)
        self.assertEqual(items[0]["warehouse"], "Stores - PJ")

    @patch.object(convert, "require_quotation_permission")
    @patch.object(convert.frappe, "get_cached_value", return_value=7)
    @patch.object(convert.frappe, "get_doc")
    def test_convert_quotation_calls_sales_order_creator(self, get_doc, _get_cached_value, require_permission):
        doc = SimpleNamespace(
            name="SAL-QTN-1",
            valid_till="2026-05-20",
            transaction_date="2026-05-13",
            company="Portland Jewellers",
            customer="CUST-1",
            currency="JMD",
            discount_amount=0,
            additional_discount_percentage=0,
            items=[
                frappe._dict(
                    {
                        "item_code": "ITEM-1",
                        "item_name": "Item 1",
                        "qty": 1,
                        "uom": "Nos",
                        "rate": 10,
                        "conversion_factor": 1,
                        "discount_percentage": 0,
                        "discount_amount": 0,
                        "price_list_rate": 10,
                    }
                )
            ],
        )
        doc.get = Mock(side_effect=lambda fieldname, default=None: getattr(doc, fieldname, default))
        get_doc.return_value = doc
        reprice_preview_fn = Mock(return_value={"delta_total": 0, "repriced_lines": []})
        create_sales_order_token_fn = Mock(return_value={"sales_order_name": "SO-1"})

        with patch.object(convert, "nowdate", return_value="2026-05-13"):
            token = convert.convert_quotation_to_sales_order_token(
                "SAL-QTN-1",
                "POS TEST SA CASHIER",
                confirm_reprice=1,
                role="cline-Cashier",
                reprice_preview_fn=reprice_preview_fn,
                create_sales_order_token_fn=create_sales_order_token_fn,
                order_name="WALKIN-7",
            )

        require_permission.assert_called_once_with("POS TEST SA CASHIER", "cline-Cashier")
        create_sales_order_token_fn.assert_called_once()
        payload = create_sales_order_token_fn.call_args[0][0]
        self.assertEqual(payload["order_name"], "WALKIN-7")
        self.assertEqual(payload["posa_order_name"], "WALKIN-7")
        self.assertEqual(token["sales_order_name"], "SO-1")
        self.assertEqual(token["quote_name"], "SAL-QTN-1")
        self.assertEqual(token["quote_valid_till"], "2026-05-20")

    @patch.object(convert, "require_quotation_permission")
    @patch.object(convert.frappe, "get_cached_value", return_value=7)
    @patch.object(convert.frappe, "get_doc")
    def test_convert_quotation_requires_reprice_confirmation(
        self, get_doc, _get_cached_value, _require_permission
    ):
        doc = SimpleNamespace(valid_till="2026-05-20", transaction_date="2026-05-13", items=[])
        doc.get = Mock(side_effect=lambda fieldname, default=None: getattr(doc, fieldname, default))
        get_doc.return_value = doc

        with patch.object(convert, "nowdate", return_value="2026-05-13"):
            with self.assertRaises(frappe.ValidationError):
                convert.convert_quotation_to_sales_order_token(
                    "SAL-QTN-1",
                    "POS TEST SA CASHIER",
                    confirm_reprice=0,
                    role="cline-Cashier",
                    reprice_preview_fn=Mock(return_value={"delta_total": 5, "repriced_lines": []}),
                    create_sales_order_token_fn=Mock(),
                )
