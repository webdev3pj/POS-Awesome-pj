# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

__version__ = "6.3.0"
# commission/__init__.py
from erpnext.controllers import selling_controller
from posawesome.overrides.selling_commission import custom_calculate_commission

# Replace ERPNext’s function with yours
selling_controller.SellingController.calculate_commission = custom_calculate_commission


def console(*data):
    frappe.publish_realtime("toconsole", data, user=frappe.session.user)
