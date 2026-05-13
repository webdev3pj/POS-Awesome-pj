# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cstr


def get_default_pos_profile_for_user(user):
    user = cstr(user or "").strip()
    if not user:
        return ""

    rows = frappe.db.sql(
        """
        select pf.name
        from `tabPOS Profile` pf
        inner join `tabPOS Profile User` pfu on pfu.parent = pf.name
        where pfu.user = %s
            and pfu.default = 1
            and pf.disabled = 0
        order by pf.modified desc
        limit 1
        """,
        (user,),
        as_dict=True,
    )
    if rows:
        return cstr(rows[0].name or "").strip()

    rows = frappe.db.sql(
        """
        select pf.name
        from `tabPOS Profile` pf
        inner join `tabPOS Profile User` pfu on pfu.parent = pf.name
        where pfu.user = %s
            and pf.disabled = 0
        order by pf.modified desc
        limit 1
        """,
        (user,),
        as_dict=True,
    )
    if rows:
        return cstr(rows[0].name or "").strip()
    return ""


def require_user_default_pos_profile(pos_profile):
    pos_profile = cstr(pos_profile or "").strip()
    default_pos_profile = get_default_pos_profile_for_user(frappe.session.user)
    if not default_pos_profile:
        frappe.throw(_("No default POS Profile is assigned to this user."))
    if pos_profile != default_pos_profile:
        frappe.throw(
            _("You can only use your default POS Profile {0}.").format(default_pos_profile)
        )
    return default_pos_profile

