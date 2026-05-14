# -*- coding: utf-8 -*-
# Copyright (c) 2020, Youssef Restom and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from posawesome.posawesome.doctype.pos_closing_shift.service import (
    get_payments_entries as _get_payments_entries,
    get_pos_invoices as _get_pos_invoices,
    make_closing_shift_from_opening as _make_closing_shift_from_opening,
    save_closing_shift_with_retry as _save_closing_shift_with_retry,
    submit_closing_shift as _submit_closing_shift,
    submit_printed_invoices,
)


class POSClosingShift(Document):
    def validate(self):
        user = frappe.get_all(
            "POS Closing Shift",
            filters={
                "user": self.user,
                "docstatus": 1,
                "pos_opening_shift": self.pos_opening_shift,
                "name": ["!=", self.name],
            },
        )

        if user:
            frappe.throw(
                _(
                    "POS Closing Shift {} against {} between selected period".format(
                        frappe.bold("already exists"), frappe.bold(self.user)
                    )
                ),
                title=_("Invalid Period"),
            )

        if (
            frappe.db.get_value("POS Opening Shift", self.pos_opening_shift, "status")
            != "Open"
        ):
            frappe.throw(
                _("Selected POS Opening Shift should be open."),
                title=_("Invalid Opening Entry"),
            )
        self.update_payment_reconciliation()

    def update_payment_reconciliation(self):
        # update the difference values in Payment Reconciliation child table
        # get default precision for site
        precision = (
            frappe.get_cached_value("System Settings", None, "currency_precision") or 3
        )
        for d in self.payment_reconciliation:
            d.difference = +flt(d.closing_amount, precision) - flt(
                d.expected_amount, precision
            )

    def on_submit(self):
        opening_entry = frappe.get_doc("POS Opening Shift", self.pos_opening_shift)
        opening_entry.pos_closing_shift = self.name
        opening_entry.set_status()
        self.delete_draft_invoices()
        opening_entry.save()

    def delete_draft_invoices(self):
        if frappe.get_value("POS Profile", self.pos_profile, "posa_allow_delete"):
            data = frappe.db.sql(
                """
                select
                    name
                from
                    `tabSales Invoice`
                where
                    docstatus = 0 and posa_is_printed = 0 and posa_pos_opening_shift = %s
                """,
                (self.pos_opening_shift),
                as_dict=1,
            )

            for invoice in data:
                frappe.delete_doc("Sales Invoice", invoice.name, force=1)

    @frappe.whitelist()
    def get_payment_reconciliation_details(self):
        currency = frappe.get_cached_value("Company", self.company, "default_currency")
        return frappe.render_template(
            "posawesome/posawesome/doctype/pos_closing_shift/closing_shift_details.html",
            {"data": self, "currency": currency},
        )


@frappe.whitelist()
def get_cashiers(doctype, txt, searchfield, start, page_len, filters):
    cashiers_list = frappe.get_all("POS Profile User", filters=filters, fields=["user"])
    return [c["user"] for c in cashiers_list]


@frappe.whitelist()
def get_pos_invoices(pos_opening_shift):
    return _get_pos_invoices(pos_opening_shift)


@frappe.whitelist()
def get_payments_entries(pos_opening_shift):
    return _get_payments_entries(pos_opening_shift)


@frappe.whitelist()
def make_closing_shift_from_opening(opening_shift):
    return _make_closing_shift_from_opening(opening_shift)


@frappe.whitelist()
def submit_closing_shift(closing_shift):
    return _submit_closing_shift(closing_shift)


def _save_closing_shift_with_retry(closing_shift_payload, attempts=3):
    return _save_closing_shift_with_retry(closing_shift_payload, attempts)
