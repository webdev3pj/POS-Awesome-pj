import requests

from .storage import (
    enqueue_outbox_event,
    refresh_items_cache,
)


def refresh_items_from_cloud(config, pos_profile_payload=None, limit=200):
    """
    Best-effort refresh for offline item search cache.
    Uses existing POSAwesome get_items method and stores compact cache locally.
    """
    base_url = (config.get("frappe_base_url") or "").rstrip("/")
    api_key = (config.get("api_key") or "").strip()
    api_secret = (config.get("api_secret") or "").strip()
    if not base_url or not api_key or not api_secret:
        return {"ok": False, "message": "cloud credentials not configured"}

    headers = {"Authorization": f"token {api_key}:{api_secret}"}
    payload = {
        "pos_profile": pos_profile_payload or {},
        "price_list": None,
        "item_group": "",
        "search_value": "",
        "customer": None,
    }

    url = f"{base_url}/api/method/posawesome.posawesome.api.posapp.get_items"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json() or {}
        rows = data.get("message") or []
        if limit and len(rows) > int(limit):
            rows = rows[: int(limit)]
        result = refresh_items_cache(rows)
        return {"ok": True, "count": result.get("count", 0)}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


def queue_customer_upsert(payload):
    """Compatibility helper for explicit queueing from non-HTTP paths."""
    customer_id = (payload or {}).get("customer_id") or (payload or {}).get("name")
    return enqueue_outbox_event(
        "CUSTOMER_UPSERT",
        payload or {},
        local_ref=customer_id,
    )

