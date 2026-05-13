# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.quotation import create


class TestQuotationCreate(FrappeTestCase):
    @patch.object(create.frappe.db, "get_value")
    @patch.object(create.frappe, "get_meta")
    def test_get_existing_quotation_payload_is_idempotent(self, get_meta, get_value):
        get_value.return_value = "SAL-QTN-1"
        doc = frappe._dict(
            {
                "name": "SAL-QTN-1",
                "valid_till": "2026-05-20",
                "transaction_date": "2026-05-13",
                "grand_total": 100,
                "currency": "JMD",
                "customer": "CUST-1",
                "as_dict": lambda: {"name": "SAL-QTN-1"},
            }
        )
        with patch.object(create.frappe, "get_doc", return_value=doc), patch.object(
            create, "nowdate", return_value="2026-05-13"
        ):
            payload = create._get_existing_quotation_payload("custom_relay_quote_id", "relay-1")

        self.assertEqual(payload["quote_name"], "SAL-QTN-1")
        self.assertEqual(payload["quote_id"], "relay-1")
        self.assertEqual(payload["is_expired"], 0)
        self.assertEqual(payload["idempotent_replay"], 1)

    @patch.object(create.frappe, "get_meta")
    def test_append_quotation_items_maps_supported_fields(self, get_meta):
        meta = Mock()
        meta.has_field.return_value = True
        get_meta.return_value = meta
        quotation_doc = Mock()
        row = Mock()
        quotation_doc.append.return_value = row

        create._append_quotation_items(
            quotation_doc,
            [
                {
                    "item_code": "ITEM-1",
                    "qty": 2,
                    "uom": "Nos",
                    "rate": 10,
                    "conversion_factor": 1,
                    "discount_percentage": 5,
                    "discount_amount": 1,
                    "price_list_rate": 11,
                    "warehouse": "Stores - PJ",
                    "posa_delivery_date": "2026-05-20",
                },
                {"item_code": ""},
            ],
            valid_till="2026-05-21",
        )

        quotation_doc.append.assert_called_once_with("items", {})
        self.assertEqual(row.item_code, "ITEM-1")
        self.assertEqual(row.qty, 2)
        self.assertEqual(row.rate, 10)
        self.assertEqual(row.discount_percentage, 5)
        self.assertEqual(row.warehouse, "Stores - PJ")
        self.assertEqual(row.delivery_date, "2026-05-20")

    def test_create_pos_quotation_token_requires_profile(self):
        with self.assertRaises(frappe.ValidationError):
            create.create_pos_quotation_token({}, role="cline-Cashier")
