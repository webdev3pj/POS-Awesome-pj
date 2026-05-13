# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.customer import info


class TestCustomerInfo(FrappeTestCase):
    @patch.object(info, "get_loyalty_program_details_with_points")
    @patch.object(info.frappe, "get_value", return_value="Retail Price List")
    @patch.object(info.frappe, "get_doc")
    def test_get_customer_info_includes_loyalty_details(
        self, get_doc, _get_value, loyalty_details
    ):
        get_doc.return_value = SimpleNamespace(
            email_id="customer@example.com",
            mobile_no="123",
            image=None,
            loyalty_program="LP",
            default_price_list="Standard Selling",
            customer_group="Retail",
            customer_type="Individual",
            territory="All Territories",
            posa_birthday=None,
            gender=None,
            tax_id="TAX",
            posa_discount=0,
            name="CUST-1",
            customer_name="Customer One",
        )
        loyalty_details.return_value = {"loyalty_points": 10, "conversion_factor": 0.5}

        data = info.get_customer_info("CUST-1")

        self.assertEqual(data["name"], "CUST-1")
        self.assertEqual(data["loyalty_points"], 10)
        self.assertEqual(data["conversion_factor"], 0.5)

    @patch.object(info.frappe, "get_cached_value", return_value="Retail")
    def test_get_company_domain_uses_cstr_company(self, get_cached_value):
        self.assertEqual(info.get_company_domain(" Test Company "), "Retail")
        get_cached_value.assert_called_once_with("Company", " Test Company ", "domain")
