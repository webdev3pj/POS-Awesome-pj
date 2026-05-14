# -*- coding: utf-8 -*-

from __future__ import unicode_literals



from urllib.parse import urlparse



import frappe

from frappe.utils import cint, cstr



def _get_edge_relay_base_url():
    relay_base_url = cstr(
        frappe.conf.get("posa_edge_relay_url")
        or frappe.conf.get("edge_relay_base_url")
        or ""
    ).strip()
    return relay_base_url.rstrip("/")

def _get_pos_profile_edge_relay_url(pos_profile):
    if not pos_profile:
        return ""
    relay_url = cstr(
        frappe.get_cached_value("POS Profile", pos_profile, "custom_edge_relay_url") or ""
    ).strip()
    return relay_url.rstrip("/")

def _get_pos_profile_field_if_exists(pos_profile, fieldname, default=None):
    if not pos_profile or not fieldname:
        return default

    try:
        meta = frappe.get_meta("POS Profile")
        if not meta or not meta.has_field(fieldname):
            return default
        return frappe.get_cached_value("POS Profile", pos_profile, fieldname)
    except Exception:
        return default

def _get_pos_profile_relay_connectivity_mode(pos_profile):
    mode = cstr(
        _get_pos_profile_field_if_exists(
            pos_profile, "posa_edge_relay_connectivity_mode", "cloud_checked"
        )
        or "cloud_checked"
    ).strip()
    if mode not in ("cloud_checked", "lan_only_browser_checked"):
        mode = "cloud_checked"
    return mode

def _get_pos_profile_allow_cloud_fallback_when_relay_down(pos_profile):
    return cint(
        _get_pos_profile_field_if_exists(
            pos_profile, "posa_allow_cloud_fallback_when_relay_down", 0
        )
        or 0
    ) == 1

def _is_private_lan_host(hostname):
    host = cstr(hostname or "").strip().lower()
    if not host:
        return False

    if host in ("localhost", "127.0.0.1"):
        return True

    return (
        host.startswith("10.")
        or host.startswith("192.168.")
        or host.startswith("172.16.")
        or host.startswith("172.17.")
        or host.startswith("172.18.")
        or host.startswith("172.19.")
        or host.startswith("172.2")
        or host.startswith("172.30.")
        or host.startswith("172.31.")
    )
