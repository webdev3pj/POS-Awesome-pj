# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.item import lookup


class TestItemLookup(FrappeTestCase):
    @patch.object(lookup.frappe.db, "get_value")
    def test_search_prefers_barcode_before_serial_and_batch(self, get_value):
        get_value.return_value = frappe._dict({"barcode": "BC-1", "item_code": "ITEM-1"})

        self.assertEqual(
            lookup.search_serial_or_batch_or_barcode_number("BC-1", search_serial_no=True),
            {"barcode": "BC-1", "item_code": "ITEM-1"},
        )
        get_value.assert_called_once()

    @patch.object(lookup.frappe.db, "get_value")
    def test_search_checks_batch_when_barcode_and_serial_missing(self, get_value):
        get_value.side_effect = [
            None,
            None,
            frappe._dict({"batch_no": "BATCH-1", "item_code": "ITEM-1"}),
        ]

        self.assertEqual(
            lookup.search_serial_or_batch_or_barcode_number("BATCH-1", search_serial_no=True),
            {"batch_no": "BATCH-1", "item_code": "ITEM-1"},
        )
        self.assertEqual(get_value.call_count, 3)

    @patch.object(lookup.frappe.db, "escape", side_effect=lambda value: "'{0}'".format(value))
    def test_get_search_items_conditions_uses_exact_name_for_batch_or_serial(self, _escape):
        self.assertEqual(
            lookup.get_seearch_items_conditions("ITEM-1", "", "BATCH-1", ""),
            " and name = 'ITEM-1'",
        )

    @patch.object(lookup.frappe.db, "escape", side_effect=lambda value: "'{0}'".format(value))
    def test_get_search_items_conditions_searches_name_and_item_name(self, _escape):
        self.assertEqual(
            lookup.get_seearch_items_conditions("ring", "", "", ""),
            " and (name like '%ring%' or item_name like '%ring%')",
        )

