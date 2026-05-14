# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from types import SimpleNamespace
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.session import bootstrap, dialog, opening


class TestSessionOpening(FrappeTestCase):
    @patch.object(dialog.frappe, "get_cached_value")
    @patch.object(dialog.frappe, "get_list")
    @patch.object(dialog.frappe, "get_cached_doc")
    @patch.object(dialog.frappe, "get_roles", return_value=["cline-Sales Associate"])
    @patch.object(dialog, "is_admin_role_testing_enabled", return_value=False)
    @patch.object(dialog, "get_default_pos_profile_for_user", return_value="POS TEST")
    def test_opening_dialog_uses_user_default_profile(
        self,
        _default_profile,
        _admin_testing,
        _get_roles,
        get_cached_doc,
        get_list,
        get_cached_value,
    ):
        get_cached_value.side_effect = lambda doctype, name, fieldname: {
            "custom_have_token": 1,
            "currency": "JMD",
        }.get(fieldname)
        get_cached_doc.return_value = SimpleNamespace(
            name="POS TEST", company="Test Company", currency="JMD"
        )
        get_list.return_value = [frappe._dict({"parent": "POS TEST"})]

        with patch.object(dialog.frappe, "session", SimpleNamespace(user="sa@example.com")):
            with patch.object(dialog.frappe, "conf", {}):
                data = opening.get_opening_dialog_data(erpnext_version=13)

        self.assertEqual(data["default_pos_profile"], "POS TEST")
        self.assertEqual(data["token_workflow_enabled"], 1)
        self.assertEqual(data["default_company"], "Test Company")
        self.assertEqual(data["user_role"], "cline-Sales Associate")
        self.assertEqual(data["payments_method"][0].currency, "JMD")
        self.assertEqual(get_list.call_args.kwargs["filters"], {"parent": ["in", ["POS TEST"]]})

    @patch.object(dialog.frappe, "get_cached_value")
    @patch.object(dialog.frappe, "get_list")
    @patch.object(dialog, "get_default_pos_profile_for_user", return_value="LEGACY POS")
    def test_opening_dialog_uses_production_style_data_when_token_workflow_off(
        self, _default_profile, get_list, get_cached_value
    ):
        get_cached_value.side_effect = lambda doctype, name, fieldname: {
            "custom_have_token": 0,
            "currency": "JMD",
        }.get(fieldname)
        get_list.side_effect = [
            [frappe._dict({"name": "Test Company"})],
            [frappe._dict({"name": "LEGACY POS", "company": "Test Company", "currency": "JMD"})],
            [frappe._dict({"parent": "LEGACY POS"})],
        ]

        with patch.object(dialog.frappe, "session", SimpleNamespace(user="cashier@example.com")):
            with patch.object(dialog.frappe, "conf", {}):
                data = opening.get_opening_dialog_data(erpnext_version=13)

        self.assertEqual(data["token_workflow_enabled"], 0)
        self.assertEqual(data["default_pos_profile"], "")
        self.assertEqual(data["user_role"], "")
        self.assertEqual(data["role_error"], "")
        self.assertEqual(data["pos_profiles_data"][0].name, "LEGACY POS")

    @patch.object(opening, "update_opening_shift_data")
    @patch.object(opening.frappe, "get_doc")
    @patch.object(opening.frappe, "get_cached_value", return_value="Test Company")
    @patch.object(opening, "require_operational_role_for_action")
    @patch.object(opening, "require_user_default_pos_profile", return_value="POS TEST")
    def test_create_opening_voucher_requires_cashier_when_relay_enabled(
        self,
        _require_default_profile,
        require_role,
        _get_cached_value,
        get_doc,
        _update_data,
    ):
        opening_doc = Mock()
        opening_doc.pos_profile = "POS TEST"
        opening_doc.as_dict.return_value = {"name": "OPEN-1"}
        get_doc.return_value = opening_doc

        with patch.object(opening.frappe, "session", SimpleNamespace(user="cashier@example.com")):
            data = opening.create_opening_voucher(
                "POS TEST",
                "Test Company",
                "[]",
                relay_workflow_enabled_fn=lambda _pos_profile: True,
            )

        require_role.assert_called_once_with(
            ("cline-Cashier", "cline-Supervisor"), "create POS opening shifts"
        )
        opening_doc.set.assert_called_once_with("balance_details", [])
        opening_doc.insert.assert_called_once_with(ignore_permissions=True)
        self.assertEqual(data["pos_opening_shift"], {"name": "OPEN-1"})

    @patch.object(opening, "update_opening_shift_data")
    @patch.object(opening.frappe, "get_doc")
    @patch.object(opening.frappe, "get_cached_value", return_value="Profile Company")
    @patch.object(opening, "require_operational_role_for_action")
    @patch.object(opening, "require_user_default_pos_profile")
    def test_create_opening_voucher_keeps_legacy_profile_selection_when_token_off(
        self,
        require_default_profile,
        require_role,
        _get_cached_value,
        get_doc,
        _update_data,
    ):
        opening_doc = Mock()
        opening_doc.pos_profile = "LEGACY POS"
        opening_doc.as_dict.return_value = {"name": "OPEN-LEGACY"}
        get_doc.return_value = opening_doc

        with patch.object(opening.frappe, "session", SimpleNamespace(user="cashier@example.com")):
            data = opening.create_opening_voucher(
                "LEGACY POS",
                "Selected Company",
                "[]",
                relay_workflow_enabled_fn=lambda _pos_profile: False,
            )

        require_default_profile.assert_not_called()
        require_role.assert_not_called()
        self.assertEqual(get_doc.call_args[0][0]["company"], "Selected Company")
        self.assertEqual(data["pos_opening_shift"], {"name": "OPEN-LEGACY"})

    @patch.object(opening, "bootstrap_non_cash_pos_session", return_value={"session_mode": "no_cash_role_session"})
    @patch.object(opening, "is_token_workflow_enabled", return_value=True)
    @patch.object(opening, "get_default_pos_profile_for_user", return_value="POS TEST")
    @patch.object(opening, "get_single_operational_role", return_value="cline-Sales Associate")
    @patch.object(opening.frappe.db, "get_all", return_value=[])
    def test_check_opening_shift_bootstraps_non_cash_role_session(
        self,
        _get_all,
        _role,
        _default_profile,
        _token_enabled,
        bootstrap_session,
    ):
        with patch.object(opening.frappe, "session", SimpleNamespace(user="sa@example.com")):
            data = opening.check_opening_shift("sa@example.com")

        bootstrap_session.assert_called_once_with("POS TEST", "cline-Sales Associate")
        self.assertEqual(data["session_mode"], "no_cash_role_session")

    @patch.object(opening, "bootstrap_non_cash_pos_session")
    @patch.object(opening, "is_token_workflow_enabled", return_value=False)
    @patch.object(opening, "get_default_pos_profile_for_user", return_value="LEGACY POS")
    @patch.object(opening, "get_single_operational_role", return_value="cline-Sales Associate")
    @patch.object(opening.frappe.db, "get_all", return_value=[])
    def test_check_opening_shift_does_not_bootstrap_non_cash_for_legacy_profile(
        self,
        _get_all,
        _role,
        _default_profile,
        _token_enabled,
        bootstrap_session,
    ):
        with patch.object(opening.frappe, "session", SimpleNamespace(user="sa@example.com")):
            data = opening.check_opening_shift("sa@example.com")

        bootstrap_session.assert_not_called()
        self.assertEqual(data, "")

    @patch.object(bootstrap, "get_single_operational_role", return_value="cline-Cashier")
    @patch.object(bootstrap.frappe, "get_doc")
    @patch.object(bootstrap, "require_user_default_pos_profile", return_value="POS TEST")
    def test_bootstrap_pos_session_blocks_cashier_virtual_session(
        self, _require_default_profile, get_doc, _role
    ):
        get_doc.return_value = SimpleNamespace(company="Test Company")

        with self.assertRaises(frappe.ValidationError):
            opening.bootstrap_pos_session("POS TEST", company="Test Company")
