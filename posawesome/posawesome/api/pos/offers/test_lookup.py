# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.offers import lookup


class TestPosOffersLookup(FrappeTestCase):
    @patch.object(lookup.frappe.db, "sql", return_value=[{"name": "OFFER-1"}])
    @patch.object(lookup.frappe, "get_doc")
    def test_get_pos_offers_scopes_by_profile_company_warehouse(self, get_doc, sql):
        get_doc.return_value = SimpleNamespace(company="Portland Jewellers", warehouse="Stores - PJ")

        with patch.object(lookup, "nowdate", return_value="2026-05-13"):
            result = lookup.get_pos_offers("POS TEST SA CASHIER")

        self.assertEqual(result, [{"name": "OFFER-1"}])
        values = sql.call_args.kwargs["values"] if "values" in sql.call_args.kwargs else sql.call_args.args[1]
        self.assertEqual(values["company"], "Portland Jewellers")
        self.assertEqual(values["pos_profile"], "POS TEST SA CASHIER")
        self.assertEqual(values["warehouse"], "Stores - PJ")
        self.assertEqual(values["valid_from"], "2026-05-13")
