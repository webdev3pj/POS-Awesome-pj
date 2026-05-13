# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos import sales_order_lookup


class TestSalesOrderLookup(FrappeTestCase):
    @patch.object(sales_order_lookup, "_doctype_has_column", return_value=False)
    @patch.object(sales_order_lookup, "_get_sales_order_items_for_lookup")
    @patch.object(sales_order_lookup, "_get_sales_orders_with_submitted_invoice")
    @patch.object(sales_order_lookup.frappe, "get_list")
    @patch.object(sales_order_lookup.frappe, "get_cached_value")
    def test_search_sales_orders_filters_paid_orders_and_batches_items(
        self,
        get_cached_value,
        get_list,
        get_invoiced_orders,
        get_items,
        _doctype_has_column,
    ):
        get_cached_value.side_effect = lambda doctype, name, fieldname: {
            "posa_sales_order_lookup_max_age_days": 1,
            "posa_allow_stale_sales_order_fetch": 0,
            "posa_stale_sales_order_history_days": 30,
            "posa_sales_order_naming_series": "",
        }.get(fieldname)
        get_list.return_value = [
            frappe._dict(
                {
                    "name": "SO-OPEN",
                    "transaction_date": sales_order_lookup.nowdate(),
                    "customer": "CUST-1",
                    "customer_name": "Customer 1",
                    "grand_total": 100,
                    "currency": "JMD",
                    "billing_status": "Not Billed",
                    "status": "To Bill",
                }
            ),
            frappe._dict(
                {
                    "name": "SO-PAID",
                    "transaction_date": sales_order_lookup.nowdate(),
                    "customer": "CUST-2",
                    "customer_name": "Customer 2",
                    "grand_total": 200,
                    "currency": "JMD",
                    "billing_status": "Not Billed",
                    "status": "To Bill",
                }
            ),
        ]
        get_invoiced_orders.return_value = {"SO-PAID"}
        get_items.return_value = {"SO-OPEN": [frappe._dict({"item_code": "ITEM-1"})]}

        rows = sales_order_lookup.search_sales_orders(
            company="Portland Jewellers",
            currency="JMD",
            pos_profile="POS TEST SA CASHIER",
        )

        self.assertEqual([row.name for row in rows], ["SO-OPEN"])
        self.assertEqual(rows[0].doctype, "Sales Order")
        self.assertEqual(rows[0]["items"][0].item_code, "ITEM-1")
        self.assertEqual(rows[0].is_stale, 0)
        self.assertEqual(get_list.call_args.kwargs["limit_page_length"], 50)
        self.assertIn("billing_status", get_list.call_args.kwargs["filters"])
        get_invoiced_orders.assert_called_once_with(["SO-OPEN", "SO-PAID"])
        get_items.assert_called_once_with(["SO-OPEN"])

    @patch.object(sales_order_lookup.frappe.db, "sql")
    def test_get_sales_orders_with_submitted_invoice_returns_distinct_so_names(self, sql):
        sql.return_value = [frappe._dict({"sales_order": "SO-1"})]

        result = sales_order_lookup._get_sales_orders_with_submitted_invoice(["SO-1", "SO-2"])

        self.assertEqual(result, {"SO-1"})
        self.assertIn("si.docstatus = 1", sql.call_args.args[0])
        self.assertEqual(sql.call_args.args[1], {"sales_orders": ("SO-1", "SO-2")})


class TestSalesOrderLookupHelpers(FrappeTestCase):
    @patch.object(sales_order_lookup.frappe, "get_meta")
    def test_doctype_has_column_requires_meta_and_database_column(self, get_meta):
        meta = Mock()
        meta.has_field.return_value = True
        get_meta.return_value = meta
        with patch.object(sales_order_lookup.frappe.db, "has_column", return_value=True):
            self.assertTrue(sales_order_lookup._doctype_has_column("Sales Order", "posa_order_name"))
