# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.delivery import charges


class TestDeliveryCharges(FrappeTestCase):
    @patch.object(charges, "get_delivery_charges", return_value={"amount": 5})
    def test_get_applicable_delivery_charges_delegates(self, get_delivery_charges):
        self.assertEqual(
            charges.get_applicable_delivery_charges(
                "Test Company", "POS TEST", "CUST-1", "ADDR-1"
            ),
            {"amount": 5},
        )
        get_delivery_charges.assert_called_once_with(
            "Test Company", "POS TEST", "CUST-1", "ADDR-1"
        )

