<template>
  <div class="pos-shell">
    <ClosingDialog></ClosingDialog>
    <Drafts></Drafts>
    <SalesOrders></SalesOrders>
    <Quotations></Quotations>
    <Returns></Returns>
    <NewAddress></NewAddress>
    <MpesaPayments></MpesaPayments>
    <Variants></Variants>
    <WorkflowTicketRail
      v-if="!dialog"
      :pos_profile="pos_profile"
      :pos_opening_shift="pos_opening_shift"
      :business_date="session_business_date"
    ></WorkflowTicketRail>
    <OpeningDialog v-if="dialog" :dialog="dialog"></OpeningDialog>
    <v-row v-show="!dialog">
      <template v-if="is_fulfillment_role">
        <v-col cols="12" class="pos">
          <FulfillmentWorkspace
            :pos_profile="pos_profile"
            :pos_opening_shift="pos_opening_shift"
            :business_date="session_business_date"
            :current_role="current_role"
          ></FulfillmentWorkspace>
        </v-col>
      </template>
      <template v-else>
        <v-col
          v-show="!payment && !offers && !coupons"
          xl="5"
          lg="5"
          md="5"
          sm="5"
          cols="12"
          class="pos pr-0"
        >
          <ItemsSelector></ItemsSelector>
        </v-col>
        <v-col
          v-show="offers"
          xl="5"
          lg="5"
          md="5"
          sm="5"
          cols="12"
          class="pos pr-0"
        >
          <PosOffers></PosOffers>
        </v-col>
        <v-col
          v-show="coupons"
          xl="5"
          lg="5"
          md="5"
          sm="5"
          cols="12"
          class="pos pr-0"
        >
          <PosCoupons></PosCoupons>
        </v-col>
        <v-col
          v-show="payment"
          xl="5"
          lg="5"
          md="5"
          sm="5"
          cols="12"
          class="pos pr-0"
        >
          <Payments></Payments>
        </v-col>

        <v-col xl="7" lg="7" md="7" sm="7" cols="12" class="pos">
          <Invoice></Invoice>
        </v-col>
      </template>
    </v-row>
  </div>
</template>

<script>
import { evntBus } from '../../bus';
import ItemsSelector from './catalog/ItemsSelector.vue';
import Invoice from './checkout/Invoice.vue';
import OpeningDialog from './dialogs/OpeningDialog.vue';
import Payments from './checkout/Payments.vue';
import PosOffers from './catalog/PosOffers.vue';
import PosCoupons from './catalog/PosCoupons.vue';
import Drafts from './documents/Drafts.vue';
import SalesOrders from "./documents/SalesOrders.vue";
import Quotations from "./documents/Quotations.vue";
import ClosingDialog from './dialogs/ClosingDialog.vue';
import NewAddress from './checkout/customer/NewAddress.vue';
import Variants from './catalog/Variants.vue';
import Returns from './documents/Returns.vue';
import MpesaPayments from './checkout/Mpesa-Payments.vue';
import WorkflowTicketRail from './workflow/WorkflowTicketRail.vue';
import FulfillmentWorkspace from './fulfillment/FulfillmentWorkspace.vue';
import { resolveCurrentRole } from '../../utils/posRole';

export default {
  data: function () {
    return {
      dialog: false,
      pos_profile: '',
      pos_opening_shift: '',
      session_business_date: '',
      payment: false,
      offers: false,
      coupons: false,
      current_role: '',
    };
  },

  components: {
    ItemsSelector,
    Invoice,
    OpeningDialog,
    Payments,
    Drafts,
    ClosingDialog,

    Returns,
    PosOffers,
    PosCoupons,
    NewAddress,
    Variants,
    MpesaPayments,
    SalesOrders,
    Quotations,
    WorkflowTicketRail,
    FulfillmentWorkspace,
  },

  computed: {
    token_workflow_enabled() {
      return parseInt((this.pos_profile && this.pos_profile.custom_have_token) || 0, 10) === 1;
    },
    is_fulfillment_role() {
      return (
        this.token_workflow_enabled &&
        ['cline-Picker', 'cline-Dispatch', 'cline-Supervisor'].includes(
          (this.current_role || '').trim()
        )
      );
    },
  },

  methods: {
    get_current_role() {
      return resolveCurrentRole();
    },
    refresh_current_role() {
      this.current_role = this.get_current_role();
    },
    check_opening_entry() {
      return frappe
        .call('posawesome.posawesome.api.posapp.check_opening_shift', {
          user: frappe.session.user,
        })
        .then((r) => {
          this.refresh_current_role();
          if (r.message) {
            this.pos_profile = r.message.pos_profile;
            this.pos_opening_shift = r.message.pos_opening_shift;
            this.session_business_date =
              r.message.session_business_date ||
              (r.message.pos_opening_shift && r.message.pos_opening_shift.posting_date) ||
              frappe.datetime.nowdate();
            this.get_offers(this.pos_profile.name);
            evntBus.$emit('register_pos_profile', r.message);
            evntBus.$emit('set_company', r.message.company);
            console.info('LoadPosProfile');
          } else {
            this.create_opening_voucher();
          }
        });
    },
    create_opening_voucher() {
      this.dialog = true;
    },
    get_closing_data() {
      if (!this.pos_opening_shift || !this.pos_opening_shift.name) {
        evntBus.$emit('show_mesage', {
          text: __('Close Shift is only available for a cashier opening shift session.'),
          color: 'warning',
        });
        return Promise.resolve();
      }
      return frappe
        .call(
          'posawesome.posawesome.doctype.pos_closing_shift.pos_closing_shift.make_closing_shift_from_opening',
          {
            opening_shift: this.pos_opening_shift,
          }
        )
        .then((r) => {
          if (r.message) {
            evntBus.$emit('open_ClosingDialog', r.message);
          } else {
            // console.log(r);
          }
        });
    },
    submit_closing_pos(data) {
      frappe
        .call(
          'posawesome.posawesome.doctype.pos_closing_shift.pos_closing_shift.submit_closing_shift',
          {
            closing_shift: data,
          }
        )
        .then((r) => {
          if (r.message) {
            evntBus.$emit('show_mesage', {
              text: `POS Shift Closed`,
              color: 'success',
            });
            evntBus.$emit('closing_pos_submitted');
            this.check_opening_entry();
          } else {
            evntBus.$emit('closing_pos_submit_failed');
            console.log(r);
          }
        })
        .catch((e) => {
          evntBus.$emit('closing_pos_submit_failed');
          evntBus.$emit('show_mesage', {
            text: (e && e.message) || __('Failed to close POS shift. Please try again.'),
            color: 'error',
          });
        });
    },
    get_offers(pos_profile) {
      return frappe
        .call('posawesome.posawesome.api.posapp.get_offers', {
          profile: pos_profile,
        })
        .then((r) => {
          if (r.message) {
            console.info('LoadOffers');
            evntBus.$emit('set_offers', r.message);
          }
        });
    },
    get_pos_setting() {
      frappe.db.get_doc('POS Settings', undefined).then((doc) => {
        evntBus.$emit('set_pos_settings', doc);
      });
    },
  },

  mounted: function () {
    this.$nextTick(function () {
      this.refresh_current_role();
      this.check_opening_entry();
      this.get_pos_setting();
      this._handle_storage_event = (event) => {
        if (!event || event.key === 'pos_current_role') {
          this.refresh_current_role();
        }
      };
      if (typeof window !== 'undefined' && window.addEventListener) {
        window.addEventListener('storage', this._handle_storage_event);
      }
      evntBus.$on('close_opening_dialog', () => {
        this.refresh_current_role();
        this.dialog = false;
      });
      evntBus.$on('register_pos_data', (data) => {
        this.refresh_current_role();
        this.pos_profile = data.pos_profile;
        this.get_offers(this.pos_profile.name);
        this.pos_opening_shift = data.pos_opening_shift;
        this.session_business_date =
          data.session_business_date ||
          (data.pos_opening_shift && data.pos_opening_shift.posting_date) ||
          frappe.datetime.nowdate();
        evntBus.$emit('register_pos_profile', data);
        console.info('LoadPosProfile');
      });
      evntBus.$on('show_payment', (data) => {
        this.payment = true ? data === 'true' : false;
        this.offers = false ? data === 'true' : false;
        this.coupons = false ? data === 'true' : false;
      });
      evntBus.$on('show_offers', (data) => {
        this.offers = true ? data === 'true' : false;
        this.payment = false ? data === 'true' : false;
        this.coupons = false ? data === 'true' : false;
      });
      evntBus.$on('show_coupons', (data) => {
        this.coupons = true ? data === 'true' : false;
        this.offers = false ? data === 'true' : false;
        this.payment = false ? data === 'true' : false;
      });
      evntBus.$on('open_closing_dialog', () => {
        this.get_closing_data();
      });
      evntBus.$on('submit_closing_pos', (data) => {
        this.submit_closing_pos(data);
      });
      evntBus.$on('pos_role_changed', () => {
        this.refresh_current_role();
      });
    });
  },
  beforeDestroy() {
    evntBus.$off('close_opening_dialog');
    evntBus.$off('register_pos_data');
    evntBus.$off('LoadPosProfile');
    evntBus.$off('show_offers');
    evntBus.$off('show_coupons');
    evntBus.$off('open_closing_dialog');
    evntBus.$off('submit_closing_pos');
    evntBus.$off('pos_role_changed');
    if (typeof window !== 'undefined' && window.removeEventListener && this._handle_storage_event) {
      window.removeEventListener('storage', this._handle_storage_event);
    }
  },
};
</script>

<style scoped>
.pos-shell {
  padding: 8px 10px 10px;
  background: #f4f7fb;
}

@media (max-width: 959px) {
  .pos-shell {
    padding: 6px;
  }
}
</style>
