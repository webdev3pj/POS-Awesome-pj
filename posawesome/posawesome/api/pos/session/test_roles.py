# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.session import roles


class TestSessionRoles(FrappeTestCase):
    def test_admin_role_testing_requires_administrator_developer_mode(self):
        with patch.object(roles.frappe, "session", SimpleNamespace(user="Administrator")):
            with patch.object(roles.frappe, "conf", {"developer_mode": 1}):
                self.assertTrue(roles.is_admin_role_testing_enabled())

        with patch.object(roles.frappe, "session", SimpleNamespace(user="cashier@example.com")):
            with patch.object(roles.frappe, "conf", {"developer_mode": 1}):
                self.assertFalse(roles.is_admin_role_testing_enabled())

    def test_admin_requested_test_role_uses_allowed_form_role(self):
        with patch.object(roles, "is_admin_role_testing_enabled", return_value=True):
            with patch.object(roles.frappe, "form_dict", {"session_role": "cline-Cashier"}):
                self.assertEqual(roles.admin_requested_test_role(), "cline-Cashier")

    def test_get_single_operational_role_requires_exactly_one_cline_role(self):
        with patch.object(roles, "admin_requested_test_role", return_value=""):
            with patch.object(
                roles.frappe,
                "get_roles",
                return_value=["Accounts User", "cline-Sales Associate"],
            ):
                self.assertEqual(roles.get_single_operational_role(), "cline-Sales Associate")

            with patch.object(
                roles.frappe,
                "get_roles",
                return_value=["cline-Sales Associate", "cline-Cashier"],
            ):
                self.assertEqual(roles.get_single_operational_role(), "")

    def test_require_operational_role_allows_relay_sync_short_circuit(self):
        with patch.object(roles, "is_relay_sync_request", return_value=True):
            self.assertEqual(
                roles.require_operational_role_for_action(
                    ("cline-Cashier",), "submit invoices", allow_relay_sync=True
                ),
                "__relay_sync__",
            )

    def test_require_operational_role_blocks_disallowed_role(self):
        with patch.object(roles, "get_single_operational_role", return_value="cline-Picker"):
            with self.assertRaises(frappe.ValidationError):
                roles.require_operational_role_for_action(
                    ("cline-Cashier",), "create POS opening shifts"
                )

