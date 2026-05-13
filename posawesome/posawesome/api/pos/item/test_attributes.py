# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from posawesome.posawesome.api.pos.item import attributes


class TestItemAttributes(FrappeTestCase):
    @patch.object(attributes, "build_item_cache")
    @patch.object(attributes.frappe, "cache")
    def test_get_item_optional_attributes_builds_missing_cache(self, cache, build_cache):
        cache_obj = Mock()
        cache_obj.hget.side_effect = [None, {"Size"}]
        cache.return_value = cache_obj

        self.assertEqual(attributes.get_item_optional_attributes("ITEM-TEMPLATE"), {"Size"})
        build_cache.assert_called_once_with("ITEM-TEMPLATE")

    @patch.object(attributes, "get_item_optional_attributes", return_value={"Size"})
    @patch.object(attributes.frappe.db, "get_all")
    def test_get_item_attributes_marks_optional_attributes(self, get_all, _optional):
        get_all.side_effect = [
            [frappe._dict({"attribute": "Size"}), frappe._dict({"attribute": "Color"})],
            [frappe._dict({"attribute_value": "Small", "abbr": "S"})],
            [frappe._dict({"attribute_value": "Red", "abbr": "R"})],
        ]

        rows = attributes.get_item_attributes("ITEM-TEMPLATE")

        self.assertTrue(rows[0].optional)
        self.assertIsNone(rows[1].get("optional"))
        self.assertEqual(rows[0].get("values")[0].attribute_value, "Small")

    @patch.object(attributes.frappe, "cache")
    @patch.object(attributes.frappe.db, "get_all")
    def test_build_item_cache_ignores_disabled_variants(self, get_all, cache):
        get_all.side_effect = [
            [frappe._dict({"attribute": "Size"}), frappe._dict({"attribute": "Color"})],
            [
                ["ITEM-S", "Size", "Small"],
                ["ITEM-S", "Color", "Red"],
                ["ITEM-NO-COLOR", "Size", "Medium"],
                ["ITEM-DISABLED", "Size", "Large"],
            ],
            [frappe._dict({"name": "ITEM-DISABLED"})],
        ]
        cache_obj = Mock()
        cache.return_value = cache_obj

        attributes.build_item_cache("ITEM-TEMPLATE")

        optional_call = cache_obj.hset.call_args_list[-1]
        self.assertEqual(optional_call[0][0], "optional_attributes")
        self.assertEqual(optional_call[0][2], {"Color"})
