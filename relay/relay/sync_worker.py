import time
import requests
from json import dumps

from .storage import (
    get_next_queued_event,
    load_config,
    mark_done,
    mark_failed,
    mark_processing,
)


EVENT_ENDPOINTS = {
    "token_create": "api/method/posawesome.posawesome.api.posapp.get_relay_workflow_state",
    "pick_update": "api/method/posawesome.posawesome.api.posapp.update_relay_picking_status",
    "dispatch_release": "api/method/posawesome.posawesome.api.posapp.release_relay_dispatch",
    "invoice_submit": "api/method/posawesome.posawesome.api.posapp.submit_invoice",
}


def _build_headers(config):
    api_key = (config.get("api_key") or "").strip()
    api_secret = (config.get("api_secret") or "").strip()
    headers = {}
    if api_key and api_secret:
        headers["Authorization"] = f"token {api_key}:{api_secret}"
    return headers


def _build_request_payload(event_type, payload):
    if event_type == "invoice_submit":
        # submit_invoice expects serialized JSON strings for invoice and data
        return {
            "invoice": dumps(payload.get("invoice") or {}, ensure_ascii=False),
            "data": dumps(payload.get("data") or {}, ensure_ascii=False),
        }
    return payload


def sync_once():
    event = get_next_queued_event()
    if not event:
        return {"ok": True, "message": "no queued events"}

    config = load_config()
    base_url = (config.get("frappe_base_url") or "").rstrip("/")
    if not base_url:
        return {
            "ok": False,
            "message": "frappe_base_url not configured",
            "event_id": event["id"],
        }

    endpoint = EVENT_ENDPOINTS.get(event.get("event_type"))
    if not endpoint:
        mark_failed(event["id"], f"Unknown event_type: {event.get('event_type')}")
        return {
            "ok": False,
            "message": "unknown event type",
            "event_id": event["id"],
        }

    url = f"{base_url}/{endpoint}"
    mark_processing(event["id"])

    try:
        payload = _build_request_payload(
            event.get("event_type"), event.get("payload") or {}
        )

        if event.get("event_type") == "invoice_submit":
            response = requests.post(
                url,
                data=payload,
                headers=_build_headers(config),
                timeout=15,
            )
        else:
            response = requests.post(
                url,
                json=payload,
                headers=_build_headers(config),
                timeout=15,
            )
        response.raise_for_status()
        mark_done(event["id"])
        return {
            "ok": True,
            "event_id": event["id"],
            "status_code": response.status_code,
        }
    except Exception as exc:
        mark_failed(event["id"], str(exc))
        return {
            "ok": False,
            "event_id": event["id"],
            "message": str(exc),
        }


def run_sync_loop(sleep_seconds=5):
    while True:
        sync_once()
        time.sleep(max(1, int(sleep_seconds)))

