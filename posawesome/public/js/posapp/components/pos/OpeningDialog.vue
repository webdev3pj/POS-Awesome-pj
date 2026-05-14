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
                <v-text-field
                  v-if="token_workflow_enabled"
                  :label="frappe._('Company')"
                  v-model="company"
                  readonly
                  outlined
                  dense
                  hide-details="auto"
                  required
                ></v-text-field>
                <v-autocomplete
                  v-else
                  :items="companies"
                  :label="frappe._('Company')"
                  v-model="company"
                  required
                ></v-autocomplete>
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-if="token_workflow_enabled"
                  :label="frappe._('POS Profile')"
                  v-model="pos_profile"
                  readonly
                  outlined
                  dense
                  hide-details="auto"
                  required
                ></v-text-field>
                <v-autocomplete
                  v-else
                  :items="pos_profiles"
                  :label="frappe._('POS Profile')"
                  v-model="pos_profile"
                  required
                ></v-autocomplete>
              </v-col>
              <v-col cols="12" v-if="token_workflow_enabled && detected_role">
                <v-alert type="info" dense outlined>
                  <strong>Role:</strong> {{ detected_role_display }}
                </v-alert>
              </v-col>
              <v-col cols="12" v-if="token_workflow_enabled && admin_role_testing_enabled">
                <v-select
                  v-model="detected_role"
                  :items="admin_test_role_options"
                  :label="__('Administrator Test Role')"
                  dense
                  outlined
                  hide-details="auto"
                  @change="set_admin_test_role"
                ></v-select>
              </v-col>
              <v-col cols="12" v-if="token_workflow_enabled && role_error">
                <v-alert type="error" dense>
                  {{ role_error }}
                </v-alert>
              </v-col>
              <v-col cols="12" v-if="token_workflow_enabled && is_non_cash_role_session">
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
import { OPERATIONAL_ROLES, resolveCurrentRole, setAdminTestRole } from '../../utils/posRole';
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
      token_workflow_enabled: false,
      // Role derived from ERPNext user roles (not user-selectable)
      detected_role: '',
      role_error: '',
      admin_role_testing_enabled: false,
      admin_test_role_options: OPERATIONAL_ROLES,
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
      if (!this.token_workflow_enabled) return false;
      const role = (this.detected_role || '').trim();
      if (!role) return false;
      return role !== 'cline-Cashier';
    },
    requires_cash_opening() {
      return !this.is_non_cash_role_session;
    },
    dialog_title() {
      if (!this.token_workflow_enabled) {
        return __('Create POS Opening Shift');
      }
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
            (r.message.companies || []).forEach((element) => {
              vm.companies.push(element.name);
            });
            vm.company = r.message.default_company || vm.companies[0] || "";
            vm.pos_profiles_data = r.message.pos_profiles_data || [];
            vm.pos_profiles = vm.pos_profiles_data.map((element) => element.name);
            vm.pos_profile = r.message.default_pos_profile || vm.pos_profiles[0] || "";
            vm.payments_method_data = r.message.payments_method;
            vm.token_workflow_enabled = parseInt(r.message.token_workflow_enabled || 0, 10) === 1;
            // Get role from user's ERPNext roles (derived, not user-selected)
            vm.admin_role_testing_enabled =
              vm.token_workflow_enabled && parseInt(r.message.admin_role_testing_enabled || 0, 10) === 1;
            try {
              if (vm.admin_role_testing_enabled) {
                localStorage.setItem("posa_admin_role_testing_enabled", "1");
              } else {
                localStorage.removeItem("posa_admin_role_testing_enabled");
              }
            } catch (e) {}
            vm.detected_role = r.message.user_role || '';
            vm.role_error = r.message.role_error || '';
            if (vm.admin_role_testing_enabled) {
              vm.detected_role = resolveCurrentRole({ fallback: vm.detected_role || "cline-Supervisor" });
              vm.role_error = "";
            }
            try {
              const relayKey = String(r.message.relay_client_auth_key || "").trim();
              if (relayKey) {
                localStorage.setItem("posa_relay_client_key", relayKey);
              } else if (parseInt(r.message.relay_client_auth_required || 0, 10) !== 1) {
                // Only clear when backend explicitly indicates auth is not required.
                localStorage.removeItem("posa_relay_client_key");
              }
            } catch (e) {}
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
      if (this.token_workflow_enabled) {
        // Store role in localStorage for token workflow sessions only.
        if (this.admin_role_testing_enabled) {
          setAdminTestRole(this.detected_role);
        } else {
          localStorage.setItem('pos_current_role', this.detected_role);
        }
      } else {
        localStorage.removeItem('pos_current_role');
      }
      const method = this.token_workflow_enabled && !this.requires_cash_opening
        ? 'posawesome.posawesome.api.posapp.bootstrap_pos_session'
        : 'posawesome.posawesome.api.posapp.create_opening_voucher';
      const args = method === 'posawesome.posawesome.api.posapp.create_opening_voucher'
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
    set_admin_test_role(role) {
      const selected = setAdminTestRole(role);
      if (selected) {
        this.detected_role = selected;
        this.role_error = "";
      }
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
