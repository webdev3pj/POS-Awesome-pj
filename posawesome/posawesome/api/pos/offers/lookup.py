# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.utils import nowdate


def get_pos_offers(profile):
    pos_profile = frappe.get_doc("POS Profile", profile)
    values = {
        "company": pos_profile.company,
        "pos_profile": profile,
        "warehouse": pos_profile.warehouse,
        "valid_from": nowdate(),
        "valid_upto": nowdate(),
    }
    return frappe.db.sql(
        """
        SELECT *
        FROM `tabPOS Offer`
        WHERE
        disable = 0 AND
        company = %(company)s AND
        (pos_profile is NULL OR pos_profile  = '' OR  pos_profile = %(pos_profile)s) AND
        (warehouse is NULL OR warehouse  = '' OR  warehouse = %(warehouse)s) AND
        (valid_from is NULL OR valid_from  = '' OR  valid_from <= %(valid_from)s) AND
        (valid_upto is NULL OR valid_from  = '' OR  valid_upto >= %(valid_upto)s)
    """,
        values=values,
        as_dict=1,
    )
