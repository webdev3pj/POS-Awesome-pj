# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe


PAGE_NAME = "posapp"
ROLE_NAME = "cline-Sales Associate"


def execute():
    if not frappe.db.exists("Page", PAGE_NAME):
        return
    if not frappe.db.exists("Role", ROLE_NAME):
        return

    page = frappe.get_doc("Page", PAGE_NAME)
    existing_roles = {
        str((row or {}).get("role") or "").strip()
        for row in (page.get("roles") or [])
        if row
    }
    if ROLE_NAME in existing_roles:
        return

    page.append("roles", {"role": ROLE_NAME})
    page.save(ignore_permissions=True)
    frappe.clear_cache()
