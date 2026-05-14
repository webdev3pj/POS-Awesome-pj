import copy
import json

import frappe
from frappe.utils import cstr


def as_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    return {}


def normalize_doc_payload(payload, doctype):
    if not isinstance(payload, dict) or not doctype:
        return payload

    meta = frappe.get_meta(doctype)
    normalized = copy.deepcopy(payload)
    normalized["doctype"] = doctype

    for fieldname, value in list(normalized.items()):
        df = meta.get_field(fieldname)
        if not df:
            continue

        if df.fieldtype == "Table":
            if isinstance(value, list) and df.options:
                normalized[fieldname] = [
                    normalize_doc_payload(row, df.options)
                    if isinstance(row, dict)
                    else row
                    for row in value
                ]
            continue

        if isinstance(value, (list, dict)):
            normalized[fieldname] = json.dumps(value)

    return normalized


def resolve_local_sale_ref(local_ref, invoice_payload, data_payload):
    return _first_value(
        local_ref,
        data_payload.get("local_sale_ref"),
        data_payload.get("local_ref"),
        invoice_payload.get("local_sale_ref"),
        invoice_payload.get("local_ref"),
    )


def resolve_local_token_id(local_token_id, token_payload):
    return _first_value(
        local_token_id,
        token_payload.get("local_token_id"),
        token_payload.get("token_id"),
        token_payload.get("sales_order"),
    )


def invoice_response(invoice_doc, local_sale_ref):
    return {
        "name": invoice_doc.name,
        "status": invoice_doc.docstatus,
        "local_sale_ref": local_sale_ref,
        "sales_invoice": invoice_doc.name,
    }


def sales_order_response(sales_order_doc, local_token_id):
    return {
        "name": sales_order_doc.name,
        "sales_order_name": sales_order_doc.name,
        "sales_order": sales_order_doc.name,
        "token_id": sales_order_doc.name,
        "local_token_id": local_token_id,
        "status": sales_order_doc.docstatus,
    }


def _first_value(*values):
    for value in values:
        value = cstr(value or "").strip()
        if value:
            return value
    return ""
