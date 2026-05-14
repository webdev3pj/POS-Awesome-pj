# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import json



import frappe

from frappe.utils import nowdate

from frappe.utils.caching import redis_cache

from erpnext.stock.get_item_details import get_item_details

from erpnext.stock.doctype.batch.batch import get_batch_qty



from posawesome.posawesome.api.pos.catalog.stock import get_stock_availability

from posawesome.posawesome.api.pos.item.attributes import get_item_attributes



def get_items_details(pos_profile, items_data):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 60

    @redis_cache(ttl=ttl or 1800)
    def __get_items_details(pos_profile, items_data):
        return _get_items_details(pos_profile, items_data)

    def _get_items_details(pos_profile, items_data):
        today = nowdate()
        pos_profile = json.loads(pos_profile)
        items_data = json.loads(items_data)
        warehouse = pos_profile.get("warehouse")
        result = []

        if len(items_data) > 0:
            for item in items_data:
                item_code = item.get("item_code")
                item_stock_qty = get_stock_availability(item_code, warehouse)
                has_batch_no, has_serial_no = frappe.get_value(
                    "Item", item_code, ["has_batch_no", "has_serial_no"]
                )

                uoms = frappe.get_all(
                    "UOM Conversion Detail",
                    filters={"parent": item_code},
                    fields=["uom", "conversion_factor"],
                )

                serial_no_data = frappe.get_all(
                    "Serial No",
                    filters={
                        "item_code": item_code,
                        "status": "Active",
                        "warehouse": warehouse,
                    },
                    fields=["name as serial_no"],
                )

                batch_no_data = []

                batch_list = get_batch_qty(warehouse=warehouse, item_code=item_code)

                if batch_list:
                    for batch in batch_list:
                        if batch.qty > 0 and batch.batch_no:
                            batch_doc = frappe.get_cached_doc("Batch", batch.batch_no)
                            if (
                                str(batch_doc.expiry_date) > str(today)
                                or batch_doc.expiry_date in ["", None]
                            ) and batch_doc.disabled == 0:
                                batch_no_data.append(
                                    {
                                        "batch_no": batch.batch_no,
                                        "batch_qty": batch.qty,
                                        "expiry_date": batch_doc.expiry_date,
                                        "batch_price": batch_doc.posa_batch_price,
                                        "manufacturing_date": batch_doc.manufacturing_date,
                                    }
                                )

                row = {}
                row.update(item)
                row.update(
                    {
                        "item_uoms": uoms or [],
                        "serial_no_data": serial_no_data or [],
                        "batch_no_data": batch_no_data or [],
                        "actual_qty": item_stock_qty or 0,
                        "has_batch_no": has_batch_no,
                        "has_serial_no": has_serial_no,
                    }
                )

                result.append(row)

        return result

    if _pos_profile.get("posa_use_server_cache"):
        return __get_items_details(pos_profile, items_data)
    else:
        return _get_items_details(pos_profile, items_data)

def get_item_detail(item, doc=None, warehouse=None, price_list=None):
    item = json.loads(item)
    today = nowdate()
    item_code = item.get("item_code")
    batch_no_data = []
    if warehouse and item.get("has_batch_no"):
        batch_list = get_batch_qty(warehouse=warehouse, item_code=item_code)
        if batch_list:
            for batch in batch_list:
                if batch.qty > 0 and batch.batch_no:
                    batch_doc = frappe.get_cached_doc("Batch", batch.batch_no)
                    if (
                        str(batch_doc.expiry_date) > str(today)
                        or batch_doc.expiry_date in ["", None]
                    ) and batch_doc.disabled == 0:
                        batch_no_data.append(
                            {
                                "batch_no": batch.batch_no,
                                "batch_qty": batch.qty,
                                "expiry_date": batch_doc.expiry_date,
                                "batch_price": batch_doc.posa_batch_price,
                                "manufacturing_date": batch_doc.manufacturing_date,
                            }
                        )

    item["selling_price_list"] = price_list

    max_discount = frappe.get_value("Item", item_code, "max_discount")
    res = get_item_details(
        item,
        doc,
        overwrite_warehouse=False,
    )
    if item.get("is_stock_item") and warehouse:
        res["actual_qty"] = get_stock_availability(item_code, warehouse)
    res["max_discount"] = max_discount
    res["batch_no_data"] = batch_no_data
    return res

def get_items_from_barcode(selling_price_list, currency, barcode):
    search_item = frappe.get_all(
        "Item Barcode",
        filters={"barcode": barcode},
        fields=["parent", "barcode", "posa_uom"],
    )
    if len(search_item) == 0:
        return ""
    item_code = search_item[0].parent
    item_list = frappe.get_all(
        "Item",
        filters={"name": item_code},
        fields=[
            "name",
            "item_name",
            "description",
            "stock_uom",
            "image",
            "is_stock_item",
            "has_variants",
            "variant_of",
            "item_group",
            "has_batch_no",
            "has_serial_no",
        ],
    )

    if item_list[0]:
        item = item_list[0]
        filters = {"price_list": selling_price_list, "item_code": item_code}
        prices_with_uom = frappe.db.count(
            "Item Price",
            filters={
                "price_list": selling_price_list,
                "item_code": item_code,
                "uom": item.stock_uom,
            },
        )

        if prices_with_uom > 0:
            filters["uom"] = item.stock_uom
        else:
            filters["uom"] = ["in", ["", None, item.stock_uom]]

        item_prices_data = frappe.get_all(
            "Item Price",
            fields=["item_code", "price_list_rate", "currency"],
            filters=filters,
        )

        item_price = 0
        if len(item_prices_data):
            item_price = item_prices_data[0].get("price_list_rate")
            currency = item_prices_data[0].get("currency")

        item.update(
            {
                "rate": item_price,
                "currency": currency,
                "item_code": item_code,
                "barcode": barcode,
                "actual_qty": 0,
                "item_barcode": search_item,
            }
        )
        return item
