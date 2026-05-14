# -*- coding: utf-8 -*-

from __future__ import unicode_literals



from posawesome.posawesome.api.pos.relay.connectivity_config import (
    _get_edge_relay_base_url,
    _get_pos_profile_allow_cloud_fallback_when_relay_down,
    _get_pos_profile_edge_relay_url,
    _get_pos_profile_field_if_exists,
    _get_pos_profile_relay_connectivity_mode,
    _is_private_lan_host,
)

from posawesome.posawesome.api.pos.relay.connectivity_status import get_relay_connectivity_status
