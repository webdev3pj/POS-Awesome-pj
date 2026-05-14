<template>
  <div class="text-center">
    <v-menu offset-y>
      <template v-slot:activator="{ on, attrs }">
        <v-btn color="primary" dark text v-bind="attrs" v-on="on">
          Menu
        </v-btn>
      </template>
      <v-card class="mx-auto" max-width="300" tile>
        <v-list dense>
          <v-list-item-group :value="menuItem" color="primary">
            <v-list-item
              v-if="canShowCloseShiftAction && activeItem == 0"
              @click="$emit('close-shift')"
            >
              <v-list-item-icon>
                <v-icon>mdi-content-save-move-outline</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>{{ __('Close Shift') }}</v-list-item-title>
              </v-list-item-content>
            </v-list-item>
            <v-list-item
              v-if="posProfile.posa_allow_print_last_invoice && lastInvoice"
              @click="$emit('print-last-invoice')"
            >
              <v-list-item-icon>
                <v-icon>mdi-printer</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>{{ __('Print Last Invoice') }}</v-list-item-title>
              </v-list-item-content>
            </v-list-item>
            <v-divider class="my-0"></v-divider>
            <v-list-item @click="$emit('logout')">
              <v-list-item-icon>
                <v-icon>mdi-logout</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>{{ __('Logout') }}</v-list-item-title>
              </v-list-item-content>
            </v-list-item>
            <v-list-item @click="$emit('about')">
              <v-list-item-icon>
                <v-icon>mdi-information-outline</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>{{ __('About') }}</v-list-item-title>
              </v-list-item-content>
            </v-list-item>
            <v-list-item v-if="tokenWorkflowEnabled" @click="$emit('open-relay-settings')">
              <v-list-item-icon>
                <v-icon>mdi-lan-connect</v-icon>
              </v-list-item-icon>
              <v-list-item-content>
                <v-list-item-title>{{ __('Relay Settings') }}</v-list-item-title>
              </v-list-item-content>
            </v-list-item>
            <template v-if="showAdminRoleTesting">
              <v-divider class="my-0"></v-divider>
              <v-subheader>{{ __('Admin Test Role') }}</v-subheader>
              <v-list-item>
                <v-list-item-content>
                  <v-select
                    :value="adminTestRole"
                    :items="adminTestRoleOptions"
                    dense
                    outlined
                    hide-details
                    @change="$emit('admin-role-change', $event)"
                  ></v-select>
                </v-list-item-content>
              </v-list-item>
            </template>
          </v-list-item-group>
        </v-list>
      </v-card>
    </v-menu>
  </div>
</template>

<script>
export default {
  props: {
    activeItem: {
      type: Number,
      default: 0,
    },
    menuItem: {
      type: Number,
      default: 0,
    },
    posProfile: {
      type: Object,
      default: () => ({}),
    },
    lastInvoice: {
      type: String,
      default: '',
    },
    canShowCloseShiftAction: Boolean,
    tokenWorkflowEnabled: Boolean,
    showAdminRoleTesting: Boolean,
    adminTestRole: {
      type: String,
      default: '',
    },
    adminTestRoleOptions: {
      type: Array,
      default: () => [],
    },
  },
};
</script>
