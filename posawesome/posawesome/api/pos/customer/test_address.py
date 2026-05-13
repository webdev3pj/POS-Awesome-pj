# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.customer import address


class TestCustomerAddress(FrappeTestCase):
    @patch.object(address.frappe.db, "sql", return_value=[])
    def test_get_customer_addresses_filters_dynamic_link_customer(self, sql):
        address.get_customer_addresses("CUST-1")

        self.assertIn("link.link_doctype = 'Customer'", sql.call_args[0][0])
        self.assertIn("link.link_name = 'CUST-1'", sql.call_args[0][0])
        self.assertEqual(sql.call_args.kwargs["as_dict"], 1)

    @patch.object(address.frappe, "get_doc")
    def test_make_address_builds_shipping_address(self, get_doc):
        inserted = Mock()
        doc = Mock()
        doc.insert.return_value = inserted
        get_doc.return_value = doc

        result = address.make_address(
            '{"name":"Ship To","address_line1":"Line 1","doctype":"Customer","customer":"CUST-1"}'
        )

        payload = get_doc.call_args[0][0]
        self.assertEqual(payload["doctype"], "Address")
        self.assertEqual(payload["address_type"], "Shipping")
        self.assertEqual(payload["links"][0]["link_name"], "CUST-1")
        self.assertEqual(result, inserted)

