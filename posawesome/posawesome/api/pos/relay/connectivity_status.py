# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import requests
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import cint, cstr, now_datetime

from posawesome.posawesome.api.pos.relay.connectivity_config import (
    _get_edge_relay_base_url,
    _get_pos_profile_allow_cloud_fallback_when_relay_down,
    _get_pos_profile_edge_relay_url,
    _get_pos_profile_relay_connectivity_mode,
    _is_private_lan_host,
)
from posawesome.posawesome.api.pos.relay.state import _is_relay_workflow_enabled

def get_relay_connectivity_status(pos_profile):
    pos_profile = cstr(pos_profile or "").strip()
    if not pos_profile:
        frappe.throw(_("POS Profile is required"))

    connectivity_mode = _get_pos_profile_relay_connectivity_mode(pos_profile)
    allow_cloud_fallback_when_relay_down = (
        _get_pos_profile_allow_cloud_fallback_when_relay_down(pos_profile)
    )

    def attach_policy(payload):
        result = dict(payload or {})
        result["connectivity_mode"] = connectivity_mode
        result["allow_cloud_fallback_when_relay_down"] = bool(
            allow_cloud_fallback_when_relay_down
        )
        result["submit_gate_source"] = (
            "browser_lan"
            if connectivity_mode == "lan_only_browser_checked"
            else "cloud_backend"
        )
        result["cloud_connected"] = bool(result.get("connected"))
        result["cloud_status"] = cstr(result.get("status") or "")
        result["cloud_message"] = cstr(result.get("message") or "")
        result["cloud_http_status"] = result.get("http_status")
        result["cloud_checked_at"] = cstr(result.get("checked_at") or "")
        debug = result.get("debug") or {}
        if isinstance(debug, dict):
            debug = dict(debug)
            debug["connectivity_mode"] = connectivity_mode
            if connectivity_mode == "lan_only_browser_checked":
                debug["mode_note"] = _(
                    "LAN-only mode expects the POS browser to check relay /health over LAN HTTPS; cloud-side relay reachability remains diagnostic only."
                )
            result["debug"] = debug
        return result

    if not _is_relay_workflow_enabled(pos_profile):
        return attach_policy({
            "enabled": False,
            "configured": False,
            "connected": False,
            "status": "disabled",
            "message": _("Relay workflow is disabled for this POS Profile."),
            "checked_at": str(now_datetime()),
        })

    profile_relay_url = _get_pos_profile_edge_relay_url(pos_profile)
    site_relay_url = _get_edge_relay_base_url()
    relay_base_url = profile_relay_url or site_relay_url

    if not relay_base_url:
        return attach_policy({
            "enabled": True,
            "configured": False,
            "connected": False,
            "status": "not_configured",
            "relay_url": "",
            "relay_source": "none",
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _(
                "Edge Relay URL is not configured on this POS Profile. Set Edge Relay URL on POS Profile or fallback key 'posa_edge_relay_url' in site_config.json."
            ),
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": "",
                "hint": _(
                    "Open POS Profile and set 'Edge Relay URL', for example http://192.168.50.10:8787"
                ),
            },
        })

    timeout_seconds = max(1, cint(frappe.conf.get("posa_edge_relay_timeout") or 3))
    health_url = "{0}/health".format(relay_base_url)
    relay_source = "pos_profile" if profile_relay_url else "site_config"
    parsed_url = urlparse(relay_base_url)
    relay_host = parsed_url.hostname or ""
    is_private_lan = _is_private_lan_host(relay_host)

    try:
        response = requests.get(health_url, timeout=timeout_seconds)
        response.raise_for_status()

        health_payload = {}
        try:
            health_payload = response.json() or {}
        except Exception:
            health_payload = {}

        relay_ok = bool(health_payload.get("ok")) if isinstance(health_payload, dict) else True
        return attach_policy({
            "enabled": True,
            "configured": True,
            "connected": relay_ok,
            "status": "online" if relay_ok else "offline",
            "relay_url": relay_base_url,
            "relay_source": relay_source,
            "relay_host": relay_host,
            "relay_host_type": "private_lan" if is_private_lan else "public_or_routable",
            "relay_config_identified": True,
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _("Edge Relay reachable.")
            if relay_ok
            else _("Edge Relay responded, but reported unhealthy status."),
            "http_status": response.status_code,
            "queue": health_payload.get("queue", {}) if isinstance(health_payload, dict) else {},
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": health_url,
                "timeout_seconds": timeout_seconds,
                "cloud_reachability_note": _(
                    "Frappe Cloud checks reachability from cloud network, not from your local browser."
                ),
            },
        })
    except requests.exceptions.Timeout:
        return attach_policy({
            "enabled": True,
            "configured": True,
            "connected": False,
            "status": "timeout",
            "relay_url": relay_base_url,
            "relay_source": relay_source,
            "relay_host": relay_host,
            "relay_host_type": "private_lan" if is_private_lan else "public_or_routable",
            "relay_config_identified": True,
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _(
                "Timed out while connecting to Edge Relay. Check network route/firewall and relay service status."
            ),
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": health_url,
                "timeout_seconds": timeout_seconds,
                "hint": _("Try opening the relay URL from the ERP server network."),
                "cloud_reachability_note": _(
                    "If this is a LAN IP like 192.168.x.x, Frappe Cloud cannot reach it without VPN/tunnel/public routing."
                ),
            },
        })
    except requests.exceptions.ConnectionError:
        return attach_policy({
            "enabled": True,
            "configured": True,
            "connected": False,
            "status": "connection_error",
            "relay_url": relay_base_url,
            "relay_source": relay_source,
            "relay_host": relay_host,
            "relay_host_type": "private_lan" if is_private_lan else "public_or_routable",
            "relay_config_identified": True,
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _(
                "Connection to Edge Relay failed. Verify host/IP, port, and whether relay app is running."
            ),
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": health_url,
                "hint": _("Ensure relay machine allows inbound traffic on relay port."),
                "cloud_reachability_note": _(
                    "Configured relay is identified, but cloud reachability still requires network path from Frappe Cloud."
                ),
            },
        })
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if getattr(exc, "response", None) else None
        return attach_policy({
            "enabled": True,
            "configured": True,
            "connected": False,
            "status": "http_error",
            "relay_url": relay_base_url,
            "relay_source": relay_source,
            "relay_host": relay_host,
            "relay_host_type": "private_lan" if is_private_lan else "public_or_routable",
            "relay_config_identified": True,
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _("Edge Relay returned HTTP error status."),
            "http_status": status_code,
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": health_url,
                "hint": _("Check relay app logs and health endpoint response."),
                "cloud_reachability_note": _(
                    "Configured relay is identified; HTTP error means target responded but health endpoint returned non-2xx."
                ),
            },
        })
    except Exception:
        return attach_policy({
            "enabled": True,
            "configured": True,
            "connected": False,
            "status": "offline",
            "relay_url": relay_base_url,
            "relay_source": relay_source,
            "relay_host": relay_host,
            "relay_host_type": "private_lan" if is_private_lan else "public_or_routable",
            "relay_config_identified": True,
            "profile_relay_url": profile_relay_url,
            "site_relay_url": site_relay_url,
            "message": _("Edge Relay is unreachable from this server."),
            "checked_at": str(now_datetime()),
            "debug": {
                "pos_profile": pos_profile,
                "relay_health_url": health_url,
                "cloud_reachability_note": _(
                    "Configured relay is identified, but no working route from Frappe Cloud to relay host."
                ),
            },
        })
