# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import frappe



def get_sales_person_names():
    sales_persons = frappe.get_list(
        "Sales Person",
        filters={"enabled": 1},
        fields=["name", "sales_person_name"],
        limit_page_length=100000,
    )
    return sales_persons

def get_sales_partner_names():
    sales_partners = frappe.get_list(
        "Sales Partner",
        fields=["name", "partner_name"],
        limit_page_length=100000,
    )
    return sales_partners
