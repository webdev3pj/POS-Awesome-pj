import time
import requests
from json import dumps

from .storage import (
    get_next_queued_outbox_event,
    get_next_queued_event,
    get_latest_local_sale,
    mark_outbox_done,
    mark_outbox_failed,
    mark_outbox_processing,
    load_config,
    mark_done,
    mark_failed,
    mark_processing,
    outbox_counts,
    set_local_quote_cloud_synced,
    set_local_sale_cloud_synced,
    set_local_sale_sync_error,
)


EVENT_ENDPOINTS = {
    "token_create": "api/method/posawesome.posawesome.api.posapp.get_relay_workflow_state",
    "pick_update": "api/method/posawesome.posawesome.api.posapp.update_relay_picking_status",
    "dispatch_release": "api/method/posawesome.posawesome.api.posapp.release_relay_dispatch",
    "invoice_submit": "api/method/posawesome.posawesome.api.posapp.submit_invoice",
}


OUTBOX_ENDPOINTS = {
    "SALE_COMMITTED": "api/method/posawesome.posawesome.api.posapp.submit_invoice",
    "CUSTOMER_UPSERT": "api/resource/Customer",
    "PICK_EVENT": "api/method/posawesome.posawesome.api.posapp.update_relay_picking_status",
    "RELEASE_EVENT": "api/method/posawesome.posawesome.api.posapp.release_relay_dispatch",
    "QUOTE_UPSERT": "api/method/posawesome.posawesome.api.posapp.create_quotation_token",
    # Phase-1 local-first tracking events - keep as no-op cloud ack to avoid blocking queue
    "TOKEN_CREATED": None,
    "SESSION_OPEN": None,
    "SESSION_CLOSE": None,
}


def _build_headers(config):
    api_key = (config.get("api_key") or "").strip()
    api_secret = (config.get("api_secret") or "").strip()
    headers = {}
    if api_key and api_secret:
        headers["Authorization"] = f"token {api_key}:{api_secret}"
    return headers


RELAY_TO_CLOUD_PICK_STATUS = {
    "PAID_PENDING_PICK": "Not Started",
    "PICK_IN_PROGRESS": "In Progress",
    "PICK_EXCEPTION": "Exception",
    "PICKED_READY_FOR_RELEASE": "Picked",
}


def _normalize_cloud_pick_status(value):
    status = (value or "").strip()
    if not status:
        return ""
    return RELAY_TO_CLOUD_PICK_STATUS.get(status, status)


def _enrich_fulfillment_payload(payload, local_ref=None):
    enriched = dict(payload or {})
    sales_invoice = (enriched.get("sales_invoice") or enriched.get("cloud_invoice_name") or "").strip()
    pos_profile = (enriched.get("pos_profile") or enriched.get("pos_profile_id") or "").strip()
    if not sales_invoice and local_ref:
        local_sale = get_latest_local_sale(local_ref)
        if local_sale:
            sales_invoice = (local_sale.get("cloud_invoice_name") or "").strip()
            pos_profile = pos_profile or (local_sale.get("pos_profile_id") or "").strip()
            if sales_invoice:
                enriched["cloud_invoice_name"] = sales_invoice
                # Some cloud handlers still expect this key specifically.
                enriched["sales_invoice"] = sales_invoice
            if pos_profile:
                enriched["pos_profile_id"] = pos_profile
                enriched["pos_profile"] = pos_profile
    return enriched


def _build_request_payload(event_type, payload):
    if event_type == "invoice_submit":
        # submit_invoice expects serialized JSON strings for invoice and data
        return {
            "invoice": dumps(payload.get("invoice") or {}, ensure_ascii=False),
            "data": dumps(payload.get("data") or {}, ensure_ascii=False),
        }

    if event_type == "SALE_COMMITTED":
        return {
            "invoice": dumps(payload.get("invoice") or {}, ensure_ascii=False),
            "data": dumps(payload.get("data") or {}, ensure_ascii=False),
        }

    if event_type == "PICK_EVENT":
        cloud_pick_status = _normalize_cloud_pick_status(
            payload.get("picking_status") or payload.get("pick_status")
        )
        return {
            "sales_invoice": payload.get("sales_invoice") or payload.get("cloud_invoice_name"),
            "pos_profile": payload.get("pos_profile") or payload.get("pos_profile_id") or "",
            "picking_status": cloud_pick_status or "In Progress",
            "exceptions_note": payload.get("notes") or payload.get("exceptions_note") or "",
        }

    if event_type == "RELEASE_EVENT":
        return {
            "sales_invoice": payload.get("sales_invoice") or payload.get("cloud_invoice_name"),
            "pos_profile": payload.get("pos_profile") or payload.get("pos_profile_id") or "",
            "allow_exception_release": 1 if payload.get("allow_partial") else 0,
            "dispatch_proof": payload.get("dispatch_proof") or {
                "ack_name": payload.get("proof_ack_name") or "",
                "proof_mode": payload.get("proof_mode") or "",
                "proof_ref_no": payload.get("proof_ref_no") or "",
                "proof_notes": payload.get("proof_notes") or "",
            },
            "dispatch_line_snapshot": payload.get("line_snapshot") or [],
        }

    if event_type == "CUSTOMER_UPSERT":
        return {
            "customer_name": payload.get("customer_name") or payload.get("customer_id") or "",
            "mobile_no": payload.get("mobile_no") or "",
            "email_id": payload.get("email_id") or "",
            "tax_id": payload.get("tax_id") or "",
        }

    if event_type == "QUOTE_UPSERT":
        quote_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
        quote_payload = dict(quote_payload or {})
        if payload.get("quote_id") and not quote_payload.get("quote_id"):
            quote_payload["quote_id"] = payload.get("quote_id")
        return {
            "data": dumps(quote_payload, ensure_ascii=False),
        }

    return payload


def _build_outbox_request(outbox_event):
    event_type = outbox_event.get("event_type")
    payload = outbox_event.get("payload") or {}
    local_ref = outbox_event.get("local_ref")
    endpoint = OUTBOX_ENDPOINTS.get(event_type)
    if endpoint is None:
        # No-op event type intentionally acknowledged as done
        return {
            "skip_cloud": True,
            "endpoint": None,
            "payload": payload,
            "method": "noop",
        }

    if event_type in ("PICK_EVENT", "RELEASE_EVENT"):
        payload = _enrich_fulfillment_payload(payload, local_ref=local_ref)
        if not (payload.get("sales_invoice") or payload.get("cloud_invoice_name")):
            raise RuntimeError(
                f"{event_type} waiting for cloud Sales Invoice for local sale {local_ref or '(missing local_ref)'}"
            )

    request_payload = _build_request_payload(event_type, payload)
    if event_type in ("SALE_COMMITTED", "PICK_EVENT", "RELEASE_EVENT", "QUOTE_UPSERT"):
        return {
            "skip_cloud": False,
            "endpoint": endpoint,
            "payload": request_payload,
            "method": "data",
        }

    if event_type == "CUSTOMER_UPSERT":
        return {
            "skip_cloud": False,
            "endpoint": endpoint,
            "payload": request_payload,
            "method": "json",
        }

    return {
        "skip_cloud": False,
        "endpoint": endpoint,
        "payload": request_payload,
        "method": "json",
    }


def _post_with_method(url, payload, method, config, extra_headers=None):
    headers = _build_headers(config)
    if extra_headers:
        headers.update(extra_headers)

    if method == "data":
        return requests.post(url, data=payload, headers=headers, timeout=15)
    return requests.post(url, json=payload, headers=headers, timeout=15)


def sync_outbox_once():
    event = get_next_queued_outbox_event()
    if not event:
        return {"ok": True, "message": "no queued outbox events"}

    config = load_config()
    base_url = (config.get("frappe_base_url") or "").rstrip("/")
    if not base_url:
        mark_outbox_failed(event["event_id"], "frappe_base_url not configured", retry_later=True)
        return {
            "ok": False,
            "message": "frappe_base_url not configured",
            "event_id": event["event_id"],
        }

    mark_outbox_processing(event["event_id"])
    event_type = event.get("event_type")
    local_ref = event.get("local_ref")

    try:
        request_spec = _build_outbox_request(event)
        if request_spec.get("skip_cloud"):
            mark_outbox_done(event["event_id"])
            return {
                "ok": True,
                "event_id": event["event_id"],
                "status": "noop_done",
            }

        endpoint = request_spec.get("endpoint")
        payload = request_spec.get("payload")
        method = request_spec.get("method")

        if not endpoint:
            mark_outbox_done(event["event_id"])
            return {
                "ok": True,
                "event_id": event["event_id"],
                "status": "no_endpoint_done",
            }

        url = f"{base_url}/{endpoint}"

        idempotency_key = event.get("idempotency_key") or event.get("event_id")
        response = _post_with_method(
            url,
            payload,
            method,
            config,
            extra_headers={"X-Relay-Event-ID": event.get("event_id"), "X-Relay-Idempotency-Key": idempotency_key},
        )
        response.raise_for_status()

        cloud_ref = None
        response_json = {}
        try:
            response_json = response.json() or {}
        except Exception:
            response_json = {}

        if isinstance(response_json, dict):
            message = response_json.get("message")
            if isinstance(message, dict):
                cloud_ref = (
                    message.get("name")
                    or message.get("sales_invoice")
                    or message.get("quote_name")
                )

        if event_type == "SALE_COMMITTED" and local_ref:
            set_local_sale_cloud_synced(local_ref, cloud_invoice_name=cloud_ref)
        if event_type == "QUOTE_UPSERT" and local_ref:
            set_local_quote_cloud_synced(local_ref, cloud_quote_name=cloud_ref)

        mark_outbox_done(event["event_id"], cloud_ref=cloud_ref)
        return {
            "ok": True,
            "event_id": event["event_id"],
            "status_code": response.status_code,
            "cloud_ref": cloud_ref,
        }
    except Exception as exc:
        if event_type == "SALE_COMMITTED" and local_ref:
            set_local_sale_sync_error(local_ref, str(exc))
        mark_outbox_failed(event["event_id"], str(exc), retry_later=True)
        return {
            "ok": False,
            "event_id": event["event_id"],
            "message": str(exc),
        }


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
        sync_outbox_once()
        outbox_counts()
        time.sleep(max(1, int(sleep_seconds)))

