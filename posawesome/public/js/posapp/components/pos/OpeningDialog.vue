<template>
  <v-row justify="center">
    <v-dialog v-model="isOpen" persistent max-width="600px">
      <!-- <template v-slot:activator="{ on, attrs }">
        <v-btn color="primary" dark v-bind="attrs" v-on="on">Open Dialog</v-btn>
      </template>-->
        <v-card>
        <v-card-title>
          <span class="headline primary--text">{{
            dialog_title
          }}</span>
        </v-card-title>
        <v-card-text>
          <v-container>
            <v-row>
              <v-col cols="12">
                <v-autocomplete
                  :items="companies"
                  :label="frappe._('Company')"
                  v-model="company"
                  required
                ></v-autocomplete>
              </v-col>
              <v-col cols="12">
                <v-autocomplete
                  :items="pos_profiles"
                  :label="frappe._('POS Profile')"
                  v-model="pos_profile"
                  required
                ></v-autocomplete>
              </v-col>
              <v-col cols="12" v-if="detected_role">
                <v-alert type="info" dense outlined>
                  <strong>Role:</strong> {{ detected_role_display }}
                </v-alert>
              </v-col>
              <v-col cols="12" v-if="role_error">
                <v-alert type="error" dense>
                  {{ role_error }}
                </v-alert>
              </v-col>
              <v-col cols="12" v-if="is_non_cash_role_session">
                <v-alert type="info" dense outlined>
                  {{
                    __(
                      'Cash opening/closing is cashier-only. You can start a non-cash POS session to create orders and tokens.'
                    )
                  }}
                </v-alert>
              </v-col>
              <v-col cols="12" v-if="requires_cash_opening">
                <template>
                  <v-data-table
                    :headers="payments_methods_headers"
                    :items="payments_methods"
                    item-key="mode_of_payment"
                    class="elevation-1"
                    :items-per-page="itemsPerPage"
                    hide-default-footer
                  >
                    <template v-slot:item.amount="props">
                      <v-edit-dialog :return-value.sync="props.item.amount">
                        {{ currencySymbol(props.item.currency) }}
                        {{ formtCurrency(props.item.amount) }}
                        <template v-slot:input>
                          <v-text-field
                            v-model="props.item.amount"
                            :rules="[max25chars]"
                            :label="frappe._('Edit')"
                            single-line
                            counter
                            type="number"
                          ></v-text-field>
                        </template>
                      </v-edit-dialog>
                    </template>
                  </v-data-table>
                </template>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="error" dark @click="go_desk">Cancel</v-btn>
          <v-btn
            color="success"
            :disabled="is_loading"
            dark
            @click="submit_dialog"
            >Submit</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-row>
</template>

<script>
import { evntBus } from '../../bus';
import format from '../../format';
export default {
  mixins: [format],
  props: ['dialog'],
  data() {
    return {
      isOpen: this.dialog ? this.dialog : false,
      dialog_data: {},
      is_loading: false,
      companies: [],
      company: '',
      pos_profiles_data: [],
      pos_profiles: [],
      pos_profile: '',
      // Role derived from ERPNext user roles (not user-selectable)
      detected_role: '',
      role_error: '',
      payments_method_data: [],
      payments_methods: [],
      payments_methods_headers: [
        {
          text: __('Mode of Payment'),
          align: 'start',
          sortable: false,
          value: 'mode_of_payment',
        },
        {
          text: __('Opening Amount'),
          value: 'amount',
          align: 'center',
          sortable: false,
        },
      ],
      itemsPerPage: 100,
      max25chars: (v) => v.length <= 12 || 'Input too long!', // TODO : should validate as number
      pagination: {},
      snack: false, // TODO : need to remove
      snackColor: '', // TODO : need to remove
      snackText: '', // TODO : need to remove
    };
  },
  watch: {
    company(val) {
      this.pos_profiles = [];
      this.pos_profiles_data.forEach((element) => {
        if (element.company === val) {
          this.pos_profiles.push(element.name);
        }
        if (this.pos_profiles.length) {
          this.pos_profile = this.pos_profiles[0];
        } else {
          this.pos_profile = '';
        }
      });
    },
    pos_profile(val) {
      this.payments_methods = [];
      this.payments_method_data.forEach((element) => {
        if (element.parent === val) {
          this.payments_methods.push({
            mode_of_payment: element.mode_of_payment,
            amount: 0,
            currency: element.currency,
          });
        }
      });
    },
  },
  computed: {
    // Display role without "cline-" prefix
    detected_role_display() {
      if (this.detected_role && this.detected_role.startsWith('cline-')) {
        return this.detected_role.substring(6);
      }
      return this.detected_role;
    },
    is_non_cash_role_session() {
      const role = (this.detected_role || '').trim();
      if (!role) return false;
      return role !== 'cline-Cashier';
    },
    requires_cash_opening() {
      return !this.is_non_cash_role_session;
    },
    dialog_title() {
      return this.requires_cash_opening
        ? __('Create POS Opening Shift')
        : __('Start POS Session');
    },
  },
  methods: {
    close_opening_dialog() {
      evntBus.$emit('close_opening_dialog');
    },
    get_opening_dialog_data() {
      const vm = this;
      frappe.call({
        method: 'posawesome.posawesome.api.posapp.get_opening_dialog_data',
        args: {},
        callback: function (r) {
          if (r.message) {
            r.message.companies.forEach((element) => {
              vm.companies.push(element.name);
            });
            vm.company = vm.companies[0];
            vm.pos_profiles_data = r.message.pos_profiles_data;
            vm.payments_method_data = r.message.payments_method;
            // Get role from user's ERPNext roles (derived, not user-selected)
            vm.detected_role = r.message.user_role || '';
            vm.role_error = r.message.role_error || '';
          }
        },
      });
    },
    submit_dialog() {
      if (!this.company || !this.pos_profile) {
        frappe.msgprint(__('Please select Company and POS Profile'));
        return;
      }
      if (this.requires_cash_opening && !this.payments_methods.length) {
        frappe.msgprint(__('Please enter opening amounts or configure payment methods for the POS Profile.'));
        return;
      }
      if (this.role_error) {
        frappe.msgprint(this.role_error);
        return;
      }
      this.is_loading = true;
      const vm = this;
      // Store role in localStorage for session
      localStorage.setItem('pos_current_role', this.detected_role);
      const method = this.requires_cash_opening
        ? 'posawesome.posawesome.api.posapp.create_opening_voucher'
        : 'posawesome.posawesome.api.posapp.bootstrap_pos_session';
      const args = this.requires_cash_opening
        ? {
            pos_profile: this.pos_profile,
            company: this.company,
            balance_details: this.payments_methods,
          }
        : {
            pos_profile: this.pos_profile,
            company: this.company,
          };
      return frappe
        .call(method, args)
        .then((r) => {
          if (r.message) {
            evntBus.$emit('register_pos_data', r.message);
            evntBus.$emit('set_company', r.message.company);
            vm.close_opening_dialog();
            vm.is_loading = false;
          }
        })
        .catch(() => {
          vm.is_loading = false;
        });
    },
    go_desk() {
      frappe.set_route('/');
      location.reload();
    },
  },
  created: function () {
    this.$nextTick(function () {
      this.get_opening_dialog_data();
    });
  },
};
</script>
