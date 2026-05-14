# -*- coding: utf-8 -*-

from __future__ import unicode_literals



from posawesome.posawesome.api.pos.relay.constants import (
    RELAY_DISPATCH_STATUSES,
    RELAY_PICKING_STATUSES,
    RELAY_TOKEN_STATUSES,
)

from posawesome.posawesome.api.pos.relay.meta import (
    _get_invoice_linked_sales_order_name,
    _get_relay_invoice_by_local_sale_ref,
    _is_relay_workflow_enabled,
    _relay_workflow_doctype_exists,
    _relay_workflow_has_field,
    _relay_workflow_meta,
    _resolve_relay_workflow_pos_profile,
    _set_relay_state_local_sale_ref,
    _set_state_field_if_exists,
)

from posawesome.posawesome.api.pos.relay.updates import _apply_relay_workflow_state_updates

from posawesome.posawesome.api.pos.relay.sales_order_state import (
    _get_relay_state_doc_for_sales_order,
    _upsert_relay_workflow_state_for_sales_order,
)

from posawesome.posawesome.api.pos.relay.invoice_state import (
    _get_relay_state_doc,
    _upsert_relay_workflow_state,
)
