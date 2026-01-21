<template>
  <div fluid class="mt-2">
    <ClosingDialog></ClosingDialog>
    <Drafts></Drafts>
    <SalesOrders></SalesOrders>
    <Returns></Returns>
    <NewAddress></NewAddress>
    <MpesaPayments></MpesaPayments>
    <Variants></Variants>
    <TokenDialog></TokenDialog>
    <CashierMode></CashierMode>
    <PendingTokensSidebar></PendingTokensSidebar>
    <OpeningDialog v-if="dialog" :dialog="dialog"></OpeningDialog>
    <v-row v-show="!dialog">
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
    </v-row>
  </div>
</template>

<script>
import { evntBus } from '../../bus';
import ItemsSelector from './ItemsSelector.vue';
import Invoice from './Invoice.vue';
import OpeningDialog from './OpeningDialog.vue';
import Payments from './Payments.vue';
import PosOffers from './PosOffers.vue';
import PosCoupons from './PosCoupons.vue';
import Drafts from './Drafts.vue';
import SalesOrders from "./SalesOrders.vue";
import ClosingDialog from './ClosingDialog.vue';
import NewAddress from './NewAddress.vue';
import Variants from './Variants.vue';
import Returns from './Returns.vue';
import MpesaPayments from './Mpesa-Payments.vue';
import TokenDialog from './TokenDialog.vue';
import CashierMode from './CashierMode.vue';
import PendingTokensSidebar from './PendingTokensSidebar.vue';

export default {
  data: function () {
    return {
      dialog: false,
      pos_profile: '',
      pos_opening_shift: '',
      payment: false,
      offers: false,
      coupons: false,
      user_roles: [],
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
    TokenDialog,
    CashierMode,
    PendingTokensSidebar,
  },
  
  computed: {
    isSalesAssociateOnly() {
      // Returns true if user has POS Sales Associate role but NOT POS Cashier
      return this.user_roles.includes("POS Sales Associate") && 
             !this.user_roles.includes("POS Cashier");
    }
  },

  methods: {
    async fetch_user_roles() {
      // Fetch user roles first
      const response = await frappe.call({
        method: "posawesome.posawesome.api.posapp.get_current_user_roles",
        args: {}
      });
      if (response.message) {
        this.user_roles = response.message;
      }
    },
    
    check_opening_entry() {
      return frappe
        .call('posawesome.posawesome.api.posapp.check_opening_shift', {
          user: frappe.session.user,
        })
        .then((r) => {
          if (r.message) {
            this.pos_profile = r.message.pos_profile;
            this.pos_opening_shift = r.message.pos_opening_shift;
            this.get_offers(this.pos_profile.name);
            evntBus.$emit('register_pos_profile', r.message);
            evntBus.$emit('set_company', r.message.company);
            console.info('LoadPosProfile');
          } else {
            // Check if user is a Sales Associate - they don't need opening shift
            if (this.isSalesAssociateOnly) {
              this.load_pos_profile_for_sales_associate();
            } else {
              this.create_opening_voucher();
            }
          }
        });
    },
    
    async load_pos_profile_for_sales_associate() {
      // Sales Associates don't need an opening shift
      // Just load the POS Profile directly
      const response = await frappe.call({
        method: 'posawesome.posawesome.api.posapp.get_opening_dialog_data',
        args: {}
      });
      
      if (response.message && response.message.pos_profiles_data && response.message.pos_profiles_data.length > 0) {
        // Get the first available POS Profile or the one assigned to user
        const pos_profile_name = response.message.pos_profiles_data[0].name;
        
        // Fetch full POS Profile data
        const profile_response = await frappe.call({
          method: 'frappe.client.get',
          args: {
            doctype: 'POS Profile',
            name: pos_profile_name
          }
        });
        
        if (profile_response.message) {
          this.pos_profile = profile_response.message;
          this.get_offers(this.pos_profile.name);
          
          // Emit the profile data without opening shift
          const data = {
            pos_profile: profile_response.message,
            pos_opening_shift: null,
            company: { name: profile_response.message.company },
            stock_settings: { allow_negative_stock: '0' }
          };
          
          evntBus.$emit('register_pos_profile', data);
          evntBus.$emit('set_company', data.company);
          console.info('LoadPosProfile for Sales Associate (no opening shift)');
        }
      }
    },
    
    create_opening_voucher() {
      this.dialog = true;
    },
    get_closing_data() {
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
            this.check_opening_entry();
          } else {
            console.log(r);
          }
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
    this.$nextTick(async function () {
      // Fetch user roles first before checking opening entry
      await this.fetch_user_roles();
      this.check_opening_entry();
      this.get_pos_setting();
      evntBus.$on('close_opening_dialog', () => {
        this.dialog = false;
      });
      evntBus.$on('register_pos_data', (data) => {
        this.pos_profile = data.pos_profile;
        this.get_offers(this.pos_profile.name);
        this.pos_opening_shift = data.pos_opening_shift;
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
  },
};
</script>

<style scoped></style>
