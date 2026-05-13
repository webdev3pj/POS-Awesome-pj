# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.session import profile


class TestSessionProfile(FrappeTestCase):
    @patch.object(profile.frappe.db, "sql")
    def test_get_default_pos_profile_prefers_default_user_row(self, sql):
        sql.return_value = [frappe._dict({"name": "POS TEST DEFAULT"})]

        self.assertEqual(
            profile.get_default_pos_profile_for_user("cashier@example.com"),
            "POS TEST DEFAULT",
        )
        self.assertIn("pfu.default = 1", sql.call_args[0][0])

    @patch.object(profile.frappe.db, "sql")
    def test_get_default_pos_profile_falls_back_to_any_enabled_user_row(self, sql):
        sql.side_effect = [[], [frappe._dict({"name": "POS TEST FALLBACK"})]]

        self.assertEqual(
            profile.get_default_pos_profile_for_user("cashier@example.com"),
            "POS TEST FALLBACK",
        )
        self.assertEqual(sql.call_count, 2)

    def test_require_user_default_pos_profile_accepts_only_session_default(self):
        with patch.object(profile.frappe, "session", SimpleNamespace(user="cashier@example.com")):
            with patch.object(
                profile,
                "get_default_pos_profile_for_user",
                return_value="POS TEST DEFAULT",
            ):
                self.assertEqual(
                    profile.require_user_default_pos_profile("POS TEST DEFAULT"),
                    "POS TEST DEFAULT",
                )
                with self.assertRaises(frappe.ValidationError):
                    profile.require_user_default_pos_profile("OTHER POS")

