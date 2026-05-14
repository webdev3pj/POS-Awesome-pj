# -*- coding: utf-8 -*-

from __future__ import unicode_literals



import json



import frappe

from frappe.utils.caching import redis_cache



from posawesome.posawesome.api.pos.catalog.groups import get_customer_group_condition



def get_customer_names(pos_profile):
    _pos_profile = json.loads(pos_profile)
    ttl = _pos_profile.get("posa_server_cache_duration")
    if ttl:
        ttl = int(ttl) * 60

    @redis_cache(ttl=ttl or 1800)
    def __get_customer_names(pos_profile):
        return _get_customer_names(pos_profile)

    def _get_customer_names(pos_profile):
        pos_profile = json.loads(pos_profile)
        condition = ""
        condition += get_customer_group_condition(pos_profile)
        customers = frappe.db.sql(
            """
            SELECT name, mobile_no, email_id, tax_id, customer_name, primary_address
            FROM `tabCustomer`
            WHERE {0}
            ORDER by name
            """.format(
                condition
            ),
            as_dict=1,
        )
        return customers

    if _pos_profile.get("posa_use_server_cache"):
        return __get_customer_names(pos_profile)
    else:
        return _get_customer_names(pos_profile)
