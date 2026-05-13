# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from posawesome.posawesome.doctype.delivery_charges.delivery_charges import (
    get_applicable_delivery_charges as get_delivery_charges,
)


def get_applicable_delivery_charges(
    company, pos_profile, customer, shipping_address_name=None
):
    return get_delivery_charges(company, pos_profile, customer, shipping_address_name)

