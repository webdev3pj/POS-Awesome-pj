# -*- coding: utf-8 -*-
# Copyright (c) 2025, POS Awesome and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class POSTokenItem(Document):
    def validate(self):
        self.amount = (self.qty or 0) * (self.rate or 0)
