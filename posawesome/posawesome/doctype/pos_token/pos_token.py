# -*- coding: utf-8 -*-
# Copyright (c) 2025, POS Awesome and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, cint


class POSToken(Document):
    def before_insert(self):
        self.generate_token_number()
        self.calculate_totals()
        self.token_datetime = now_datetime()
        self.set_sales_associate_name()

    def validate(self):
        self.calculate_totals()

    def set_sales_associate_name(self):
        """Set the full name of the sales associate"""
        if self.sales_associate:
            self.sales_associate_name = frappe.db.get_value(
                "User", self.sales_associate, "full_name"
            ) or self.sales_associate

    def generate_token_number(self):
        """Generate a unique token number for easy scanning"""
        # Get the count of tokens created today for this POS profile
        today = frappe.utils.today()
        count = frappe.db.count(
            "POS Token",
            filters={
                "pos_profile": self.pos_profile,
                "creation": [">=", today]
            }
        ) + 1
        
        # Create a simple token format: PROFILE_ABBREVIATION-YYYYMMDD-SEQUENCE
        profile_abbr = "".join([word[0].upper() for word in self.pos_profile.split()[:2]])
        date_str = frappe.utils.today().replace("-", "")
        self.token_number = f"{profile_abbr}-{date_str}-{count:04d}"

    def calculate_totals(self):
        """Calculate total quantity and amount"""
        self.total_qty = sum(item.qty or 0 for item in self.items)
        self.total_amount = sum(item.amount or 0 for item in self.items)

    def mark_as_paid(self, invoice_name, cashier=None):
        """Mark token as paid and link to invoice"""
        self.status = "Paid"
        self.linked_invoice = invoice_name
        self.paid_datetime = now_datetime()
        if cashier:
            self.cashier = cashier
        self.save(ignore_permissions=True)

    def cancel_token(self):
        """Cancel the token"""
        if self.status == "Paid":
            frappe.throw("Cannot cancel a paid token")
        self.status = "Cancelled"
        self.save(ignore_permissions=True)
