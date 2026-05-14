import frappe
from frappe.utils import cint, cstr, getdate, nowdate


def age_days_from_date(raw_date):
    try:
        date_value = getdate(raw_date)
        return max(0, (getdate(nowdate()) - date_value).days)
    except Exception:
        return 0


def resolve_pos_profile_for_lookup(pos_profile, company):
    pos_profile = cstr(pos_profile or "").strip()
    if pos_profile:
        return pos_profile

    active_shift = frappe.db.get_all(
        "POS Opening Shift",
        filters={
            "user": frappe.session.user,
            "pos_closing_shift": ["in", ["", None]],
            "docstatus": 1,
            "status": "Open",
            "company": company,
        },
        fields=["pos_profile"],
        order_by="period_start_date desc",
        limit_page_length=1,
    )
    if active_shift:
        return cstr(active_shift[0].get("pos_profile") or "").strip()
    return ""


def profile_so_policy(pos_profile):
    max_age_days = 1
    allow_stale = 0
    history_days = 30
    naming_series = ""
    if pos_profile:
        max_age_days = max(
            0,
            cint(
                frappe.get_cached_value(
                    "POS Profile", pos_profile, "posa_sales_order_lookup_max_age_days"
                )
                or 1
            ),
        )
        allow_stale = 1 if cint(
            frappe.get_cached_value(
                "POS Profile", pos_profile, "posa_allow_stale_sales_order_fetch"
            )
            or 0
        ) else 0
        history_days = max(
            max_age_days,
            cint(
                frappe.get_cached_value(
                    "POS Profile", pos_profile, "posa_stale_sales_order_history_days"
                )
                or 30
            ),
        )
        naming_series = cstr(
            frappe.get_cached_value(
                "POS Profile", pos_profile, "posa_sales_order_naming_series"
            )
            or ""
        ).strip()
    return {
        "max_age_days": max_age_days,
        "allow_stale": allow_stale,
        "history_days": history_days,
        "naming_series": naming_series,
    }


def resolve_allow_stale(arg_allow_stale, default_allow_stale):
    if arg_allow_stale in (None, ""):
        return 1 if cint(default_allow_stale) else 0
    return 1 if cint(arg_allow_stale) else 0


def doctype_has_column(doctype, fieldname):
    return frappe.get_meta(doctype).has_field(fieldname) and frappe.db.has_column(
        doctype, fieldname
    )
