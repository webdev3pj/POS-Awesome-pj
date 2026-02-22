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
            <div class="mb-2"><b>{{ __('Message') }}:</b> {{ relay_status.message || '-' }}</div>
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
            <div class="mb-2"><b>{{ __('Checked At') }}:</b> {{ relay_status.checked_at || '-' }}</div>
            <div class="mb-2" v-if="relay_status.debug && relay_status.debug.hint"><b>{{ __('Hint') }}:</b> {{ relay_status.debug.hint }}</div>
            <div class="mb-2" v-if="relay_status.debug && relay_status.debug.cloud_reachability_note"><b>{{ __('Cloud Reachability Note') }}:</b> {{ relay_status.debug.cloud_reachability_note }}</div>
            <div class="mb-2" v-if="relay_status.queue && relay_status.connected">
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
            <div class="mb-2"><b>{{ __('URL') }}:</b> {{ cloud_status.url || window.location.origin }}</div>
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
                  v-if="!pos_profile.posa_hide_closing_shift && item == 0"
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
  </nav>
</template>

<script>
import { evntBus } from '../bus';

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
        connected: false,
        status: '',
        message: '',
        relay_source: '',
        relay_config_identified: false,
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
      cloud_poll_timer: null,
    };
  },
  computed: {
    relay_status_chip_text() {
      if (this.relay_status.connected) {
        return __('Relay Online');
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
      return __('Relay Offline');
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
  },
  methods: {
    changePage(key) {
      this.$emit('changePage', key);
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
      evntBus.$emit('open_closing_dialog');
    },
    show_mesage(data) {
      this.snack = true;
      this.snackColor = data.color;
      this.snackText = data.text;
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
        this.relay_status = {
          enabled: false,
          connected: false,
          status: '',
          message: '',
          relay_source: '',
          relay_config_identified: false,
          relay_host: '',
          relay_host_type: '',
          profile_relay_url: '',
          site_relay_url: '',
          http_status: null,
          checked_at: '',
          queue: {},
          debug: {},
        };
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
          this.relay_status = {
            enabled: !!relay.enabled,
            connected: !!relay.connected,
            status: relay.status || '',
            message: relay.message || '',
            relay_source: relay.relay_source || '',
            relay_config_identified: !!relay.relay_config_identified,
            relay_host: relay.relay_host || '',
            relay_host_type: relay.relay_host_type || '',
            profile_relay_url: relay.profile_relay_url || '',
            site_relay_url: relay.site_relay_url || '',
            http_status: relay.http_status || null,
            checked_at: relay.checked_at || '',
            queue: relay.queue || {},
            debug: relay.debug || {},
          };

          if (!silent && relay.enabled) {
            evntBus.$emit('show_mesage', {
              text:
                relay.message ||
                (relay.connected
                  ? __('Relay connection established')
                  : __('Relay connection unavailable')),
              color: relay.connected ? 'success' : 'warning',
            });
          }
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
    this.$nextTick(function () {
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
        this.pos_profile = data.pos_profile;
        const payments = { text: 'Payments', icon: 'mdi-cash-register' };
        if (
          this.pos_profile.posa_use_pos_awesome_payments &&
          this.items.length !== 2
        ) {
          this.items.push(payments);
        }
        this.start_relay_poll(this.pos_profile.name);
      });
      evntBus.$on('check_relay_connectivity', () => {
        this.fetch_relay_status(this.pos_profile && this.pos_profile.name, false);
      });
      evntBus.$on('set_last_invoice', (data) => {
        this.last_invoice = data;
      });
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
    });
  },
  beforeDestroy() {
    this.stop_relay_poll();
    this.stop_cloud_poll();
    window.removeEventListener('online', this.on_online_status_change);
    window.removeEventListener('offline', this.on_online_status_change);
    evntBus.$off('show_mesage');
    evntBus.$off('set_company');
    evntBus.$off('register_pos_profile');
    evntBus.$off('check_relay_connectivity');
    evntBus.$off('set_last_invoice');
    evntBus.$off('freeze');
    evntBus.$off('unfreeze');
  },
};
</script>

<style scoped>
.margen-top {
  margin-top: 0px;
}
</style>
