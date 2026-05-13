# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos import quotation_lookup


class TestQuotationLookup(FrappeTestCase):
    @patch.object(quotation_lookup, "_age_days_from_date", return_value=1)
    @patch.object(quotation_lookup.frappe, "get_doc")
    @patch.object(quotation_lookup.frappe, "get_list")
    @patch.object(quotation_lookup.frappe, "get_cached_value")
    def test_search_pos_quotations_adds_pos_metadata(
        self, get_cached_value, get_list, get_doc, _age_days_from_date
    ):
        today = "2026-05-13"
        get_cached_value.side_effect = lambda doctype, name, fieldname: {
            "company": "Portland Jewellers",
            "currency": "JMD",
            "posa_sales_order_lookup_max_age_days": 1,
            "posa_allow_stale_sales_order_fetch": 0,
            "posa_stale_sales_order_history_days": 30,
            "posa_quotation_validity_days": 7,
        }.get(fieldname)
        get_list.return_value = [
            frappe._dict(
                {
                    "name": "QTN-1",
                    "transaction_date": today,
                    "valid_till": today,
                }
            )
        ]
        quotation = frappe._dict(
            {
                "name": "QTN-1",
                "valid_till": today,
                "as_dict": lambda: frappe._dict(
                    {"name": "QTN-1", "valid_till": today}
                ),
            }
        )
        get_doc.return_value = quotation

        with patch.object(quotation_lookup, "nowdate", return_value=today):
            rows = quotation_lookup.search_pos_quotations(pos_profile="POS TEST SA CASHIER")

        self.assertEqual([row.quote_name for row in rows], ["QTN-1"])
        self.assertEqual(rows[0].age_days, 1)
        self.assertEqual(rows[0].is_stale, 0)
        self.assertEqual(rows[0].is_expired, 0)
        self.assertEqual(rows[0].stale_policy_max_age_days, 7)

    @patch.object(quotation_lookup.frappe, "get_cached_value", return_value=0)
    def test_require_quotation_permission_blocks_disabled_sales_associate(self, _get_cached_value):
        with self.assertRaises(frappe.ValidationError):
            quotation_lookup.require_quotation_permission("POS TEST SA CASHIER", "cline-Sales Associate")

    @patch.object(quotation_lookup.frappe, "get_cached_value", return_value=1)
    def test_require_quotation_permission_allows_enabled_cashier(self, _get_cached_value):
        quotation_lookup.require_quotation_permission("POS TEST SA CASHIER", "cline-Cashier")
