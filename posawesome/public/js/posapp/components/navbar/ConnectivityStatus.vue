<template>
  <span v-if="show" class="d-inline-flex align-center">
    <v-menu v-if="relayStatus.enabled" bottom offset-y>
      <template v-slot:activator="{ on, attrs }">
        <v-chip
          small
          class="mr-2"
          :color="relayChipColor"
          text-color="white"
          v-bind="attrs"
          v-on="on"
        >
          {{ relayChipText }}
        </v-chip>
      </template>
      <v-card max-width="520" class="pa-2">
        <v-card-title class="text-subtitle-1 pb-1">
          {{ __('Edge Relay Diagnostics') }}
        </v-card-title>
        <v-divider></v-divider>
        <v-card-text class="pt-3">
          <div class="mb-2"><b>{{ __('Status') }}:</b> {{ relayStatus.status || '-' }}</div>
          <div class="mb-2"><b>{{ __('Effective Submit Gate') }}:</b> {{ relayStatus.submit_gate_source || '-' }}</div>
          <div class="mb-2"><b>{{ __('Connectivity Mode') }}:</b> {{ relayStatus.connectivity_mode || 'cloud_checked' }}</div>
          <div class="mb-2"><b>{{ __('Message') }}:</b> {{ relayStatus.message || '-' }}</div>
          <div class="mb-2"><b>{{ __('Cloud Diagnostic Status') }}:</b> {{ relayStatus.cloud_status || relayStatus.status || '-' }}</div>
          <div class="mb-2"><b>{{ __('Cloud Diagnostic Message') }}:</b> {{ relayStatus.cloud_message || relayStatus.message || '-' }}</div>
          <div class="mb-2"><b>{{ __('Cloud Relay Reachable') }}:</b> {{ relayStatus.cloud_connected ? __('Yes') : __('No') }}</div>
          <div class="mb-2"><b>{{ __('Browser-LAN Relay Reachable') }}:</b> {{ relayStatus.browser_checked ? (relayStatus.browser_connected ? __('Yes') : __('No')) : __('Not checked') }}</div>
          <div class="mb-2" v-if="relayStatus.browser_checked"><b>{{ __('Browser-LAN Status') }}:</b> {{ relayStatus.browser_status || '-' }}</div>
          <div class="mb-2" v-if="relayStatus.browser_checked"><b>{{ __('Browser-LAN Message') }}:</b> {{ relayStatus.browser_message || '-' }}</div>
          <div class="mb-2" v-if="relayStatus.browser_checked"><b>{{ __('Browser-LAN Checked At') }}:</b> {{ relayStatus.browser_checked_at || '-' }}</div>
          <div class="mb-2"><b>{{ __('POS Profile Relay URL') }}:</b> {{ relayStatus.profile_relay_url || __('Not set') }}</div>
          <div class="mb-2"><b>{{ __('Site Relay URL') }}:</b> {{ relayStatus.site_relay_url || __('Not set') }}</div>
          <div class="mb-2"><b>{{ __('Using') }}:</b> {{ relayStatus.relay_source || '-' }}</div>
          <div class="mb-2"><b>{{ __('Relay Identified') }}:</b> {{ relayStatus.relay_config_identified ? __('Yes') : __('No') }}</div>
          <div class="mb-2"><b>{{ __('Relay Host') }}:</b> {{ relayStatus.relay_host || '-' }}</div>
          <div class="mb-2"><b>{{ __('Relay Host Type') }}:</b> {{ relayStatus.relay_host_type || '-' }}</div>
          <div class="mb-2" v-if="relayStatus.relay_host_type === 'private_lan'">
            <b>{{ __('LAN Note') }}:</b>
            {{ __('Private LAN address detected. Frappe Cloud can identify this relay config, but it is reachable only if cloud has a network route (VPN/tunnel/public mapping).') }}
          </div>
          <div class="mb-2"><b>{{ __('Health URL') }}:</b> {{ relayHealthUrl }}</div>
          <div class="mb-2" v-if="relayStatus.http_status"><b>{{ __('HTTP Status') }}:</b> {{ relayStatus.http_status }}</div>
          <div class="mb-2" v-if="relayStatus.cloud_http_status"><b>{{ __('Cloud Relay HTTP Status') }}:</b> {{ relayStatus.cloud_http_status }}</div>
          <div class="mb-2" v-if="relayStatus.browser_http_status"><b>{{ __('Browser-LAN HTTP Status') }}:</b> {{ relayStatus.browser_http_status }}</div>
          <div class="mb-2"><b>{{ __('Checked At') }}:</b> {{ relayStatus.checked_at || '-' }}</div>
          <div class="mb-2" v-if="relayStatus.debug && relayStatus.debug.hint"><b>{{ __('Hint') }}:</b> {{ relayStatus.debug.hint }}</div>
          <div class="mb-2" v-if="relayStatus.debug && relayStatus.debug.mode_note"><b>{{ __('Mode Note') }}:</b> {{ relayStatus.debug.mode_note }}</div>
          <div class="mb-2" v-if="relayStatus.debug && relayStatus.debug.cloud_reachability_note"><b>{{ __('Cloud Reachability Note') }}:</b> {{ relayStatus.debug.cloud_reachability_note }}</div>
          <div class="mb-2" v-if="relayStatus.queue && relayStatus.cloud_connected">
            <b>{{ __('Queue') }}:</b>
            {{ __('Queued') }} {{ relayStatus.queue.queued || 0 }},
            {{ __('Processing') }} {{ relayStatus.queue.processing || 0 }},
            {{ __('Failed') }} {{ relayStatus.queue.failed || 0 }}
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn small text color="primary" @click="$emit('refresh-relay')">
            {{ __('Refresh') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-menu>
    <v-chip
      v-if="relayStatus.enabled && !relayStatus.connected"
      small
      class="mr-2"
      color="error"
      text-color="white"
    >
      {{ relayDownText }}
    </v-chip>
    <v-chip
      v-if="relayStatus.enabled && relayStatus.connected && !cloudStatus.server_online"
      small
      class="mr-2"
      color="warning"
      text-color="white"
    >
      {{ __('OFFLINE MODE (Relay Active)') }}
    </v-chip>
    <v-menu bottom offset-y>
      <template v-slot:activator="{ on, attrs }">
        <v-chip
          small
          class="mr-2"
          :color="cloudChipColor"
          text-color="white"
          v-bind="attrs"
          v-on="on"
        >
          {{ cloudChipText }}
        </v-chip>
      </template>
      <v-card max-width="420" class="pa-2">
        <v-card-title class="text-subtitle-1 pb-1">
          {{ __('Cloud Connectivity') }}
        </v-card-title>
        <v-divider></v-divider>
        <v-card-text class="pt-3">
          <div class="mb-2"><b>{{ __('Browser Internet') }}:</b> {{ cloudStatus.navigator_online ? __('Online') : __('Offline') }}</div>
          <div class="mb-2"><b>{{ __('Cloud Reachability') }}:</b> {{ cloudStatus.server_online ? __('Reachable') : __('Unreachable') }}</div>
          <div class="mb-2"><b>{{ __('URL') }}:</b> {{ cloudStatus.url || browserOrigin }}</div>
          <div class="mb-2" v-if="cloudStatus.response_ms"><b>{{ __('Latency') }}:</b> {{ cloudStatus.response_ms }} ms</div>
          <div class="mb-2" v-if="cloudStatus.http_status"><b>{{ __('HTTP Status') }}:</b> {{ cloudStatus.http_status }}</div>
          <div class="mb-2"><b>{{ __('Checked At') }}:</b> {{ cloudStatus.checked_at || '-' }}</div>
          <div class="mb-2"><b>{{ __('Message') }}:</b> {{ cloudStatus.message || '-' }}</div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn small text color="primary" @click="$emit('refresh-cloud')">
            {{ __('Refresh') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-menu>
  </span>
</template>

<script>
export default {
  props: {
    show: Boolean,
    relayStatus: {
      type: Object,
      default: () => ({}),
    },
    relayChipText: {
      type: String,
      default: '',
    },
    relayChipColor: {
      type: String,
      default: 'error',
    },
    cloudStatus: {
      type: Object,
      default: () => ({}),
    },
    cloudChipText: {
      type: String,
      default: '',
    },
    cloudChipColor: {
      type: String,
      default: 'warning',
    },
    browserOrigin: {
      type: String,
      default: '',
    },
  },
  computed: {
    relayDownText() {
      return this.relayStatus.connectivity_mode === 'lan_only_browser_checked'
        ? __('RELAY DOWN (LAN relay unavailable)')
        : __('RELAY DOWN (Offline continuity unavailable)');
    },
    relayHealthUrl() {
      return this.relayStatus.debug && this.relayStatus.debug.relay_health_url
        ? this.relayStatus.debug.relay_health_url
        : '-';
    },
  },
};
</script>
