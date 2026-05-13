# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.sales_invoice import from_sales_order as sales_order_invoice


class TestSalesOrderInvoice(FrappeTestCase):
    @patch.object(sales_order_invoice, "make_sales_invoice")
    @patch.object(sales_order_invoice.frappe, "get_doc")
    @patch.object(sales_order_invoice, "_get_draft_invoice_for_sales_order")
    def test_make_or_get_sales_invoice_reuses_existing_draft(
        self, get_draft_invoice, get_doc, make_sales_invoice
    ):
        get_draft_invoice.return_value = "ACC-SINV-DRAFT"
        draft = Mock()
        draft.as_dict.return_value = {"name": "ACC-SINV-DRAFT"}
        get_doc.return_value = draft

        result = sales_order_invoice.make_or_get_sales_invoice_from_order(
            "SO-1", pos_profile="POS TEST SA CASHIER", pos_opening_shift="POSA-OS-1"
        )

        self.assertEqual(result, {"name": "ACC-SINV-DRAFT"})
        get_doc.assert_called_once_with("Sales Invoice", "ACC-SINV-DRAFT")
        make_sales_invoice.assert_not_called()

    @patch.object(sales_order_invoice, "make_sales_invoice")
    @patch.object(sales_order_invoice, "_get_draft_invoice_for_sales_order")
    def test_make_or_get_sales_invoice_maps_new_invoice_when_no_draft(
        self, get_draft_invoice, make_sales_invoice
    ):
        get_draft_invoice.return_value = ""
        invoice = Mock()
        invoice.as_dict.return_value = {"doctype": "Sales Invoice", "name": None}
        make_sales_invoice.return_value = invoice

        result = sales_order_invoice.make_or_get_sales_invoice_from_order("SO-1")

        self.assertEqual(result["doctype"], "Sales Invoice")
        make_sales_invoice.assert_called_once_with("SO-1", ignore_permissions=True)

    @patch.object(sales_order_invoice.frappe, "get_doc")
    def test_update_invoice_from_order_updates_existing_invoice(self, get_doc):
        invoice = Mock()
        get_doc.return_value = invoice

        result = sales_order_invoice.update_invoice_from_order_data(
            {"name": "ACC-SINV-DRAFT", "customer": "CUST-1"}
        )

        self.assertIs(result, invoice)
        get_doc.assert_called_once_with("Sales Invoice", "ACC-SINV-DRAFT")
        invoice.update.assert_called_once_with({"name": "ACC-SINV-DRAFT", "customer": "CUST-1"})
        invoice.save.assert_called_once_with()
        self.assertTrue(invoice.flags.ignore_permissions)

    @patch.object(sales_order_invoice.frappe.db, "sql")
    @patch.object(sales_order_invoice.frappe.db, "has_column", return_value=True)
    def test_get_draft_invoice_for_sales_order_scopes_by_profile_and_shift(self, _has_column, sql):
        sql.return_value = [frappe._dict({"name": "ACC-SINV-DRAFT"})]

        result = sales_order_invoice._get_draft_invoice_for_sales_order(
            "SO-1", pos_profile="POS TEST SA CASHIER", pos_opening_shift="POSA-OS-1"
        )

        query = sql.call_args.args[0]
        values = sql.call_args.args[1]
        self.assertEqual(result, "ACC-SINV-DRAFT")
        self.assertIn("sii.sales_order = %s", query)
        self.assertIn("si.pos_profile = %s", query)
        self.assertIn("si.posa_pos_opening_shift = %s", query)
        self.assertEqual(values, ["SO-1", "POS TEST SA CASHIER", "POSA-OS-1"])
