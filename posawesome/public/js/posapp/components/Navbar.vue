<template>
  <nav>
    <v-app-bar app height="40" class="elevation-2">
      <v-app-bar-nav-icon
        @click.stop="drawer = !drawer"
        class="grey--text"
      ></v-app-bar-nav-icon>
      <v-img
        src="/assets/posawesome/js/posapp/components/pos/pos.png"
        alt="POS Awesome"
        max-width="32"
        class="mr-2"
        color="primary"
      ></v-img>
      <v-toolbar-title
        @click="go_desk"
        style="cursor: pointer"
        class="text-uppercase primary--text"
      >
        <span class="font-weight-light">pos</span>
        <span>awesome</span>
      </v-toolbar-title>

      <v-spacer></v-spacer>
      <v-menu v-if="relay_status.enabled" bottom offset-y>
        <template v-slot:activator="{ on, attrs }">
          <v-chip
            small
            class="mr-2"
            :color="relay_status_chip_color"
            text-color="white"
            v-bind="attrs"
            v-on="on"
          >
            {{ relay_status_chip_text }}
          </v-chip>
        </template>
        <v-card max-width="520" class="pa-2">
          <v-card-title class="text-subtitle-1 pb-1">
            {{ __('Edge Relay Diagnostics') }}
          </v-card-title>
          <v-divider></v-divider>
          <v-card-text class="pt-3">
            <div class="mb-2"><b>{{ __('Status') }}:</b> {{ relay_status.status || '-' }}</div>
            <div class="mb-2"><b>{{ __('Effective Submit Gate') }}:</b> {{ relay_status.submit_gate_source || '-' }}</div>
            <div class="mb-2"><b>{{ __('Connectivity Mode') }}:</b> {{ relay_status.connectivity_mode || 'cloud_checked' }}</div>
            <div class="mb-2"><b>{{ __('Message') }}:</b> {{ relay_status.message || '-' }}</div>
            <div class="mb-2"><b>{{ __('Cloud Diagnostic Status') }}:</b> {{ relay_status.cloud_status || relay_status.status || '-' }}</div>
            <div class="mb-2"><b>{{ __('Cloud Diagnostic Message') }}:</b> {{ relay_status.cloud_message || relay_status.message || '-' }}</div>
            <div class="mb-2"><b>{{ __('Cloud Relay Reachable') }}:</b> {{ relay_status.cloud_connected ? __('Yes') : __('No') }}</div>
            <div class="mb-2"><b>{{ __('Browser-LAN Relay Reachable') }}:</b> {{ relay_status.browser_checked ? (relay_status.browser_connected ? __('Yes') : __('No')) : __('Not checked') }}</div>
            <div class="mb-2" v-if="relay_status.browser_checked"><b>{{ __('Browser-LAN Status') }}:</b> {{ relay_status.browser_status || '-' }}</div>
            <div class="mb-2" v-if="relay_status.browser_checked"><b>{{ __('Browser-LAN Message') }}:</b> {{ relay_status.browser_message || '-' }}</div>
            <div class="mb-2" v-if="relay_status.browser_checked"><b>{{ __('Browser-LAN Checked At') }}:</b> {{ relay_status.browser_checked_at || '-' }}</div>
            <div class="mb-2"><b>{{ __('POS Profile Relay URL') }}:</b> {{ relay_status.profile_relay_url || __('Not set') }}</div>
            <div class="mb-2"><b>{{ __('Site Relay URL') }}:</b> {{ relay_status.site_relay_url || __('Not set') }}</div>
            <div class="mb-2"><b>{{ __('Using') }}:</b> {{ relay_status.relay_source || '-' }}</div>
            <div class="mb-2"><b>{{ __('Relay Identified') }}:</b> {{ relay_status.relay_config_identified ? __('Yes') : __('No') }}</div>
            <div class="mb-2"><b>{{ __('Relay Host') }}:</b> {{ relay_status.relay_host || '-' }}</div>
            <div class="mb-2"><b>{{ __('Relay Host Type') }}:</b> {{ relay_status.relay_host_type || '-' }}</div>
            <div class="mb-2" v-if="relay_status.relay_host_type === 'private_lan'">
              <b>{{ __('LAN Note') }}:</b>
              {{ __('Private LAN address detected. Frappe Cloud can identify this relay config, but it is reachable only if cloud has a network route (VPN/tunnel/public mapping).') }}
            </div>
            <div class="mb-2"><b>{{ __('Health URL') }}:</b> {{ relay_status.debug && relay_status.debug.relay_health_url ? relay_status.debug.relay_health_url : '-' }}</div>
            <div class="mb-2" v-if="relay_status.http_status"><b>{{ __('HTTP Status') }}:</b> {{ relay_status.http_status }}</div>
            <div class="mb-2" v-if="relay_status.cloud_http_status"><b>{{ __('Cloud Relay HTTP Status') }}:</b> {{ relay_status.cloud_http_status }}</div>
            <div class="mb-2" v-if="relay_status.browser_http_status"><b>{{ __('Browser-LAN HTTP Status') }}:</b> {{ relay_status.browser_http_status }}</div>
            <div class="mb-2"><b>{{ __('Checked At') }}:</b> {{ relay_status.checked_at || '-' }}</div>
            <div class="mb-2" v-if="relay_status.debug && relay_status.debug.hint"><b>{{ __('Hint') }}:</b> {{ relay_status.debug.hint }}</div>
            <div class="mb-2" v-if="relay_status.debug && relay_status.debug.mode_note"><b>{{ __('Mode Note') }}:</b> {{ relay_status.debug.mode_note }}</div>
            <div class="mb-2" v-if="relay_status.debug && relay_status.debug.cloud_reachability_note"><b>{{ __('Cloud Reachability Note') }}:</b> {{ relay_status.debug.cloud_reachability_note }}</div>
            <div class="mb-2" v-if="relay_status.queue && relay_status.cloud_connected">
              <b>{{ __('Queue') }}:</b>
              {{ __('Queued') }} {{ relay_status.queue.queued || 0 }},
              {{ __('Processing') }} {{ relay_status.queue.processing || 0 }},
              {{ __('Failed') }} {{ relay_status.queue.failed || 0 }}
            </div>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn small text color="primary" @click="fetch_relay_status(pos_profile && pos_profile.name, false)">
              {{ __('Refresh') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-menu>
      <v-chip
        v-if="relay_status.enabled && !relay_status.connected"
        small
        class="mr-2"
        color="error"
        text-color="white"
      >
        {{ relay_status.connectivity_mode === 'lan_only_browser_checked' ? __('RELAY DOWN (LAN relay unavailable)') : __('RELAY DOWN (Offline continuity unavailable)') }}
      </v-chip>
      <v-chip
        v-if="relay_status.enabled && relay_status.connected && !cloud_status.server_online"
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
            :color="cloud_status_chip_color"
            text-color="white"
            v-bind="attrs"
            v-on="on"
          >
            {{ cloud_status_chip_text }}
          </v-chip>
        </template>
        <v-card max-width="420" class="pa-2">
          <v-card-title class="text-subtitle-1 pb-1">
            {{ __('Cloud Connectivity') }}
          </v-card-title>
          <v-divider></v-divider>
          <v-card-text class="pt-3">
            <div class="mb-2"><b>{{ __('Browser Internet') }}:</b> {{ cloud_status.navigator_online ? __('Online') : __('Offline') }}</div>
            <div class="mb-2"><b>{{ __('Cloud Reachability') }}:</b> {{ cloud_status.server_online ? __('Reachable') : __('Unreachable') }}</div>
            <div class="mb-2"><b>{{ __('URL') }}:</b> {{ cloud_status.url || browser_origin }}</div>
            <div class="mb-2" v-if="cloud_status.response_ms"><b>{{ __('Latency') }}:</b> {{ cloud_status.response_ms }} ms</div>
            <div class="mb-2" v-if="cloud_status.http_status"><b>{{ __('HTTP Status') }}:</b> {{ cloud_status.http_status }}</div>
            <div class="mb-2"><b>{{ __('Checked At') }}:</b> {{ cloud_status.checked_at || '-' }}</div>
            <div class="mb-2"><b>{{ __('Message') }}:</b> {{ cloud_status.message || '-' }}</div>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn small text color="primary" @click="check_cloud_connectivity(false)">
              {{ __('Refresh') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-menu>
      <v-btn style="cursor: unset" text color="primary">
        <span right>{{ pos_profile.name }}</span>
      </v-btn>
      <div class="text-center">
        <v-menu offset-y>
          <template v-slot:activator="{ on, attrs }">
            <v-btn color="primary" dark text v-bind="attrs" v-on="on"
              >Menu</v-btn
            >
          </template>
          <v-card class="mx-auto" max-width="300" tile>
            <v-list dense>
              <v-list-item-group v-model="menu_item" color="primary">
                <v-list-item
                  @click="close_shift_dialog"
                  v-if="can_show_close_shift_action && item == 0"
                >
                  <v-list-item-icon>
                    <v-icon>mdi-content-save-move-outline</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>
                    <v-list-item-title>{{
                      __('Close Shift')
                    }}</v-list-item-title>
                  </v-list-item-content>
                </v-list-item>
                <v-list-item
                  @click="print_last_invoice"
                  v-if="
                    pos_profile.posa_allow_print_last_invoice &&
                    this.last_invoice
                  "
                >
                  <v-list-item-icon>
                    <v-icon>mdi-printer</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>
                    <v-list-item-title>{{
                      __('Print Last Invoice')
                    }}</v-list-item-title>
                  </v-list-item-content>
                </v-list-item>
                <v-divider class="my-0"></v-divider>
                <v-list-item @click="logOut">
                  <v-list-item-icon>
                    <v-icon>mdi-logout</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>
                    <v-list-item-title>{{ __('Logout') }}</v-list-item-title>
                  </v-list-item-content>
                </v-list-item>
                <v-list-item @click="go_about">
                  <v-list-item-icon>
                    <v-icon>mdi-information-outline</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>
                    <v-list-item-title>{{ __('About') }}</v-list-item-title>
                  </v-list-item-content>
                </v-list-item>
                <v-list-item @click="open_relay_settings">
                  <v-list-item-icon>
                    <v-icon>mdi-lan-connect</v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>
                    <v-list-item-title>{{ __('Relay Settings') }}</v-list-item-title>
                  </v-list-item-content>
                </v-list-item>
                <template v-if="show_admin_role_testing">
                  <v-divider class="my-0"></v-divider>
                  <v-subheader>{{ __('Admin Test Role') }}</v-subheader>
                  <v-list-item>
                    <v-list-item-content>
                      <v-select
                        v-model="admin_test_role"
                        :items="admin_test_role_options"
                        dense
                        outlined
                        hide-details
                        @change="change_admin_test_role"
                      ></v-select>
                    </v-list-item-content>
                  </v-list-item>
                </template>
              </v-list-item-group>
            </v-list>
          </v-card>
        </v-menu>
      </div>
    </v-app-bar>
    <v-navigation-drawer
      v-model="drawer"
      :mini-variant.sync="mini"
      app
      class="primary margen-top"
      width="170"
    >
      <v-list dark>
        <v-list-item class="px-2">
          <v-list-item-avatar>
            <v-img :src="company_img"></v-img>
          </v-list-item-avatar>

          <v-list-item-title>{{ company }}</v-list-item-title>

          <v-btn icon @click.stop="mini = !mini">
            <v-icon>mdi-chevron-left</v-icon>
          </v-btn>
        </v-list-item>
        <!-- <MyPopup/> -->
        <v-list-item-group v-model="item" color="white">
          <v-list-item
            v-for="item in items"
            :key="item.text"
            @click="changePage(item.text)"
          >
            <v-list-item-icon>
              <v-icon v-text="item.icon"></v-icon>
            </v-list-item-icon>
            <v-list-item-content>
              <v-list-item-title v-text="item.text"></v-list-item-title>
            </v-list-item-content>
          </v-list-item>
        </v-list-item-group>
        <v-divider v-if="show_workflow_monitor_toggle" class="my-2"></v-divider>
        <v-list-item
          v-if="show_workflow_monitor_toggle"
          class="workflow-monitor-drawer-item"
          @click="toggle_workflow_monitor"
        >
          <v-list-item-icon>
            <v-badge
              :content="String(workflow_monitor_pending_count)"
              :value="workflow_monitor_pending_count > 0"
              color="error"
              overlap
            >
              <v-icon>mdi-ticket-outline</v-icon>
            </v-badge>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title>{{ __('Order Monitor') }}</v-list-item-title>
            <v-list-item-subtitle>
              {{ workflow_monitor_expanded ? __('Open') : __('Show pending orders') }}
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>
    <v-snackbar v-model="snack" :timeout="5000" :color="snackColor" top right>
      {{ snackText }}
    </v-snackbar>
    <v-dialog v-model="freeze" persistent max-width="290">
      <v-card>
        <v-card-title class="text-h5">
          {{ freezeTitle }}
        </v-card-title>
        <v-card-text>{{ freezeMsg }}</v-card-text>
      </v-card>
    </v-dialog>
    <v-dialog v-model="relay_settings_dialog" max-width="520">
      <v-card>
        <v-card-title class="text-subtitle-1">
          {{ __('Edge Relay Settings') }}
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="relay_settings_form.relay_url"
            :label="__('Relay URL')"
            dense
            outlined
            hide-details="auto"
            class="mb-3"
            placeholder="http://192.168.1.9:8787"
          ></v-text-field>
          <v-select
            v-model="relay_settings_form.connectivity_mode"
            :items="relay_connectivity_modes"
            :label="__('Connectivity Mode')"
            dense
            outlined
            hide-details="auto"
            class="mb-3"
          ></v-select>
          <v-text-field
            v-model="relay_settings_form.client_key"
            :label="__('Relay Client Key')"
            dense
            outlined
            hide-details="auto"
            type="password"
            autocomplete="off"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn text color="error" @click="clear_browser_relay_config">
            {{ __('Clear') }}
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn text @click="relay_settings_dialog = false">
            {{ __('Cancel') }}
          </v-btn>
          <v-btn color="primary" @click="save_browser_relay_config">
            {{ __('Save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </nav>
</template>

<script>
import { evntBus } from '../bus';
import {
  OPERATIONAL_ROLES,
  isAdminRoleTestingEnabled,
  resolveCurrentRole,
  setAdminTestRole,
} from '../utils/posRole';

export default {
  // components: {MyPopup},
  data() {
    return {
      drawer: false,
      mini: true,
      item: 0,
      items: [{ text: 'POS', icon: 'mdi-network-pos' }],
      page: '',
      fav: true,
      menu: false,
      message: false,
      hints: true,
      menu_item: 0,
      snack: false,
      snackColor: '',
      snackText: '',
      company: 'POS Awesome',
      company_img: '/assets/erpnext/images/erpnext-logo.svg',
      pos_profile: '',
      freeze: false,
      freezeTitle: '',
      freezeMsg: '',
      last_invoice: '',
      relay_status: {
        enabled: false,
        configured: false,
        connected: false,
        effective_connected: false,
        status: '',
        effective_status: '',
        message: '',
        effective_message: '',
        connectivity_mode: 'cloud_checked',
        submit_gate_source: 'cloud_backend',
        allow_cloud_fallback_when_relay_down: false,
        cloud_connected: false,
        cloud_status: '',
        cloud_message: '',
        cloud_http_status: null,
        cloud_checked_at: '',
        browser_checked: false,
        browser_connected: false,
        browser_status: '',
        browser_message: '',
        browser_http_status: null,
        browser_checked_at: '',
        relay_source: '',
        relay_config_identified: false,
        relay_url: '',
        relay_host: '',
        relay_host_type: '',
        profile_relay_url: '',
        site_relay_url: '',
        http_status: null,
        checked_at: '',
        queue: {},
        debug: {},
      },
      relay_poll_timer: null,
      cloud_status: {
        navigator_online: typeof navigator !== 'undefined' ? !!navigator.onLine : true,
        server_online: false,
        http_status: null,
        response_ms: null,
        checked_at: '',
        message: '',
        url: '',
      },
      browser_origin: typeof window !== 'undefined' && window.location ? window.location.origin : '',
      cloud_poll_timer: null,
      current_role: '',
      admin_role_testing_enabled: false,
      admin_test_role: '',
      admin_test_role_options: OPERATIONAL_ROLES,
      workflow_monitor_pending_count: 0,
      workflow_monitor_expanded: false,
      relay_settings_dialog: false,
      relay_settings_form: {
        relay_url: '',
        connectivity_mode: 'lan_only_browser_checked',
        client_key: '',
      },
      relay_connectivity_modes: [
        { text: 'Browser LAN', value: 'lan_only_browser_checked' },
        { text: 'Cloud Backend', value: 'cloud_checked' },
      ],
    };
  },
  computed: {
    is_sales_associate_role() {
      return (this.current_role || '') === 'cline-Sales Associate';
    },
    can_show_close_shift_action() {
      if (!this.pos_profile || this.pos_profile.posa_hide_closing_shift) return false;
      return !this.is_sales_associate_role;
    },
    relay_status_chip_text() {
      const relayDownText =
        this.relay_status.connectivity_mode === 'lan_only_browser_checked'
          ? __('Relay Offline (LAN)')
          : __('Relay Offline');
      if (this.relay_status.connected) {
        return this.relay_status.connectivity_mode === 'lan_only_browser_checked'
          ? __('Relay Online (LAN)')
          : __('Relay Online');
      }
      if (this.relay_status.status === 'not_configured') {
        return __('Relay Not Configured');
      }
      if (this.relay_status.status === 'timeout') {
        return __('Relay Timeout');
      }
      if (this.relay_status.status === 'connection_error') {
        return __('Relay Connection Error');
      }
      if (this.relay_status.status === 'http_error') {
        return __('Relay HTTP Error');
      }
      if (this.relay_status.status === 'connection_error' && this.relay_status.relay_config_identified) {
        return __('Relay Identified / Not Reachable');
      }
      return relayDownText;
    },
    relay_status_chip_color() {
      if (this.relay_status.connected) return 'success';
      if (this.relay_status.status === 'not_configured') return 'warning';
      if (this.relay_status.status === 'timeout') return 'orange';
      if (this.relay_status.status === 'connection_error') return 'error';
      if (this.relay_status.status === 'http_error') return 'error';
      return 'error';
    },
    cloud_status_chip_text() {
      if (!this.cloud_status.navigator_online) {
        return __('Internet Offline');
      }
      return this.cloud_status.server_online
        ? __('Cloud Online')
        : __('Cloud Unreachable');
    },
    cloud_status_chip_color() {
      if (!this.cloud_status.navigator_online) {
        return 'error';
      }
      return this.cloud_status.server_online ? 'success' : 'warning';
    },
    show_workflow_monitor_toggle() {
      const profile = this.pos_profile || {};
      return parseInt(profile.custom_have_token || 0, 10) === 1;
    },
    show_admin_role_testing() {
      return this.admin_role_testing_enabled;
    },
  },
  methods: {
    sync_current_role() {
      this.admin_role_testing_enabled = isAdminRoleTestingEnabled();
      this.current_role = resolveCurrentRole();
      this.admin_test_role = this.current_role;
    },
    change_admin_test_role(role) {
      const selected = setAdminTestRole(role);
      if (!selected) return;
      this.current_role = selected;
      this.admin_test_role = selected;
      evntBus.$emit('show_mesage', {
        text: __('Administrator test role changed. Reload POS if the visible workspace does not switch immediately.'),
        color: 'info',
      });
      evntBus.$emit('pos_role_changed', { role: selected });
    },
    changePage(key) {
      this.$emit('changePage', key);
    },
    toggle_workflow_monitor() {
      evntBus.$emit('workflow_monitor_toggle_requested');
    },
    on_workflow_monitor_summary_changed(payload) {
      const summary = payload || {};
      const summaryProfile = String(summary.profile_name || '').trim();
      const activeProfile = String((this.pos_profile && this.pos_profile.name) || '').trim();
      if (activeProfile && summaryProfile && activeProfile !== summaryProfile) {
        return;
      }
      this.workflow_monitor_pending_count = parseInt(summary.pending_count || 0, 10) || 0;
      this.workflow_monitor_expanded = !!summary.expanded;
    },
    go_desk() {
      frappe.set_route('/');
      location.reload();
    },
    go_about() {
      const win = window.open(
        'https://github.com/yrestom/POS-Awesome',
        '_blank'
      );
      win.focus();
    },
    close_shift_dialog() {
      this.sync_current_role();
      if (this.is_sales_associate_role) {
        evntBus.$emit('show_mesage', {
          text: __('Close Shift is cashier-only. Sales Associates do not open or close cash shifts.'),
          color: 'warning',
        });
        return;
      }
      evntBus.$emit('open_closing_dialog');
    },
    show_mesage(data) {
      this.snack = true;
      this.snackColor = data.color;
      this.snackText = data.text;
    },
    normalize_relay_url(relayUrl) {
      return String(relayUrl || '').trim().replace(/\/$/, '');
    },
    relay_config_storage_key(profileName) {
      const site =
        (frappe.boot && (frappe.boot.sitename || frappe.boot.site_name)) ||
        window.location.host ||
        'site';
      const profile = String(profileName || 'default').trim() || 'default';
      return `posa_edge_relay_config:${site}:${profile}`;
    },
    relay_default_config_storage_key() {
      return this.relay_config_storage_key('__default__');
    },
    active_profile_storage_key() {
      const site =
        (frappe.boot && (frappe.boot.sitename || frappe.boot.site_name)) ||
        window.location.host ||
        'site';
      return `posa_active_pos_profile:${site}`;
    },
    active_pos_profile_name() {
      const current = String((this.pos_profile && this.pos_profile.name) || '').trim();
      if (current) return current;
      try {
        return String(localStorage.getItem(this.active_profile_storage_key()) || '').trim();
      } catch (e) {
        return '';
      }
    },
    remember_active_pos_profile(profileName) {
      const name = String(profileName || '').trim();
      if (!name) return;
      try {
        localStorage.setItem(this.active_profile_storage_key(), name);
      } catch (e) {}
    },
    load_browser_relay_config(profileName) {
      try {
        const raw =
          localStorage.getItem(this.relay_config_storage_key(profileName)) ||
          localStorage.getItem(this.relay_default_config_storage_key());
        if (!raw) return null;
        const parsed = JSON.parse(raw) || {};
        const relayUrl = this.normalize_relay_url(parsed.relay_url);
        if (!relayUrl) return null;
        return {
          relay_url: relayUrl,
          connectivity_mode:
            parsed.connectivity_mode === 'cloud_checked'
              ? 'cloud_checked'
              : 'lan_only_browser_checked',
          client_key: String(parsed.client_key || '').trim(),
          saved_at: parsed.saved_at || '',
        };
      } catch (e) {
        return null;
      }
    },
    cache_profile_relay_config_if_missing(profile) {
      if (!profile || !profile.name || !navigator.onLine) return;
      if (this.load_browser_relay_config(profile.name)) return;
      const relayUrl = this.normalize_relay_url(profile.custom_edge_relay_url || '');
      if (!relayUrl) return;
      const config = {
        relay_url: relayUrl,
        connectivity_mode:
          profile.posa_edge_relay_connectivity_mode === 'cloud_checked'
            ? 'cloud_checked'
            : 'lan_only_browser_checked',
        client_key: localStorage.getItem('posa_relay_client_key') || '',
        saved_at: frappe.datetime.now_datetime(),
        refreshed_from_profile: 1,
      };
      localStorage.setItem(this.relay_config_storage_key(profile.name), JSON.stringify(config));
      localStorage.setItem(this.relay_default_config_storage_key(), JSON.stringify(config));
    },
    apply_browser_relay_config_to_profile(profile) {
      if (!profile || !profile.name) return profile;
      const browserConfig = this.load_browser_relay_config(profile.name);
      if (!browserConfig) return profile;
      return {
        ...profile,
        custom_have_token: parseInt(profile.custom_have_token || 0, 10) === 1 ? profile.custom_have_token : 1,
        posa_edge_relay_connectivity_mode: browserConfig.connectivity_mode,
      };
    },
    open_relay_settings() {
      const profileName = this.active_pos_profile_name();
      const browserConfig = this.load_browser_relay_config(profileName);
      this.relay_settings_form = {
        relay_url:
          (browserConfig && browserConfig.relay_url) ||
          this.normalize_relay_url(this.relay_status.profile_relay_url || this.relay_status.relay_url || ''),
        connectivity_mode:
          (browserConfig && browserConfig.connectivity_mode) ||
          (this.pos_profile && this.pos_profile.posa_edge_relay_connectivity_mode) ||
          this.relay_status.connectivity_mode ||
          'lan_only_browser_checked',
        client_key:
          (browserConfig && browserConfig.client_key) ||
          (localStorage.getItem('posa_relay_client_key') || ''),
      };
      this.relay_settings_dialog = true;
    },
    save_browser_relay_config() {
      const profileName = this.active_pos_profile_name();
      const relayUrl = this.normalize_relay_url(this.relay_settings_form.relay_url);
      if (!profileName) {
        this.show_mesage({ text: __('Open a POS Profile before saving relay settings.'), color: 'warning' });
        return;
      }
      if (!/^https?:\/\//i.test(relayUrl)) {
        this.show_mesage({ text: __('Relay URL must start with http:// or https://'), color: 'error' });
        return;
      }
      if (!this.pos_profile || !this.pos_profile.name) {
        this.pos_profile = { name: profileName, custom_have_token: 1 };
      }
      const config = {
        relay_url: relayUrl,
        connectivity_mode:
          this.relay_settings_form.connectivity_mode === 'cloud_checked'
            ? 'cloud_checked'
            : 'lan_only_browser_checked',
        client_key: String(this.relay_settings_form.client_key || '').trim(),
        saved_at: frappe.datetime.now_datetime(),
      };
      localStorage.setItem(this.relay_config_storage_key(profileName), JSON.stringify(config));
      localStorage.setItem(this.relay_default_config_storage_key(), JSON.stringify(config));
      if (config.client_key) {
        localStorage.setItem('posa_relay_client_key', config.client_key);
      } else {
        localStorage.removeItem('posa_relay_client_key');
      }
      this.pos_profile = this.apply_browser_relay_config_to_profile(this.pos_profile);
      this.relay_settings_dialog = false;
      this.save_relay_config_to_profile(profileName, config);
      this.show_mesage({ text: __('Relay settings saved for this browser.'), color: 'success' });
      this.fetch_relay_status(profileName, false);
    },
    save_relay_config_to_profile(profileName, config) {
      if (!profileName || !navigator.onLine) {
        return;
      }
      frappe.call({
        method: 'frappe.client.set_value',
        args: {
          doctype: 'POS Profile',
          name: profileName,
          fieldname: {
            custom_edge_relay_url: config.relay_url,
            posa_edge_relay_connectivity_mode: config.connectivity_mode,
          },
        },
        callback: (r) => {
          if (r && !r.exc) {
            this.show_mesage({ text: __('Relay settings also saved to POS Profile.'), color: 'success' });
          }
        },
        error: () => {
          this.show_mesage({
            text: __('Relay settings saved locally. POS Profile save failed; try again while online.'),
            color: 'warning',
          });
        },
      });
    },
    clear_browser_relay_config() {
      const profileName = this.active_pos_profile_name();
      if (profileName) {
        localStorage.removeItem(this.relay_config_storage_key(profileName));
      }
      localStorage.removeItem(this.relay_default_config_storage_key());
      this.relay_settings_form = {
        relay_url: '',
        connectivity_mode: 'lan_only_browser_checked',
        client_key: localStorage.getItem('posa_relay_client_key') || '',
      };
      this.show_mesage({ text: __('Browser relay settings cleared.'), color: 'warning' });
      this.fetch_relay_status(profileName, false);
    },
    apply_pos_profile_registration(data) {
      if (!data || !data.pos_profile) return;
      this.sync_current_role();
      this.remember_active_pos_profile(data.pos_profile.name);
      this.cache_profile_relay_config_if_missing(data.pos_profile);
      this.pos_profile = this.apply_browser_relay_config_to_profile(data.pos_profile);
      const payments = { text: 'Payments', icon: 'mdi-cash-register' };
      if (
        this.pos_profile.posa_use_pos_awesome_payments &&
        this.items.length !== 2
      ) {
        this.items.push(payments);
      }
      this.start_relay_poll(this.pos_profile.name);
    },
    recover_pos_profile_if_missed() {
      if (this.pos_profile && this.pos_profile.name) return;
      frappe.call({
        method: 'posawesome.posawesome.api.posapp.check_opening_shift',
        args: { user: frappe.session.user },
        async: true,
        callback: (r) => {
          const msg = r && r.message;
          if (!msg || !msg.pos_profile) return;
          if (this.pos_profile && this.pos_profile.name) return;
          this.apply_pos_profile_registration(msg);
        },
      });
      const storedProfile = this.active_pos_profile_name();
      if (storedProfile && navigator.onLine) {
        frappe.db
          .get_doc('POS Profile', storedProfile)
          .then((profile) => {
            if (!profile || (this.pos_profile && this.pos_profile.name)) return;
            this.apply_pos_profile_registration({ pos_profile: profile });
          })
          .catch(() => {});
      } else if (storedProfile) {
        this.pos_profile = { name: storedProfile, custom_have_token: 1 };
      }
    },
    emit_cloud_status_changed() {
      evntBus.$emit('cloud_status_changed', { ...(this.cloud_status || {}) });
    },
    build_empty_relay_status() {
      return {
        enabled: false,
        configured: false,
        connected: false,
        effective_connected: false,
        status: '',
        effective_status: '',
        message: '',
        effective_message: '',
        connectivity_mode: 'cloud_checked',
        submit_gate_source: 'cloud_backend',
        allow_cloud_fallback_when_relay_down: false,
        cloud_connected: false,
        cloud_status: '',
        cloud_message: '',
        cloud_http_status: null,
        cloud_checked_at: '',
        browser_checked: false,
        browser_connected: false,
        browser_status: '',
        browser_message: '',
        browser_http_status: null,
        browser_checked_at: '',
        relay_source: '',
        relay_config_identified: false,
        relay_url: '',
        relay_host: '',
        relay_host_type: '',
        profile_relay_url: '',
        site_relay_url: '',
        http_status: null,
        checked_at: '',
        queue: {},
        debug: {},
      };
    },
    async check_browser_relay_connectivity(relayBaseUrl) {
      const relayUrl = String(relayBaseUrl || '').trim().replace(/\/$/, '');
      const checkedAt = frappe.datetime.now_datetime();
      if (!relayUrl) {
        return {
          checked: false,
          connected: false,
          status: 'not_configured',
          message: __('Relay URL is not configured for browser health check.'),
          http_status: null,
          checked_at: checkedAt,
        };
      }

      const healthUrl = `${relayUrl}/health`;
      const timeoutMs = 3000;
      const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
      let timeoutHandle = null;
      try {
        if (controller) {
          timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
        }
        const resp = await fetch(`${healthUrl}?_=${Date.now()}`, {
          method: 'GET',
          cache: 'no-store',
          mode: 'cors',
          signal: controller ? controller.signal : undefined,
        });

        let payload = {};
        try {
          payload = await resp.json();
        } catch (e) {
          payload = {};
        }

        if (!resp.ok) {
          return {
            checked: true,
            connected: false,
            status: 'http_error',
            message: __('Browser reached relay URL, but relay /health returned an HTTP error.'),
            http_status: resp.status,
            checked_at: checkedAt,
          };
        }

        const relayOk = !!(payload && payload.ok);
        return {
          checked: true,
          connected: relayOk,
          status: relayOk ? 'online' : 'offline',
          message: relayOk
            ? __('Browser-LAN relay health check passed.')
            : __('Relay responded to browser health check but reported unhealthy status.'),
          http_status: resp.status,
          checked_at: checkedAt,
        };
      } catch (error) {
        const isAbort = !!(error && (error.name === 'AbortError' || /abort/i.test(String(error.message || ''))));
        return {
          checked: true,
          connected: false,
          status: isAbort ? 'timeout' : 'connection_error',
          message: isAbort
            ? __('Browser-LAN relay health check timed out.')
            : __('Browser could not reach relay URL over LAN. Check LAN HTTPS/cert trust/firewall.'),
          http_status: null,
          checked_at: checkedAt,
        };
      } finally {
        if (timeoutHandle) {
          clearTimeout(timeoutHandle);
        }
      }
    },
    async resolve_effective_relay_status(baseStatus) {
      const relayStatus = { ...this.build_empty_relay_status(), ...(baseStatus || {}) };
      const profileName = this.pos_profile && this.pos_profile.name;
      const browserConfig = this.load_browser_relay_config(profileName);
      if (browserConfig) {
        relayStatus.enabled = true;
        relayStatus.configured = true;
        relayStatus.relay_source = 'browser_cache';
        relayStatus.relay_config_identified = true;
        relayStatus.relay_url = browserConfig.relay_url;
        relayStatus.profile_relay_url = browserConfig.relay_url;
        relayStatus.connectivity_mode = browserConfig.connectivity_mode;
        relayStatus.status = relayStatus.status === 'not_configured' ? '' : relayStatus.status;
        relayStatus.message = __('Using browser-cached Edge Relay URL.');
      } else {
        relayStatus.configured = false;
        relayStatus.relay_source = '';
        relayStatus.relay_config_identified = false;
        relayStatus.relay_url = '';
        relayStatus.profile_relay_url = '';
        relayStatus.site_relay_url = '';
        relayStatus.status = 'not_configured';
        relayStatus.message = __('Relay URL is not configured in this browser.');
      }
      const mode =
        relayStatus.connectivity_mode === 'lan_only_browser_checked'
          ? 'lan_only_browser_checked'
          : 'cloud_checked';
      relayStatus.connectivity_mode = mode;
      relayStatus.submit_gate_source = mode === 'lan_only_browser_checked' ? 'browser_lan' : 'cloud_backend';
      relayStatus.effective_connected = !!relayStatus.cloud_connected;
      relayStatus.effective_status = relayStatus.cloud_status || relayStatus.status || '';
      relayStatus.effective_message = relayStatus.cloud_message || relayStatus.message || '';

      const relayUrl = String(
        relayStatus.profile_relay_url || relayStatus.site_relay_url || relayStatus.relay_url || ''
      )
        .trim()
        .replace(/\/$/, '');

      if (relayStatus.enabled && relayStatus.configured && mode === 'lan_only_browser_checked' && relayUrl) {
        const browserStatus = await this.check_browser_relay_connectivity(relayUrl);
        relayStatus.browser_checked = !!browserStatus.checked;
        relayStatus.browser_connected = !!browserStatus.connected;
        relayStatus.browser_status = browserStatus.status || '';
        relayStatus.browser_message = browserStatus.message || '';
        relayStatus.browser_http_status = browserStatus.http_status || null;
        relayStatus.browser_checked_at = browserStatus.checked_at || '';
        relayStatus.effective_connected = !!browserStatus.connected;
        relayStatus.effective_status = browserStatus.status || relayStatus.effective_status || '';
        relayStatus.effective_message = browserStatus.message || relayStatus.effective_message || '';
      }

      relayStatus.connected = !!relayStatus.effective_connected;
      relayStatus.status = relayStatus.effective_status || relayStatus.status || '';
      relayStatus.message = relayStatus.effective_message || relayStatus.message || '';
      return relayStatus;
    },
    logOut() {
      var me = this;
      me.logged_out = true;
      return frappe.call({
        method: 'logout',
        callback: function (r) {
          if (r.exc) {
            return;
          }
          frappe.set_route('/login');
          location.reload();
        },
      });
    },
    print_last_invoice() {
      if (!this.last_invoice) return;
      const print_format =
        this.pos_profile.print_format_for_online ||
        this.pos_profile.print_format;
      const letter_head = this.pos_profile.letter_head || 0;
      const url =
        frappe.urllib.get_base_url() +
        '/printview?doctype=Sales%20Invoice&name=' +
        this.last_invoice +
        '&trigger_print=1' +
        '&format=' +
        print_format +
        '&no_letterhead=' +
        letter_head;
      const printWindow = window.open(url, 'Print');
      printWindow.addEventListener(
        'load',
        function () {
          printWindow.print();
        },
        true
      );
    },
    fetch_relay_status(profileName, silent = true) {
      if (!profileName) {
        this.relay_status = this.build_empty_relay_status();
        evntBus.$emit('relay_status_changed', this.relay_status);
        return;
      }
      if (!navigator.onLine) {
        this.resolve_effective_relay_status(this.build_empty_relay_status()).then((resolvedStatus) => {
          this.relay_status = resolvedStatus;
          evntBus.$emit('relay_status_changed', this.relay_status);
        });
        return;
      }

      frappe.call({
        method: 'posawesome.posawesome.api.posapp.get_relay_connectivity_status',
        args: {
          pos_profile: profileName,
        },
        async: true,
        callback: (r) => {
          const relay = r.message || {};
          const backendRelayStatus = {
            enabled: !!relay.enabled,
            configured: typeof relay.configured === 'boolean' ? !!relay.configured : true,
            connected: !!relay.connected,
            effective_connected: !!relay.connected,
            cloud_connected: typeof relay.cloud_connected === 'boolean' ? !!relay.cloud_connected : !!relay.connected,
            status: relay.status || '',
            effective_status: relay.status || '',
            cloud_status: relay.cloud_status || relay.status || '',
            message: relay.message || '',
            effective_message: relay.message || '',
            cloud_message: relay.cloud_message || relay.message || '',
            connectivity_mode: relay.connectivity_mode || 'cloud_checked',
            submit_gate_source: relay.submit_gate_source || 'cloud_backend',
            allow_cloud_fallback_when_relay_down: !!relay.allow_cloud_fallback_when_relay_down,
            relay_source: relay.relay_source || '',
            relay_config_identified: !!relay.relay_config_identified,
            relay_url: this.normalize_relay_url(relay.relay_url || ''),
            relay_host: relay.relay_host || '',
            relay_host_type: relay.relay_host_type || '',
            profile_relay_url: this.normalize_relay_url(relay.profile_relay_url || ''),
            site_relay_url: this.normalize_relay_url(relay.site_relay_url || ''),
            http_status: relay.http_status || null,
            cloud_http_status:
              relay.cloud_http_status !== undefined && relay.cloud_http_status !== null
                ? relay.cloud_http_status
                : relay.http_status || null,
            cloud_checked_at: relay.cloud_checked_at || relay.checked_at || '',
            checked_at: relay.checked_at || '',
            queue: relay.queue || {},
            debug: relay.debug || {},
            browser_checked: false,
            browser_connected: false,
            browser_status: '',
            browser_message: '',
            browser_http_status: null,
            browser_checked_at: '',
          };
          this.resolve_effective_relay_status(backendRelayStatus).then((resolvedStatus) => {
            this.relay_status = resolvedStatus;
            evntBus.$emit('relay_status_changed', this.relay_status);

            if (!silent && relay.enabled && this.relay_status.relay_source !== 'browser_cache') {
              evntBus.$emit('show_mesage', {
                text:
                  this.relay_status.message ||
                  (this.relay_status.connected
                    ? __('Relay connection established')
                    : __('Relay connection unavailable')),
                color: this.relay_status.connected ? 'success' : 'warning',
              });
            }
          });
        },
      });
    },
    start_relay_poll(profileName) {
      if (this.relay_poll_timer) {
        clearInterval(this.relay_poll_timer);
        this.relay_poll_timer = null;
      }

      if (!profileName) return;
      this.fetch_relay_status(profileName, false);
      this.relay_poll_timer = setInterval(() => {
        this.fetch_relay_status(profileName, true);
      }, 15000);
    },
    stop_relay_poll() {
      if (this.relay_poll_timer) {
        clearInterval(this.relay_poll_timer);
        this.relay_poll_timer = null;
      }
    },
    async check_cloud_connectivity(silent = true) {
      const targetUrl = window.location.origin;
      const startedAt = Date.now();
      const online = typeof navigator !== 'undefined' ? !!navigator.onLine : true;

      if (!online) {
        this.cloud_status = {
          navigator_online: false,
          server_online: false,
          http_status: null,
          response_ms: null,
          checked_at: frappe.datetime.now_datetime(),
          message: __('Browser reports no internet connection.'),
          url: targetUrl,
        };
        if (!silent) {
          evntBus.$emit('show_mesage', {
            text: __('Internet appears offline on this device.'),
            color: 'warning',
          });
        }
        this.emit_cloud_status_changed();
        return;
      }

      try {
        const resp = await fetch(`/api/method/frappe.auth.get_logged_user?_=${Date.now()}`, {
          method: 'GET',
          cache: 'no-store',
          credentials: 'same-origin',
        });
        const ms = Date.now() - startedAt;
        const reachable = resp.ok;
        this.cloud_status = {
          navigator_online: true,
          server_online: reachable,
          http_status: resp.status,
          response_ms: ms,
          checked_at: frappe.datetime.now_datetime(),
          message: reachable
            ? __('Frappe Cloud is reachable.')
            : __('Frappe Cloud responded with an error status.'),
          url: targetUrl,
        };
        if (!silent) {
          evntBus.$emit('show_mesage', {
            text: this.cloud_status.message,
            color: reachable ? 'success' : 'warning',
          });
        }
        this.emit_cloud_status_changed();
      } catch (error) {
        this.cloud_status = {
          navigator_online: true,
          server_online: false,
          http_status: null,
          response_ms: Date.now() - startedAt,
          checked_at: frappe.datetime.now_datetime(),
          message: __('Unable to reach Frappe Cloud from browser/network.'),
          url: targetUrl,
        };
        if (!silent) {
          evntBus.$emit('show_mesage', {
            text: __('Unable to reach Frappe Cloud from this POS session.'),
            color: 'warning',
          });
        }
        this.emit_cloud_status_changed();
      }
    },
    start_cloud_poll() {
      if (this.cloud_poll_timer) {
        clearInterval(this.cloud_poll_timer);
        this.cloud_poll_timer = null;
      }
      this.check_cloud_connectivity(true);
      this.cloud_poll_timer = setInterval(() => {
        this.check_cloud_connectivity(true);
      }, 15000);
    },
    stop_cloud_poll() {
      if (this.cloud_poll_timer) {
        clearInterval(this.cloud_poll_timer);
        this.cloud_poll_timer = null;
      }
    },
    on_online_status_change() {
      this.check_cloud_connectivity(false);
    },
  },
  created: function () {
    // Register event-bus listeners synchronously to avoid missing the initial
    // `register_pos_profile` emit during fast POS boot / role-switch flows.
    this.sync_current_role();
    this.start_cloud_poll();
    window.addEventListener('online', this.on_online_status_change);
    window.addEventListener('offline', this.on_online_status_change);
    evntBus.$on('show_mesage', (data) => {
      this.show_mesage(data);
    });
    evntBus.$on('set_company', (data) => {
      this.company = data.name;
      this.company_img = data.company_logo
        ? data.company_logo
        : this.company_img;
    });
    evntBus.$on('register_pos_profile', (data) => {
      this.apply_pos_profile_registration(data);
    });
    evntBus.$on('register_pos_data', (data) => {
      this.apply_pos_profile_registration(data);
    });
    evntBus.$on('check_relay_connectivity', () => {
      this.fetch_relay_status(this.pos_profile && this.pos_profile.name, false);
    });
    evntBus.$on('set_last_invoice', (data) => {
      this.last_invoice = data;
    });
    evntBus.$on('workflow_monitor_summary_changed', this.on_workflow_monitor_summary_changed);
    evntBus.$on('freeze', (data) => {
      this.freeze = true;
      this.freezeTitle = data.title;
      this.freezeMsg = data.msg;
    });
    evntBus.$on('unfreeze', () => {
      this.freeze = false;
      this.freezTitle = '';
      this.freezeMsg = '';
    });
    // If the navbar was created after POS emitted `register_pos_profile`, recover
    // the active profile from the opening shift session and start relay polling.
    setTimeout(() => {
      this.recover_pos_profile_if_missed();
    }, 250);
  },
  beforeDestroy() {
    this.stop_relay_poll();
    this.stop_cloud_poll();
    window.removeEventListener('online', this.on_online_status_change);
    window.removeEventListener('offline', this.on_online_status_change);
    evntBus.$off('show_mesage');
    evntBus.$off('set_company');
    evntBus.$off('register_pos_profile');
    evntBus.$off('register_pos_data');
    evntBus.$off('check_relay_connectivity');
    evntBus.$off('set_last_invoice');
    evntBus.$off('workflow_monitor_summary_changed', this.on_workflow_monitor_summary_changed);
    evntBus.$off('freeze');
    evntBus.$off('unfreeze');
  },
};
</script>

<style scoped>
.margen-top {
  margin-top: 0px;
}

.workflow-monitor-drawer-item :deep(.v-list-item__subtitle) {
  color: rgba(255, 255, 255, 0.72);
}
</style>
