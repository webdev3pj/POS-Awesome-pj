<template>
  <div>
    <v-dialog v-model="cancel_dialog" max-width="330">
      <v-card>
        <v-card-title class="text-h5">
          <span class="headline primary--text">{{
            __("Cancel Current Invoice ?")
          }}</span>
        </v-card-title>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="error" @click="cancel_invoice">
            {{ __("Cancel") }}
          </v-btn>
          <v-btn color="warning" @click="cancel_dialog = false">
            {{ __("Back") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-card
      style="max-height: 70vh; height: 70vh"
      class="cards my-0 py-0 mt-3 grey lighten-5"
    >
      <v-row align="center" class="items px-2 py-1">
        <v-col
          v-if="pos_profile.posa_allow_sales_order"
          cols="9"
          class="pb-2 pr-0"
        >
          <Customer></Customer>
        </v-col>
        <v-col
          v-if="!pos_profile.posa_allow_sales_order"
          cols="12"
          class="pb-2"
        >
          <Customer></Customer>
        </v-col>
        <v-col v-if="pos_profile.posa_allow_sales_order" cols="3" class="pb-2">
          <v-select
            dense
            hide-details
            outlined
            color="primary"
            background-color="white"
            :items="invoiceTypes"
            :label="frappe._('Type')"
            v-model="invoiceType"
            :disabled="invoiceType == 'Return' || is_sales_associate_role"
          ></v-select>
        </v-col>
      </v-row>

      <v-row
        align="center"
        class="items px-2 py-1 mt-0 pt-0"
        v-if="pos_profile.posa_use_delivery_charges"
      >
        <v-col cols="8" class="pb-0 mb-0 pr-0 pt-0">
          <v-autocomplete
            dense
            clearable
            auto-select-first
            outlined
            color="primary"
            :label="frappe._('Delivery Charges')"
            v-model="selcted_delivery_charges"
            :items="delivery_charges"
            item-text="name"
            return-object
            background-color="white"
            :no-data-text="__('Charges not found')"
            hide-details
            :filter="deliveryChargesFilter"
            :disabled="readonly"
            @change="update_delivery_charges()"
          >
            <template v-slot:item="data">
              <template>
                <v-list-item-content>
                  <v-list-item-title
                    class="primary--text subtitle-1"
                    v-html="data.item.name"
                  ></v-list-item-title>
                  <v-list-item-subtitle
                    v-html="`Rate: ${data.item.rate}`"
                  ></v-list-item-subtitle>
                </v-list-item-content>
              </template>
            </template>
          </v-autocomplete>
        </v-col>
        <v-col cols="4" class="pb-0 mb-0 pt-0">
          <v-text-field
            dense
            outlined
            color="primary"
            :label="frappe._('Delivery Charges Rate')"
            background-color="white"
            hide-details
            :value="formtCurrency(delivery_charges_rate)"
            :prefix="currencySymbol(pos_profile.currency)"
            disabled
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row
        align="center"
        class="items px-2 py-1 mt-0 pt-0"
        v-if="pos_profile.posa_allow_change_posting_date"
      >
        <v-col
          v-if="pos_profile.posa_allow_change_posting_date"
          cols="4"
          class="pb-2"
        >
          <v-menu
            ref="invoice_posting_date"
            v-model="invoice_posting_date"
            :close-on-content-click="false"
            transition="scale-transition"
            dense
          >
            <template v-slot:activator="{ on, attrs }">
              <v-text-field
                v-model="posting_date"
                :label="frappe._('Posting Date')"
                readonly
                outlined
                dense
                background-color="white"
                clearable
                color="primary"
                hide-details
                v-bind="attrs"
                v-on="on"
              ></v-text-field>
            </template>
            <v-date-picker
              v-model="posting_date"
              no-title
              scrollable
              color="primary"
              :min="
                frappe.datetime.add_days(frappe.datetime.now_date(true), -7)
              "
              :max="frappe.datetime.add_days(frappe.datetime.now_date(true), 7)"
              @input="invoice_posting_date = false"
            >
            </v-date-picker>
          </v-menu>
        </v-col>
      </v-row>

      <div class="my-0 py-0 overflow-y-auto" style="max-height: 60vh">
        <template @mouseover="style = 'cursor: pointer'">
          <v-data-table
            :headers="items_headers"
            :items="items"
            :single-expand="singleExpand"
            :expanded.sync="expanded"
            show-expand
            item-key="posa_row_id"
            class="elevation-1"
            :items-per-page="itemsPerPage"
            hide-default-footer
          >
            <template v-slot:item.qty="{ item }">{{
              formtFloat(item.qty, 2)
            }}</template>
            <template v-slot:item.rate="{ item }"
              >{{ currencySymbol(pos_profile.currency) }}
              {{ formtCurrency(item.rate, 2) }}</template
            >
            <template v-slot:item.amount="{ item }"
              >{{ currencySymbol(pos_profile.currency) }}
              {{
                formtCurrency(
                  flt(item.qty, 2) *
                    flt(item.rate, 2)
                )
              }}</template
            >
            <template v-slot:item.posa_is_offer="{ item }">
              <v-simple-checkbox
                :value="!!item.posa_is_offer || !!item.posa_is_replace"
                disabled
              ></v-simple-checkbox>
            </template>

            <template v-slot:expanded-item="{ headers, item }">
              <td :colspan="headers.length" class="ma-0 pa-0">
                <v-row class="ma-0 pa-0">
                  <v-col cols="1">
                    <v-btn
                      :disabled="!!item.posa_is_offer || !!item.posa_is_replace"
                      icon
                      color="error"
                      @click.stop="remove_item(item)"
                    >
                      <v-icon>mdi-delete</v-icon>
                    </v-btn>
                  </v-col>
                  <v-spacer></v-spacer>
                  <v-col cols="1">
                    <v-btn
                      :disabled="!!item.posa_is_offer || !!item.posa_is_replace"
                      icon
                      color="secondary"
                      @click.stop="subtract_one(item)"
                    >
                      <v-icon>mdi-minus-circle-outline</v-icon>
                    </v-btn>
                  </v-col>
                  <v-col cols="1">
                    <v-btn
                      :disabled="!!item.posa_is_offer || !!item.posa_is_replace"
                      icon
                      color="secondary"
                      @click.stop="add_one(item)"
                    >
                      <v-icon>mdi-plus-circle-outline</v-icon>
                    </v-btn>
                  </v-col>
                </v-row>
                <v-row class="ma-0 pa-0">
                  <v-col cols="4">
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Item Code')"
                      background-color="white"
                      hide-details
                      v-model="item.item_code"
                      disabled
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('QTY')"
                      background-color="white"
                      hide-details
                      :value="formtFloat(item.qty, 2)"
                      @change="updateItemQty(item, $event)"
                      :rules="[isNumber]"
                      :disabled="!!item.posa_is_offer || !!item.posa_is_replace"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-select
                      dense
                      background-color="white"
                      :label="frappe._('UOM')"
                      v-model="item.uom"
                      :items="item.item_uoms"
                      outlined
                      item-text="uom"
                      item-value="uom"
                      hide-details
                      @change="calc_uom(item, $event)"
                      :disabled="
                        !!invoice_doc.is_return ||
                        !!item.posa_is_offer ||
                        !!item.posa_is_replace
                      "
                    >
                    </v-select>
                  </v-col>
                  <v-col cols="4">
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Rate')"
                      background-color="white"
                      hide-details
                      :prefix="currencySymbol(pos_profile.currency)"
                      :value="formtCurrency(item.rate, 2)"
                      @change="updateItemRate(item, $event)"
                      :rules="[isNumber]"
                      id="rate"
                      :disabled="
                        !!item.posa_is_offer ||
                        !!item.posa_is_replace ||
                        !!item.posa_offer_applied ||
                        !pos_profile.posa_allow_user_to_edit_rate ||
                        !!invoice_doc.is_return
                          ? true
                          : false
                      "
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Discount Percentage')"
                      background-color="white"
                      hide-details
                      :value="formtFloat(item.discount_percentage)"
                      @change="
                        [
                          setFormatedCurrency(
                            item,
                            'discount_percentage',
                            null,
                            true,
                            $event
                          ),
                          calc_prices(item, $event, 'discount_percentage'),
                        ]
                      "
                      :rules="[isNumber]"
                      id="discount_percentage"
                      :disabled="
                        !!item.posa_is_offer ||
                        !!item.posa_is_replace ||
                        item.posa_offer_applied ||
                        !pos_profile.posa_allow_user_to_edit_item_discount ||
                        !!invoice_doc.is_return
                          ? true
                          : false
                      "
                      suffix="%"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Discount Amount')"
                      background-color="white"
                      hide-details
                      :value="formtCurrency(item.discount_amount)"
                      :rules="[isNumber]"
                      @change="
                        [
                          setFormatedCurrency(
                            item,
                            'discount_amount',
                            null,
                            true,
                            $event
                          ),
                          ,
                          calc_prices(item, $event, 'discount_amount'),
                        ]
                      "
                      :prefix="currencySymbol(pos_profile.currency)"
                      id="discount_amount"
                      :disabled="
                        !!item.posa_is_offer ||
                        !!item.posa_is_replace ||
                        !!item.posa_offer_applied ||
                        !pos_profile.posa_allow_user_to_edit_item_discount ||
                        !!invoice_doc.is_return
                          ? true
                          : false
                      "
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Price list Rate')"
                      background-color="white"
                      hide-details
                      :value="formtCurrency(item.price_list_rate)"
                      disabled
                      :prefix="currencySymbol(pos_profile.currency)"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Available QTY')"
                      background-color="white"
                      hide-details
                      :value="formtFloat(item.actual_qty)"
                      disabled
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Group')"
                      background-color="white"
                      hide-details
                      v-model="item.item_group"
                      disabled
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Stock QTY')"
                      background-color="white"
                      hide-details
                      :value="formtFloat(item.stock_qty)"
                      disabled
                    ></v-text-field>
                  </v-col>
                  <v-col cols="4">
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Stock UOM')"
                      background-color="white"
                      hide-details
                      v-model="item.stock_uom"
                      disabled
                    ></v-text-field>
                  </v-col>
                  <v-col align="center" cols="4" v-if="item.posa_offer_applied">
                    <v-checkbox
                      dense
                      :label="frappe._('Offer Applied')"
                      v-model="item.posa_offer_applied"
                      readonly
                      hide-details
                      class="shrink mr-2 mt-0"
                    ></v-checkbox>
                  </v-col>
                  <v-col
                    cols="4"
                    v-if="item.has_serial_no == 1 || item.serial_no"
                  >
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Serial No QTY')"
                      background-color="white"
                      hide-details
                      v-model="item.serial_no_selected_count"
                      type="number"
                      disabled
                    ></v-text-field>
                  </v-col>
                  <v-col
                    cols="12"
                    v-if="item.has_serial_no == 1 || item.serial_no"
                  >
                    <v-autocomplete
                      v-model="item.serial_no_selected"
                      :items="item.serial_no_data"
                      item-text="serial_no"
                      outlined
                      dense
                      chips
                      color="primary"
                      small-chips
                      :label="frappe._('Serial No')"
                      multiple
                      @change="set_serial_no(item)"
                    ></v-autocomplete>
                  </v-col>
                  <v-col
                    cols="4"
                    v-if="item.has_batch_no == 1 || item.batch_no"
                  >
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Batch No. Available QTY')"
                      background-color="white"
                      hide-details
                      :value="formtFloat(item.actual_batch_qty)"
                      disabled
                    ></v-text-field>
                  </v-col>
                  <v-col
                    cols="4"
                    v-if="item.has_batch_no == 1 || item.batch_no"
                  >
                    <v-text-field
                      dense
                      outlined
                      color="primary"
                      :label="frappe._('Batch No Expiry Date')"
                      background-color="white"
                      hide-details
                      v-model="item.batch_no_expiry_date"
                      disabled
                    ></v-text-field>
                  </v-col>
                  <v-col
                    cols="8"
                    v-if="item.has_batch_no == 1 || item.batch_no"
                  >
                    <v-autocomplete
                      v-model="item.batch_no"
                      :items="item.batch_no_data"
                      item-text="batch_no"
                      outlined
                      dense
                      color="primary"
                      :label="frappe._('Batch No')"
                      @change="set_batch_qty(item, $event)"
                    >
                      <template v-slot:item="data">
                        <template>
                          <v-list-item-content>
                            <v-list-item-title
                              v-html="data.item.batch_no"
                            ></v-list-item-title>
                            <v-list-item-subtitle
                              v-html="
                                `Available QTY  '${data.item.batch_qty}' - Expiry Date ${data.item.expiry_date}`
                              "
                            ></v-list-item-subtitle>
                          </v-list-item-content>
                        </template>
                      </template>
                    </v-autocomplete>
                  </v-col>
                  <v-col
                    cols="4"
                    v-if="
                      pos_profile.posa_allow_sales_order &&
                      invoiceType == 'Order'
                    "
                  >
                    <v-menu
                      ref="item_delivery_date"
                      v-model="item.item_delivery_date"
                      :close-on-content-click="false"
                      :return-value.sync="item.posa_delivery_date"
                      transition="scale-transition"
                      dense
                    >
                      <template v-slot:activator="{ on, attrs }">
                        <v-text-field
                          v-model="item.posa_delivery_date"
                          :label="frappe._('Delivery Date')"
                          readonly
                          outlined
                          dense
                          clearable
                          color="primary"
                          hide-details
                          v-bind="attrs"
                          v-on="on"
                        ></v-text-field>
                      </template>
                      <v-date-picker
                        v-model="item.posa_delivery_date"
                        no-title
                        scrollable
                        color="primary"
                        :min="frappe.datetime.now_date()"
                      >
                        <v-spacer></v-spacer>
                        <v-btn
                          text
                          color="primary"
                          @click="item.item_delivery_date = false"
                        >
                          Cancel
                        </v-btn>
                        <v-btn
                          text
                          color="primary"
                          @click="
                            [
                              $refs.item_delivery_date.save(
                                item.posa_delivery_date
                              ),
                              validate_due_date(item),
                            ]
                          "
                        >
                          OK
                        </v-btn>
                      </v-date-picker>
                    </v-menu>
                  </v-col>
                  <v-col
                    cols="8"
                    v-if="pos_profile.posa_display_additional_notes"
                  >
                    <v-textarea
                      class="pa-0"
                      outlined
                      dense
                      clearable
                      color="primary"
                      auto-grow
                      rows="1"
                      :label="frappe._('Additional Notes')"
                      v-model="item.posa_notes"
                      :value="item.posa_notes"
                    ></v-textarea>
                  </v-col>
                </v-row>
              </td>
            </template>
          </v-data-table>
        </template>
      </div>
    </v-card>
    <v-card class="cards mb-0 mt-3 py-0 grey lighten-5">
      <v-row no-gutters>
        <v-col cols="7">
          <v-row no-gutters class="pa-1 pt-9 pr-1">
            <v-col cols="6" class="pa-1">
              <v-text-field
                :value="formtFloat(total_qty)"
                :label="frappe._('Total Qty')"
                outlined
                dense
                readonly
                hide-details
                color="accent"
              ></v-text-field>
            </v-col>
            <v-col
              v-if="!pos_profile.posa_use_percentage_discount"
              cols="6"
              class="pa-1"
            >
              <v-text-field
                :value="formtCurrency(discount_amount)"
                @change="
                  setFormatedCurrency(
                    discount_amount,
                    'discount_amount',
                    null,
                    false,
                    $event
                  )
                "
                :rules="[isNumber]"
                :label="frappe._('Additional Discount')"
                ref="discount"
                outlined
                dense
                hide-details
                color="warning"
                :prefix="currencySymbol(pos_profile.currency)"
                :disabled="
                  !pos_profile.posa_allow_user_to_edit_additional_discount ||
                  discount_percentage_offer_name
                    ? true
                    : false
                "
              ></v-text-field>
            </v-col>
            <v-col
              v-if="pos_profile.posa_use_percentage_discount"
              cols="6"
              class="pa-1"
            >
              <v-text-field
                :value="formtFloat(additional_discount_percentage)"
                @change="
                  [
                    setFormatedFloat(
                      additional_discount_percentage,
                      'additional_discount_percentage',
                      null,
                      false,
                      $event
                    ),
                    update_discount_umount(),
                  ]
                "
                :rules="[isNumber]"
                :label="frappe._('Additional Discount %')"
                suffix="%"
                ref="percentage_discount"
                outlined
                dense
                color="warning"
                hide-details
                :disabled="
                  !pos_profile.posa_allow_user_to_edit_additional_discount ||
                  discount_percentage_offer_name
                    ? true
                    : false
                "
              ></v-text-field>
            </v-col>
            <v-col cols="6" class="pa-1 mt-2">
              <v-text-field
                :value="formtCurrency(total_items_discount_amount)"
                :prefix="currencySymbol(pos_profile.currency)"
                :label="frappe._('Items Discounts')"
                outlined
                dense
                color="warning"
                readonly
                hide-details
              ></v-text-field>
            </v-col>

            <v-col cols="6" class="pa-1 mt-2">
              <v-text-field
                :value="formtCurrency(subtotal)"
                :prefix="currencySymbol(pos_profile.currency)"
                :label="frappe._('Total')"
                outlined
                dense
                readonly
                hide-details
                color="success"
              ></v-text-field>
            </v-col>
          </v-row>
        </v-col>
        <v-col cols="5">
          <v-row no-gutters class="pa-1 pt-2 pl-0">
            <v-col v-if="show_held_button" cols="6" class="pa-1">
              <v-btn
                block
                class="pa-0"
                color="warning"
                dark
                @click="get_draft_invoices"
                >{{ __("Held") }}</v-btn
              >
            </v-col>
            <v-col
              v-if="pos_profile.custom_allow_select_sales_order === 1 && !is_sales_associate_role"
              cols="6"
              class="pa-1"
            >
              <v-btn
                block
                class="pa-0"
                color="info"
                dark
                @click="get_draft_orders"
                >{{ __("Select S.O") }}</v-btn
              >
            </v-col>
            <v-col
              v-if="can_use_quotation_actions"
              cols="6"
              class="pa-1"
            >
              <v-btn
                block
                class="pa-0"
                color="indigo"
                dark
                @click="save_quote"
              >
                {{ __("Save Quote") }}
              </v-btn>
            </v-col>
            <v-col
              v-if="can_use_quotation_actions"
              cols="6"
              class="pa-1"
            >
              <v-btn
                block
                class="pa-0"
                color="cyan darken-1"
                dark
                @click="get_draft_quotations"
              >
                {{ __("Select Quote") }}
              </v-btn>
            </v-col>
            <v-col v-if="show_return_button" cols="6" class="pa-1">
              <v-btn
                block
                class="pa-0"
                :class="{ 'disable-events': !pos_profile.posa_allow_return }"
                color="secondary"
                dark
                @click="open_returns"
                >{{ __("Return") }}</v-btn
              >
            </v-col>
            <v-col cols="6" class="pa-1">
              <v-btn
                block
                class="pa-0"
                color="error"
                dark
                @click="cancel_dialog = true"
                >{{ __("Cancel") }}</v-btn
              >
            </v-col>
            <v-col cols="6" class="pa-1">
              <v-btn
                block
                class="pa-0"
                color="accent"
                dark
                @click="handle_save_new"
                >{{ __("Save/New") }}</v-btn
              >
            </v-col>
            <v-col v-if="show_pay_button" class="pa-1">
              <v-btn
                block
                class="pa-0"
                color="success"
                @click="show_payment"
                dark
                :disabled="is_sales_associate_role"
                >{{ __("PAY") }}</v-btn
              >
            </v-col>
            <v-col
              v-if="pos_profile.posa_allow_print_draft_invoices"
              cols="6"
              class="pa-1"
            >
              <v-btn
                block
                class="pa-0"
                color="primary"
                @click="print_draft_invoice"
                dark
                >{{ __("Print Draft") }}</v-btn
              >
            </v-col>
          </v-row>
        </v-col>
      </v-row>
    </v-card>
  </div>
</template>

<script>
import { evntBus } from "../../bus";
import format from "../../format";
import Customer from "./Customer.vue";
import { resolveCurrentRole } from "../../utils/posRole";

export default {
  mixins: [format],
  data() {
    return {
      pos_profile: "",
      pos_opening_shift: "",
      stock_settings: "",
      invoice_doc: "",
      return_doc: "",
      customer: "",
      customer_info: "",
      discount_amount: 0,
      additional_discount_percentage: 0,
      total_tax: 0,
      items: [],
      posOffers: [],
      posa_offers: [],
      posa_coupons: [],
      allItems: [],
      discount_percentage_offer_name: null,
      invoiceTypes: ["Invoice", "Order"],
      invoiceType: "Invoice",
      itemsPerPage: 1000,
      expanded: [],
      singleExpand: true,
      cancel_dialog: false,
      float_precision: 2,
      currency_precision: 2,
      new_line: false,
      delivery_charges: [],
      delivery_charges_rate: 0,
      selcted_delivery_charges: {},
      invoice_posting_date: false,
      posting_date: frappe.datetime.nowdate(),
      current_role: "",
      relay_status: {
        enabled: false,
        connected: false,
        profile_relay_url: "",
      },
      items_headers: [
        {
          text: __("Name"),
          align: "start",
          sortable: true,
          value: "item_name",
        },
        { text: __("QTY"), value: "qty", align: "center" },
        { text: __("UOM"), value: "uom", align: "center" },
        { text: __("Rate"), value: "rate", align: "center" },
        { text: __("Amount"), value: "amount", align: "center" },
        { text: __("is Offer"), value: "posa_is_offer", align: "center" },
      ],
    };
  },

  components: {
    Customer,
  },

  computed: {
    is_sales_associate_role() {
      return (this.current_role || "") === "cline-Sales Associate";
    },
    is_cashier_role() {
      return (this.current_role || "") === "cline-Cashier";
    },
    simplified_sa_cashier_ui_enabled() {
      return (
        parseInt((this.pos_profile && this.pos_profile.posa_simplified_sa_cashier_ui) || 0, 10) === 1
      );
    },
    show_held_button() {
      return !(this.simplified_sa_cashier_ui_enabled && this.is_sales_associate_role);
    },
    show_return_button() {
      return !(this.simplified_sa_cashier_ui_enabled && this.is_sales_associate_role);
    },
    show_pay_button() {
      return !(this.simplified_sa_cashier_ui_enabled && this.is_sales_associate_role);
    },
    can_use_quotation_actions() {
      const role = (this.current_role || "").trim();
      if (role === "cline-Sales Associate") {
        return parseInt((this.pos_profile && this.pos_profile.posa_allow_sa_quotation) || 1, 10) === 1;
      }
      if (role === "cline-Cashier") {
        return (
          parseInt((this.pos_profile && this.pos_profile.posa_allow_cashier_quotation) || 1, 10) === 1
        );
      }
      return false;
    },
    total_qty() {
      this.close_payments();
      let qty = 0;
      this.items.forEach((item) => {
        qty += flt(item.qty);
      });
      return this.flt(qty, this.float_precision);
    },
    Total() {
      let sum = 0;
      this.items.forEach((item) => {
        sum += flt(item.qty) * flt(item.rate);
      });
      return this.flt(sum, this.currency_precision);
    },
    subtotal() {
      this.close_payments();
      let sum = 0;
      this.items.forEach((item) => {
        sum += flt(item.qty) * flt(item.rate);
      });
      sum -= this.flt(this.discount_amount);
      sum += this.flt(this.delivery_charges_rate);
      return this.flt(sum, this.currency_precision);
    },
    total_items_discount_amount() {
      let sum = 0;
      this.items.forEach((item) => {
        sum += flt(item.qty) * flt(item.discount_amount);
      });
      return this.flt(sum, this.float_precision);
    },
  },

  methods: {
    get_current_role() {
      return resolveCurrentRole();
    },
    normalize_relay_url(relayUrl) {
      return String(relayUrl || "").trim().replace(/\/$/, "");
    },
    relay_config_storage_key() {
      const site =
        (frappe.boot && (frappe.boot.sitename || frappe.boot.site_name)) ||
        window.location.host ||
        "site";
      const profile = String((this.pos_profile && this.pos_profile.name) || "default").trim() || "default";
      return `posa_edge_relay_config:${site}:${profile}`;
    },
    relay_default_config_storage_key() {
      const site =
        (frappe.boot && (frappe.boot.sitename || frappe.boot.site_name)) ||
        window.location.host ||
        "site";
      return `posa_edge_relay_config:${site}:__default__`;
    },
    get_browser_relay_config() {
      try {
        const raw =
          localStorage.getItem(this.relay_config_storage_key()) ||
          localStorage.getItem(this.relay_default_config_storage_key());
        if (!raw) return null;
        const parsed = JSON.parse(raw) || {};
        const relayUrl = this.normalize_relay_url(parsed.relay_url);
        if (!relayUrl) return null;
        return { relay_url: relayUrl };
      } catch (e) {
        return null;
      }
    },
    get_relay_base_url() {
      const browserConfig = this.get_browser_relay_config();
      const raw =
        (browserConfig && browserConfig.relay_url) ||
        (this.relay_status && this.relay_status.profile_relay_url) ||
        (this.relay_status && this.relay_status.relay_url) ||
        "";
      return this.normalize_relay_url(raw);
    },
    so_lookup_policy() {
      const maxAgeDays = Math.max(
        0,
        Number((this.pos_profile && this.pos_profile.posa_sales_order_lookup_max_age_days) || 1) || 1
      );
      const allowStale =
        Number((this.pos_profile && this.pos_profile.posa_allow_stale_sales_order_fetch) || 0) === 1;
      const historyDays = Math.max(
        maxAgeDays,
        Number((this.pos_profile && this.pos_profile.posa_stale_sales_order_history_days) || 30) || 30
      );
      return { maxAgeDays, allowStale, historyDays };
    },
	    get_relay_client_headers(extra = {}) {
	      const headers = { ...extra };
	      try {
	        const relayKey = (localStorage.getItem("posa_relay_client_key") || "").trim();
	        if (relayKey) headers["X-Relay-Client-Key"] = relayKey;
	      } catch (e) {}
	      return headers;
	    },
    get_explicit_token_ref(source = {}) {
      const doc = source || {};
      const line = (
        (Array.isArray(doc.items)
          ? doc.items.find((row) => row && row.sales_order)
          : null) || {}
      );
      return String(
        doc.token_id ||
          doc.sales_order ||
          doc.sales_order_name ||
          line.sales_order ||
          ""
      ).trim();
    },
	    relay_customer_fallback_enabled() {
      return this.relayWorkflowEnabled() && !!this.get_relay_base_url();
    },
    is_click_event(payload) {
      return !!(payload && typeof payload === "object" && payload.target && payload.preventDefault);
    },
    relayWorkflowEnabled() {
      const browserConfig = this.get_browser_relay_config();
      return (
        parseInt((this.pos_profile && this.pos_profile.custom_have_token) || 0, 10) === 1 ||
        !!(browserConfig && browserConfig.relay_url)
      );
    },
    reset_after_token_save() {
      this.items = [];
      this.customer = this.pos_profile.customer;
      this.invoice_doc = "";
      this.discount_amount = 0;
      this.additional_discount_percentage = 0;
      this.delivery_charges_rate = 0;
      this.selcted_delivery_charges = {};
      this.posa_offers = [];
      evntBus.$emit("set_pos_coupons", []);
      this.posa_coupons = [];
      this.return_doc = "";
      this.invoiceType = "Order";
      this.invoiceTypes = ["Invoice", "Order"];
      evntBus.$emit("set_customer_readonly", false);
    },
    handle_save_new() {
      this.current_role = this.get_current_role();
      if (this.is_sales_associate_role) {
        return this.save_sales_order_token_and_reset();
      }
      return this.new_invoice();
    },
    get_sales_order_token_payload() {
      return {
        pos_profile: this.pos_profile.name,
        pos_opening_shift: (this.pos_opening_shift && this.pos_opening_shift.name) || "",
        company: this.pos_profile.company,
        customer: this.customer,
        currency: this.pos_profile.currency,
        campaign: this.pos_profile.campaign || "",
        posting_date: this.posting_date,
        items: this.get_order_items(),
        discount_amount: flt(this.discount_amount),
        additional_discount_percentage: flt(this.additional_discount_percentage),
        posa_offers: this.posa_offers || [],
        posa_coupons: this.posa_coupons || [],
        posa_delivery_charges: (this.selcted_delivery_charges || {}).name || "",
        posa_delivery_charges_rate: this.delivery_charges_rate || 0,
      };
    },
    get_quotation_payload() {
      const payload = this.get_sales_order_token_payload();
      payload.valid_till = frappe.datetime.add_days(
        payload.posting_date || frappe.datetime.nowdate(),
        Math.max(
          1,
          Number((this.pos_profile && this.pos_profile.posa_quotation_validity_days) || 7) || 7
        )
      );
      return payload;
    },
    create_quotation_token_cloud(payload) {
      return new Promise((resolve, reject) => {
        frappe.call({
          method: "posawesome.posawesome.api.posapp.create_quotation_token",
          args: { data: payload },
          async: true,
          callback: (r) => {
            if (r && r.exc) {
              reject(new Error(__("Unable to create Quotation.")));
              return;
            }
            if (!r || !r.message) {
              reject(new Error(__("Empty response while creating Quotation.")));
              return;
            }
            resolve(r.message);
          },
          error: (err) => {
            const message =
              (err && err.message) || __("Unable to create Quotation. Please try again.");
            reject(new Error(message));
          },
        });
      });
    },
    async create_quotation_token_relay_local(payload) {
      const relayBaseUrl = this.get_relay_base_url();
      if (!relayBaseUrl) {
        throw new Error(__("Relay URL is not configured for offline Quotations."));
      }
      const validityDays = Math.max(
        1,
        Number((this.pos_profile && this.pos_profile.posa_quotation_validity_days) || 7) || 7
      );
      const quotePayload = {
        pos_profile_id: this.pos_profile.name,
        created_by: frappe.session.user,
        customer_id: this.customer,
        customer_name:
          (this.customer_info && this.customer_info.customer_name) || this.customer,
        currency: this.pos_profile.currency,
        valid_until:
          payload.valid_till ||
          frappe.datetime.add_days(payload.posting_date || frappe.datetime.nowdate(), validityDays),
        validity_days: validityDays,
        role: this.current_role || this.get_current_role() || "",
        items: (this.items || []).map((item) => ({
          item_code: item.item_code,
          item_name: item.item_name || item.item_code,
          qty: flt(item.qty),
          uom: item.uom,
          rate: flt(item.rate),
          amount: flt(item.qty) * flt(item.rate),
          conversion_factor: flt(
            typeof item.conversion_factor === "undefined" ? 1 : item.conversion_factor || 1
          ),
          serial_no: item.serial_no || "",
          batch_no: item.batch_no || "",
          discount_percentage: flt(item.discount_percentage || 0),
          discount_amount: flt(item.discount_amount || 0),
          price_list_rate: flt(item.price_list_rate || item.rate || 0),
          posa_notes: item.posa_notes || "",
          posa_delivery_date: item.posa_delivery_date || "",
          posa_row_id: item.posa_row_id,
        })),
      };

      const resp = await fetch(`${relayBaseUrl}/relay/quote/create`, {
        method: "POST",
        headers: this.get_relay_client_headers({ "Content-Type": "application/json" }),
        body: JSON.stringify(quotePayload),
      });
      let body = {};
      try {
        body = (await resp.json()) || {};
      } catch (e) {
        body = {};
      }
      if (!resp.ok || !body.ok || !body.quote) {
        throw new Error(body.message || __("Unable to create Quotation on local relay."));
      }
      return {
        quote_name: body.quote.quote_id,
        valid_till: body.quote.valid_until || quotePayload.valid_until,
        is_expired: 0,
        age_days: Number(body.quote.order_age_days || 0),
        grand_total: Number(body.quote.base_total || 0),
        currency: body.quote.currency || this.pos_profile.currency,
        local_only: 1,
        relay_quote: body.quote,
      };
    },
    async save_quote() {
      this.current_role = this.get_current_role();
      if (!this.can_use_quotation_actions) {
        evntBus.$emit("show_mesage", {
          text: __("Quotation actions are disabled for this role/profile."),
          color: "warning",
        });
        return null;
      }
      if (!this.customer) {
        evntBus.$emit("show_mesage", { text: __(`There is no Customer !`), color: "error" });
        return null;
      }
      if (!this.items.length) {
        evntBus.$emit("show_mesage", { text: __(`There is no Items !`), color: "error" });
        return null;
      }
      if (!this.validate()) {
        return null;
      }

      const payload = this.get_quotation_payload();
      try {
        let result = null;
        let usedRelayFallback = false;
        try {
          result = await this.create_quotation_token_cloud(payload);
        } catch (cloudErr) {
          if (!this.relayWorkflowEnabled() || !this.get_relay_base_url()) {
            throw cloudErr;
          }
          result = await this.create_quotation_token_relay_local(payload);
          usedRelayFallback = true;
        }
        const quoteName = result.quote_name || result.name || "";
        const validTill = result.valid_till || "";
        evntBus.$emit("show_mesage", {
          text: usedRelayFallback
            ? __("Quotation {0} created on relay (offline mode). Valid till: {1}", [quoteName, validTill || "-"])
            : __("Quotation {0} created. Valid till: {1}", [quoteName, validTill || "-"]),
          color: usedRelayFallback ? "warning" : "success",
        });
        this.reset_after_token_save();
        return result;
      } catch (e) {
        evntBus.$emit("show_mesage", {
          text: (e && e.message) || __("Unable to create Quotation."),
          color: "error",
        });
        return null;
      }
    },
    create_sales_order_token(payload) {
      return new Promise((resolve, reject) => {
        frappe.call({
          method: "posawesome.posawesome.api.posapp.create_sales_order_token",
          args: { data: payload },
          async: true,
          callback: (r) => {
            if (r && r.exc) {
              reject(new Error(__("Unable to create Sales Order token.")));
              return;
            }
            if (!r || !r.message) {
              reject(new Error(__("Empty response while creating Sales Order token.")));
              return;
            }
            resolve(r.message);
          },
          error: (err) => {
            const message =
              (err && err.message) ||
              __("Unable to create Sales Order token. Please try again.");
            reject(new Error(message));
          },
        });
      });
    },
    build_relay_local_token_meta(relayToken, tokenPayload = {}) {
      const token = relayToken || {};
      const sourceItems = Array.isArray(token.items) && token.items.length ? token.items : tokenPayload.items || [];
      const grandTotal = sourceItems.reduce((sum, row) => {
        const qty = flt((row && row.qty) || 0);
        const rate = flt((row && row.rate) || 0);
        return sum + flt((row && row.amount) || qty * rate);
      }, 0);
      const tokenId = String(token.token_id || "").trim();
      return {
        local_only: 1,
        token_id: tokenId,
        token_last4: tokenId ? tokenId.slice(-4) : "",
        sales_order_name: tokenId,
        customer: tokenPayload.customer || token.customer_id || this.customer,
        customer_name:
          (this.customer_info && this.customer_info.customer_name) ||
          token.customer_name ||
          tokenPayload.customer ||
          this.customer,
        grand_total: grandTotal,
        currency: this.pos_profile.currency,
        order_taken_at: token.created_at || token.updated_at || new Date().toISOString(),
        sales_associate_user: frappe.session.user,
        sales_associate_name: frappe.session.user_fullname || frappe.session.user,
        sales_order: {
          customer: token.customer_id || tokenPayload.customer || this.customer,
          customer_name:
            (this.customer_info && this.customer_info.customer_name) ||
            token.customer_name ||
            tokenPayload.customer ||
            this.customer,
          items: sourceItems.map((row) => {
            const payload = row && row.payload && typeof row.payload === "object" ? row.payload : {};
            return {
              item_code: row.item_code || payload.item_code,
              item_name: row.item_name || payload.item_name || "",
              qty: flt((row && row.qty) || payload.qty || 0),
              uom: row.uom || payload.uom || "",
              rate: flt((row && row.rate) || payload.rate || 0),
              amount: flt((row && row.amount) || payload.amount || 0),
            };
          }),
        },
      };
    },
    async create_sales_order_token_relay_local(tokenPayload) {
      const relayBaseUrl = this.get_relay_base_url();
      if (!relayBaseUrl) {
        throw new Error(__("Relay URL is not configured for offline Sales Order tokens."));
      }
      const items = (this.items || []).map((item) => ({
        item_code: item.item_code,
        item_name: item.item_name || item.item_code,
        qty: flt(item.qty),
        uom: item.uom,
        rate: flt(item.rate),
        amount: flt(item.qty) * flt(item.rate),
        conversion_factor: flt(
          typeof item.conversion_factor === "undefined" ? 1 : item.conversion_factor || 1
        ),
        serial_no: item.serial_no || "",
        batch_no: item.batch_no || "",
        discount_percentage: flt(item.discount_percentage || 0),
        discount_amount: flt(item.discount_amount || 0),
        price_list_rate: flt(item.price_list_rate || item.rate || 0),
        posa_notes: item.posa_notes || "",
        posa_delivery_date: item.posa_delivery_date || "",
        posa_row_id: item.posa_row_id,
      }));
      const relayPayload = {
        pos_profile_id: this.pos_profile.name,
        cashier_user_id: frappe.session.user,
        customer_id: this.customer,
        customer_name:
          (this.customer_info && this.customer_info.customer_name) || this.customer,
        source_doctype: "Sales Order",
        source_name: "",
        role: this.current_role || this.get_current_role() || "",
        items: items,
      };

      const resp = await fetch(`${relayBaseUrl}/relay/token/create`, {
        method: "POST",
        headers: this.get_relay_client_headers({ "Content-Type": "application/json" }),
        body: JSON.stringify(relayPayload),
      });
      let body = {};
      try {
        body = (await resp.json()) || {};
      } catch (e) {
        body = {};
      }
      if (!resp.ok || !body.ok || !body.token) {
        throw new Error(body.message || __("Unable to create Sales Order token on local relay."));
      }
      const meta = this.build_relay_local_token_meta(body.token, tokenPayload || {});
      meta.outbox_event_id = body.outbox_event_id || null;
      meta.created_locally_on_relay = 1;
      return meta;
    },
    normalize_relay_token_to_order_doc(row = {}) {
      const createdAt = String(row.created_at || "").trim();
      const transactionDate = createdAt
        ? createdAt.replace("T", " ").slice(0, 10)
        : frappe.datetime.nowdate();
      const items = (row.items || []).map((line, idx) => {
        const payload = line && line.payload && typeof line.payload === "object" ? line.payload : {};
        const qty = flt(line.qty || payload.qty || 0);
        const rate = flt(line.rate || payload.rate || 0);
        return {
          item_code: line.item_code || payload.item_code,
          item_name: line.item_name || payload.item_name || line.item_code || "",
          qty: qty,
          rate: rate,
          amount: flt(line.amount || payload.amount || qty * rate),
          uom: line.uom || payload.uom || "",
          conversion_factor: flt(
            typeof payload.conversion_factor === "undefined" ? 1 : payload.conversion_factor || 1
          ),
          serial_no: payload.serial_no || "",
          batch_no: payload.batch_no || "",
          discount_percentage: flt(payload.discount_percentage || 0),
          discount_amount: flt(payload.discount_amount || 0),
          price_list_rate: flt(payload.price_list_rate || rate),
          posa_notes: payload.posa_notes || "",
          posa_delivery_date: payload.posa_delivery_date || "",
          posa_offers: payload.posa_offers || [],
          posa_offer_applied: !!payload.posa_offer_applied,
          posa_is_offer: !!payload.posa_is_offer,
          posa_is_replace: !!payload.posa_is_replace,
          is_free_item: !!payload.is_free_item,
          posa_row_id: payload.posa_row_id || `${row.token_id || "TOKEN"}-${idx + 1}`,
          sales_order: row.token_id || "",
          sales_order_name: row.token_id || "",
        };
      });
      const grandTotal = flt(row.grand_total || 0);
      return {
        name: row.token_id || "",
        doctype: "Sales Order",
        relay_offline_order: 1,
        relay_token_status: row.status || "TOKEN_OPEN",
        token_id: row.token_id || "",
        sales_order: row.token_id || "",
        sales_order_name: row.token_id || "",
        customer: row.customer_id || row.customer_name || "",
        customer_name: row.customer_name || row.customer_id || "",
        company: this.pos_profile.company,
        currency: this.pos_profile.currency,
        pos_profile: this.pos_profile.name,
        posting_date: transactionDate,
        transaction_date: transactionDate,
        grand_total: grandTotal,
        rounded_total: flt(row.rounded_total || grandTotal),
        net_total: flt(row.net_total || grandTotal),
        total: flt(row.total || grandTotal),
        discount_amount: 0,
        additional_discount_percentage: 0,
        posa_offers: [],
        posa_coupons: [],
        items: items,
      };
    },
    async fetch_open_orders_from_relay(searchText = "") {
      const base = this.get_relay_base_url();
      if (!base) {
        throw new Error(__("Relay URL is not configured."));
      }
      const policy = this.so_lookup_policy();
      const params = new URLSearchParams();
      params.set("limit", "100");
      params.set("statuses_csv", "TOKEN_OPEN");
      params.set("max_age_days", String(policy.maxAgeDays));
      params.set("allow_stale", policy.allowStale ? "1" : "0");
      params.set("history_days", String(policy.historyDays));
      if (searchText) params.set("search", searchText);
      const resp = await fetch(`${base}/relay/tokens/search?${params.toString()}`, {
        method: "GET",
        headers: this.get_relay_client_headers({ Accept: "application/json" }),
      });
      let body = {};
      try {
        body = (await resp.json()) || {};
      } catch (e) {
        body = {};
      }
      if (!resp.ok || body.ok === false) {
        throw new Error(body.message || __("Unable to load Sales Orders from relay."));
      }
      return (body.rows || []).map((row) => this.normalize_relay_token_to_order_doc(row));
    },
    merge_sales_order_rows(cloudRows = [], relayRows = []) {
      const seen = new Set();
      const keyFor = (row) =>
        String(
          (row && (row.token_id || row.sales_order_name || row.sales_order || row.name)) || ""
        ).trim();
      const merged = [];
      (cloudRows || []).forEach((row) => {
        const key = keyFor(row);
        if (key) seen.add(key);
        merged.push(row);
      });
      (relayRows || []).forEach((row) => {
        const key = keyFor(row);
        if (key && seen.has(key)) return;
        if (key) seen.add(key);
        merged.push(row);
      });
      return merged;
    },
    async fetch_quotes_from_relay(searchText = "") {
      const base = this.get_relay_base_url();
      if (!base) throw new Error(__("Relay URL is not configured."));
      const policy = this.so_lookup_policy();
      const params = new URLSearchParams();
      params.set("pos_profile_id", this.pos_profile.name || "");
      params.set("limit", "100");
      params.set("statuses_csv", "OPEN");
      params.set("max_age_days", String(policy.maxAgeDays));
      params.set("allow_stale", policy.allowStale ? "1" : "0");
      params.set("history_days", String(policy.historyDays));
      if (searchText) params.set("search", searchText);
      const resp = await fetch(`${base}/relay/quotes/search?${params.toString()}`, {
        method: "GET",
        headers: this.get_relay_client_headers({ Accept: "application/json" }),
      });
      let body = {};
      try {
        body = (await resp.json()) || {};
      } catch (e) {
        body = {};
      }
      if (!resp.ok || body.ok === false) {
        throw new Error(body.message || __("Unable to load Quotations from relay."));
      }
      return body.rows || [];
    },
    escape_html(value) {
      return String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
    },
    token_slip_date_time(meta) {
      const raw = String((meta && meta.order_taken_at) || "");
      if (!raw) {
        return {
          dateLabel: frappe.datetime.str_to_user(this.posting_date || frappe.datetime.nowdate()),
          timeLabel: frappe.datetime.now_time().split(".")[0],
        };
      }
      const normalized = raw.replace("T", " ").replace("Z", "");
      const [datePart, timePartRaw] = normalized.split(" ");
      return {
        dateLabel: datePart ? frappe.datetime.str_to_user(datePart) : raw,
        timeLabel: (timePartRaw || "").split(".")[0] || frappe.datetime.now_time().split(".")[0],
      };
    },
    token_slip_qr_payload(meta) {
      const dt = this.token_slip_date_time(meta);
      return JSON.stringify({
        type: "POS-SO-TOKEN",
        sales_order: meta.sales_order_name,
        token_id: meta.token_id,
        token_last4: meta.token_last4,
        customer_name: meta.customer_name,
        grand_total: meta.grand_total,
        currency: meta.currency,
        sales_associate_user: meta.sales_associate_user || frappe.session.user,
        sales_associate_name:
          meta.sales_associate_name || frappe.session.user_fullname || frappe.session.user,
        order_date: dt.dateLabel,
        order_time: dt.timeLabel,
        site: window.location.origin,
      });
    },
    print_sales_order_token_slip(meta) {
      const printWindow = window.open("", "", "height=700,width=420");
      if (!printWindow) {
        evntBus.$emit("show_mesage", {
          text: __("Popup blocked. Please allow popups to print token slips."),
          color: "warning",
        });
        return;
      }

      const dt = this.token_slip_date_time(meta);
      const soName = this.escape_html(meta.sales_order_name || "");
      const tokenLast4 = this.escape_html(meta.token_last4 || "");
      const customerName = this.escape_html(meta.customer_name || "");
      const saName = this.escape_html(
        meta.sales_associate_name || frappe.session.user_fullname || frappe.session.user
      );
      const currency = this.escape_html(this.currencySymbol(meta.currency) || "");
      const grandTotal = this.escape_html(this.formtCurrency(meta.grand_total || 0));
      const qrPayload = this.escape_html(this.token_slip_qr_payload(meta));
      const barcodeValue = this.escape_html(meta.token_id || meta.sales_order_name || "");

      printWindow.document.write(`
        <html>
          <head>
            <title>Sales Order Token Slip</title>
            <meta charset="utf-8" />
            <script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"><\/script>
            <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"><\/script>
            <style>
              body {
                width: 80mm;
                margin: 0 auto;
                padding: 8px;
                font-family: Arial, sans-serif;
                color: #111;
              }
              .center { text-align: center; }
              .title { font-size: 16px; font-weight: bold; margin-bottom: 6px; }
              .muted { color: #555; font-size: 11px; }
              .row { margin: 3px 0; font-size: 12px; }
              .token-last4 { font-size: 28px; font-weight: bold; letter-spacing: 2px; margin: 8px 0 4px; }
              .total { font-size: 15px; font-weight: bold; margin: 6px 0; }
              .divider { border-top: 1px dashed #999; margin: 8px 0; }
              #qrcode { width: 128px; height: 128px; margin: 0 auto; }
              #barcode-wrap { margin-top: 8px; text-align: center; }
              #barcode { width: 100%; max-width: 280px; }
              .fallback { font-size: 11px; color: #a33; margin-top: 4px; display: none; }
            </style>
          </head>
          <body>
            <div class="center title">Sales Order Token</div>
            <div class="center muted">Full SO: ${soName}</div>
            <div class="center token-last4">${tokenLast4}</div>
            <div class="divider"></div>
            <div class="row"><b>Customer:</b> ${customerName}</div>
            <div class="row"><b>Sales Associate:</b> ${saName}</div>
            <div class="row"><b>Date:</b> ${this.escape_html(dt.dateLabel)}</div>
            <div class="row"><b>Time:</b> ${this.escape_html(dt.timeLabel)}</div>
            <div class="row total"><b>Grand Total:</b> ${currency} ${grandTotal}</div>
            <div class="divider"></div>
            <div id="qrcode" class="center"></div>
            <div id="barcode-wrap">
              <svg id="barcode"></svg>
              <div class="muted">${soName}</div>
            </div>
            <div id="render-fallback" class="fallback center">
              QR/Barcode render failed. Use SO Number / Last4 above.
            </div>
            <script>
              (function() {
                var failed = false;
                try {
                  if (window.QRCode) {
                    new QRCode(document.getElementById('qrcode'), {
                      text: ${JSON.stringify("")} + ${JSON.stringify(this.token_slip_qr_payload(meta))},
                      width: 128,
                      height: 128,
                      correctLevel: QRCode.CorrectLevel.M
                    });
                  } else {
                    failed = true;
                  }
                  if (window.JsBarcode) {
                    JsBarcode('#barcode', ${JSON.stringify(meta.token_id || meta.sales_order_name || "")}, {
                      format: 'CODE128',
                      width: 1.5,
                      height: 40,
                      displayValue: false,
                      margin: 0
                    });
                  } else {
                    failed = true;
                  }
                } catch (e) {
                  failed = true;
                }
                if (failed) {
                  var fb = document.getElementById('render-fallback');
                  if (fb) fb.style.display = 'block';
                }
                window.focus();
                setTimeout(function() { window.print(); }, 300);
              })();
            <\/script>
          </body>
        </html>
      `);

      printWindow.document.close();
    },
    show_sales_order_token_dialog(meta) {
      const vm = this;
      const dt = this.token_slip_date_time(meta);
      const tokenLast4 = this.escape_html(meta.token_last4 || "");
      const soName = this.escape_html(meta.sales_order_name || "");
      const customerName = this.escape_html(meta.customer_name || "");
      const grandTotal = `${this.currencySymbol(meta.currency)} ${this.formtCurrency(meta.grand_total || 0)}`;
      const d = new frappe.ui.Dialog({
        title: __("Sales Order Token"),
        fields: [
          {
            fieldname: "token",
            fieldtype: "HTML",
            options: `
              <div style="text-align:center;font-size:42px;padding:0.5rem 0;"><b>${tokenLast4}</b></div>
              <div style="text-align:center;padding-bottom:0.5rem;"><small><b>SO:</b> ${soName}</small></div>
              <div style="font-size:13px;line-height:1.5;">
                <div><b>${__("Customer")}:</b> ${customerName}</div>
                <div><b>${__("Sales Associate")}:</b> ${this.escape_html(meta.sales_associate_name || frappe.session.user_fullname || frappe.session.user)}</div>
                <div><b>${__("Date")}:</b> ${this.escape_html(dt.dateLabel)} &nbsp; <b>${__("Time")}:</b> ${this.escape_html(dt.timeLabel)}</div>
                <div><b>${__("Grand Total")}:</b> ${this.escape_html(grandTotal)}</div>
              </div>
              <div style="padding-top:0.75rem;text-align:center;color:#085294;font-size:13px;font-weight:600;">
                ${this.escape_html(__("Use the 'Print Token Slip' button below to print and hand this token to the customer."))}
              </div>`,
          },
          {
            fieldname: "relay_note",
            fieldtype: "HTML",
            options: `<div style="text-align:center;color:#1e88e5;padding-top:0.25rem;"><small>${frappe._(
              meta.local_only
                ? "Sales Order token created on local relay (offline mode). It will sync to cloud later."
                : "Sales Order token created. Relay token sync is best-effort."
            )}</small></div>`,
          },
        ],
        primary_action_label: __("Print Token Slip"),
        primary_action() {
          vm.print_sales_order_token_slip(meta);
          d.hide();
        },
        secondary_action_label: __("Close"),
      });
      d.show();
    },
    sync_relay_token_for_sales_order(meta) {
      const relayEnabled = this.relayWorkflowEnabled();
      const relayBaseUrl = this.get_relay_base_url();
      if (!relayEnabled || !relayBaseUrl || !meta || !meta.sales_order) {
        return;
      }

      const soDoc = meta.sales_order || {};
      const tokenPayload = {
        token_id: meta.token_id || meta.sales_order_name,
        pos_profile_id: this.pos_profile.name,
        cashier_user_id: frappe.session.user,
        customer_id: soDoc.customer || meta.customer,
        customer_name: soDoc.customer_name || meta.customer_name,
        source_doctype: "Sales Order",
        source_name: meta.sales_order_name,
        role: this.current_role || "",
        items: (soDoc.items || []).map((row) => ({
          item_code: row.item_code,
          item_name: row.item_name,
          qty: row.qty,
          uom: row.uom,
          rate: row.rate,
          amount: row.amount,
        })),
      };

      fetch(`${relayBaseUrl}/relay/token/create`, {
        method: "POST",
        headers: this.get_relay_client_headers({ "Content-Type": "application/json" }),
        body: JSON.stringify(tokenPayload),
      }).catch(() => {
        evntBus.$emit("show_mesage", {
          text: __("Sales Order token created, but relay token sync failed. You can continue."),
          color: "warning",
        });
      });
    },
    async save_sales_order_token_and_reset() {
      this.current_role = this.get_current_role();
      if (!this.customer) {
        evntBus.$emit("show_mesage", {
          text: __(`There is no Customer !`),
          color: "error",
        });
        return null;
      }
      if (!this.items.length) {
        evntBus.$emit("show_mesage", {
          text: __(`There is no Items !`),
          color: "error",
        });
        return null;
      }
      if (!this.validate()) {
        return null;
      }
      if (!this.pos_profile.posa_allow_sales_order) {
        evntBus.$emit("show_mesage", {
          text: __("POS Profile is not configured to allow Sales Orders."),
          color: "error",
        });
        return null;
      }

      try {
        const payload = this.get_sales_order_token_payload();
        let result = null;
        let usedRelayOfflineFallback = false;
        try {
          result = await this.create_sales_order_token(payload);
        } catch (cloudErr) {
          if (!this.relayWorkflowEnabled() || !this.get_relay_base_url()) {
            throw cloudErr;
          }
          result = await this.create_sales_order_token_relay_local(payload);
          usedRelayOfflineFallback = true;
        }
        this.show_sales_order_token_dialog(result);
        if (!usedRelayOfflineFallback) {
          this.sync_relay_token_for_sales_order(result);
        }
        evntBus.$emit("workflow_monitor_refresh_requested");
        this.reset_after_token_save();
        evntBus.$emit("show_mesage", {
          text: __(
            usedRelayOfflineFallback
              ? "Sales Order token created on local relay (offline): {0}"
              : "Sales Order token created: {0}",
            [result.sales_order_name || result.token_id || ""]
          ),
          color: usedRelayOfflineFallback ? "warning" : "success",
        });
        frappe.utils.play_sound("submit");
        return result;
      } catch (e) {
        evntBus.$emit("show_mesage", {
          text: e.message || __("Unable to create Sales Order token."),
          color: "error",
        });
        frappe.utils.play_sound("error");
        return null;
      }
    },
    apply_relay_customer_info(row) {
      let payload = (row && row.payload) || {};
      if (typeof payload === "string") {
        try {
          payload = JSON.parse(payload) || {};
        } catch (e) {
          payload = {};
        }
      }
      const customerId =
        payload.customer_id || payload.name || (row && row.customer_id) || this.customer;
      this.customer_info = {
        loyalty_points:
          typeof payload.loyalty_points === "undefined" ? null : payload.loyalty_points,
        conversion_factor:
          typeof payload.conversion_factor === "undefined"
            ? null
            : payload.conversion_factor,
        email_id: payload.email_id || (row && row.email_id) || "",
        mobile_no: payload.mobile_no || (row && row.mobile_no) || "",
        image: payload.image || "",
        loyalty_program: payload.loyalty_program || null,
        customer_price_list: payload.customer_price_list || null,
        customer_group: payload.customer_group || "",
        customer_type: payload.customer_type || "Individual",
        territory: payload.territory || "",
        birthday: payload.birthday || null,
        gender: payload.gender || "",
        tax_id: payload.tax_id || (row && row.tax_id) || "",
        posa_discount: payload.posa_discount || 0,
        name: customerId,
        customer_name:
          payload.customer_name || (row && row.customer_name) || customerId,
        customer_group_price_list: payload.customer_group_price_list || null,
        primary_address: payload.primary_address || "",
      };
      this.update_price_list();
      return true;
    },
    async fetch_customer_details_from_relay() {
      if (!this.customer || !this.relay_customer_fallback_enabled()) {
        return false;
      }
      const base = this.get_relay_base_url();
      try {
        const resp = await fetch(
          `${base}/relay/customer/search?q=${encodeURIComponent(this.customer)}&limit=20`,
          {
            method: "GET",
            headers: this.get_relay_client_headers({
              Accept: "application/json",
            }),
          }
        );
        const payload = await resp.json();
        if (!resp.ok || !payload.ok) {
          return false;
        }
        const rows = payload.rows || [];
        const row =
          rows.find((r) => r.customer_id === this.customer) ||
          rows.find((r) => ((r.payload || {}).name || (r.payload || {}).customer_id) === this.customer) ||
          rows[0];
        if (!row) {
          return false;
        }
        return this.apply_relay_customer_info(row);
      } catch (e) {
        return false;
      }
    },
    remove_item(item) {
      const index = this.items.findIndex(
        (el) => el.posa_row_id == item.posa_row_id
      );
      if (index >= 0) {
        this.items.splice(index, 1);
      }
      const idx = this.expanded.findIndex(
        (el) => el.posa_row_id == item.posa_row_id
      );
      if (idx >= 0) {
        this.expanded.splice(idx, 1);
      }
    },

    add_one(item) {
      item.qty++;
      if (item.qty == 0) {
        this.remove_item(item);
      }
      this.calc_stock_qty(item, item.qty);
      this.$forceUpdate();
    },
    subtract_one(item) {
      item.qty--;
      if (item.qty == 0) {
        this.remove_item(item);
      }
      this.calc_stock_qty(item, item.qty);
      this.$forceUpdate();
    },

    add_item(item) {
      if (!item.uom) {
        item.uom = item.stock_uom;
      }
      let index = -1;
      if (!this.new_line) {
        index = this.items.findIndex(
          (el) =>
            el.item_code === item.item_code &&
            el.uom === item.uom &&
            !el.posa_is_offer &&
            !el.posa_is_replace &&
            el.batch_no === item.batch_no
        );
      }
      if (index === -1 || this.new_line) {
        const new_item = this.get_new_item(item);
        if (item.has_serial_no && item.to_set_serial_no) {
          new_item.serial_no_selected = [];
          new_item.serial_no_selected.push(item.to_set_serial_no);
          item.to_set_serial_no = null;
        }
        if (item.has_batch_no && item.to_set_batch_no) {
          new_item.batch_no = item.to_set_batch_no;
          item.to_set_batch_no = null;
          item.batch_no = null;
          this.set_batch_qty(new_item, new_item.batch_no, false);
        }
        this.items.unshift(new_item);
        this.update_item_detail(new_item);
      } else {
        const cur_item = this.items[index];
        this.update_items_details([cur_item]);
        if (item.has_serial_no && item.to_set_serial_no) {
          if (cur_item.serial_no_selected.includes(item.to_set_serial_no)) {
            evntBus.$emit("show_mesage", {
              text: __(`This Serial Number {0} has already been added!`, [
                item.to_set_serial_no,
              ]),
              color: "warning",
            });
            item.to_set_serial_no = null;
            return;
          }
          cur_item.serial_no_selected.push(item.to_set_serial_no);
          item.to_set_serial_no = null;
        }
        if (!cur_item.has_batch_no) {
          cur_item.qty += item.qty || 1;
          this.calc_stock_qty(cur_item, cur_item.qty);
        } else {
          if (
            (cur_item.stock_qty < cur_item.actual_batch_qty &&
              cur_item.batch_no == item.batch_no) ||
            !cur_item.batch_no
          ) {
            cur_item.qty += item.qty || 1;
            this.calc_stock_qty(cur_item, cur_item.qty);
          } else {
            const new_item = this.get_new_item(cur_item);
            new_item.batch_no = item.batch_no || item.to_set_batch_no;
            new_item.batch_no_expiry_date = "";
            new_item.actual_batch_qty = "";
            new_item.qty = item.qty || 1;
            if (new_item.batch_no) {
              this.set_batch_qty(new_item, new_item.batch_no, false);
              item.to_set_batch_no = null;
              item.batch_no = null;
            }
            this.items.unshift(new_item);
          }
        }
        this.set_serial_no(cur_item);
      }
      this.$forceUpdate();
    },

    get_new_item(item) {
      const new_item = { ...item };
      if (!item.qty) {
        item.qty = 1;
      }
      if (!item.posa_is_offer) {
        item.posa_is_offer = 0;
      }
      if (!item.posa_is_replace) {
        item.posa_is_replace = "";
      }
      new_item.stock_qty = item.qty;
      new_item.discount_amount = 0;
      new_item.discount_percentage = 0;
      new_item.discount_amount_per_item = 0;
      new_item.price_list_rate = item.rate;
      new_item.qty = item.qty;
      new_item.uom = item.uom ? item.uom : item.stock_uom;
      new_item.actual_batch_qty = "";
      new_item.conversion_factor = 1;
      new_item.posa_offers = JSON.stringify([]);
      new_item.posa_offer_applied = 0;
      new_item.posa_is_offer = item.posa_is_offer;
      new_item.posa_is_replace = item.posa_is_replace || null;
      new_item.is_free_item = 0;
      new_item.posa_notes = "";
      new_item.posa_delivery_date = "";
      new_item.posa_row_id = this.makeid(20);
      if (
        (!this.pos_profile.posa_auto_set_batch && new_item.has_batch_no) ||
        new_item.has_serial_no
      ) {
        this.expanded.push(new_item);
      }
      return new_item;
    },

    cancel_invoice() {
      const doc = this.get_invoice_doc();
      this.invoiceType = this.pos_profile.posa_default_sales_order
        ? "Order"
        : "Invoice";
      this.invoiceTypes = ["Invoice", "Order"];
      this.posting_date = frappe.datetime.nowdate();
      if (doc.name && this.pos_profile.posa_allow_delete) {
        frappe.call({
          method: "posawesome.posawesome.api.posapp.delete_invoice",
          args: { invoice: doc.name },
          async: true,
          callback: function (r) {
            if (r.message) {
              evntBus.$emit("show_mesage", {
                text: r.message,
                color: "warning",
              });
            }
          },
        });
      }
      this.items = [];
      this.posa_offers = [];
      evntBus.$emit("set_pos_coupons", []);
      this.posa_coupons = [];
      this.customer = this.pos_profile.customer;
      this.invoice_doc = "";
      this.return_doc = "";
      this.discount_amount = 0;
      this.additional_discount_percentage = 0;
      this.delivery_charges_rate = 0;
      this.selcted_delivery_charges = {};
      evntBus.$emit("set_customer_readonly", false);
      this.cancel_dialog = false;
    },

    new_invoice(data = {}) {
      let old_invoice = null;
      evntBus.$emit("set_customer_readonly", false);
      this.expanded = [];
      this.posa_offers = [];
      evntBus.$emit("set_pos_coupons", []);
      this.posa_coupons = [];
      this.return_doc = "";

      const doc = this.get_invoice_doc();

      // Check if doc has name or items
      if (doc.name || doc.items.length) {
        old_invoice = this.update_invoice(doc);

	        if (
	          old_invoice &&
	          old_invoice.docstatus === 0 &&
	          this.pos_profile.custom_have_token === 1
	        ) {
	          const token = this.get_explicit_token_ref(old_invoice);
	          if (!token) return;
	          const posting_date = frappe.datetime.str_to_user(old_invoice.posting_date);
          const posting_time =
            old_invoice.posting_time?.split(".")[0] || frappe.datetime.now_time();

          const d = new frappe.ui.Dialog({
            title: "Token",
            fields: [
              {
                fieldname: "token",
                fieldtype: "HTML",
                options: `<div style="text-align:center;font-size:48px;padding:1rem 0;"><b>${token}</b></div>`,
              },
              {
                fieldname: "relay_note",
                fieldtype: "HTML",
                options: `<div style="text-align:center;color:#1e88e5;padding-bottom:0.5rem;"><small>${frappe._(
                  "Relay workflow enabled for this POS Profile"
                )}</small></div>`,
              },
            ],
            primary_action_label: "Print",
            primary_action() {
              const print_window = window.open("", "", "height=600,width=400");

              print_window.document.write(`
                <html>
                  <head>
                    <title>Token Print</title>
                    <style>
                      @media screen {
                        body {
                          width: 4in;
                          padding: 0.25in;
                          min-height: 8in;
                          font-family: Arial, sans-serif;
                          text-align: center;
                          margin: 0 auto;
                        }
                      }
                      @media print {
                        body {
                          width: 4in;
                          padding: 0.25in;
                          min-height: 8in;
                          font-family: Arial, sans-serif;
                          text-align: center;
                          margin: 0 auto;
                        }
                      }
                      .token {
                        font-size: 60px;
                        font-weight: bold;
                        margin: 2rem 0;
                      }
                      .meta {
                        font-size: 16px;
                        margin-bottom: 1.5rem;
                      }
                    </style>
                  </head>
                  <body>
                    <div class="meta">
                      <p><b>Date:</b> ${posting_date}</p>
                      <p><b>Time:</b> ${posting_time}</p>
                    </div>
                    <div class="token">${token}</div>
                  </body>
                </html>
              `);

              print_window.document.close();
              print_window.focus();
              print_window.print();
              print_window.close();
            },
          });

          d.show();
        }
      }

      // Continue resetting form if it's not a return
      if (!data.name && !data.is_return) {
        this.items = [];
        this.customer = this.pos_profile.customer;
        this.invoice_doc = "";
        this.discount_amount = 0;
        this.additional_discount_percentage = 0;
        this.invoiceType = this.pos_profile.posa_default_sales_order
          ? "Order"
          : "Invoice";
        this.invoiceTypes = ["Invoice", "Order"];
      } else {
        if (data.is_return) {
          evntBus.$emit("set_customer_readonly", true);
          this.invoiceType = "Return";
          this.invoiceTypes = ["Return"];
        }
        this.invoice_doc = data;
        this.items = data.items;
        if (!data.relay_offline_order) {
          this.update_items_details(this.items);
        }
        this.posa_offers = data.posa_offers || [];
        this.items.forEach((item) => {
          if (!item.posa_row_id) item.posa_row_id = this.makeid(20);
          if (item.batch_no) this.set_batch_qty(item, item.batch_no);
        });
        this.customer = data.customer;
        this.posting_date = data.posting_date || frappe.datetime.nowdate();
        this.discount_amount = data.discount_amount;
        this.additional_discount_percentage = data.additional_discount_percentage;

        this.items.forEach((item) => {
          if (item.serial_no) {
            item.serial_no_selected = [];
            const serial_list = item.serial_no.split("\n");
            serial_list.forEach((element) => {
              if (element.length) item.serial_no_selected.push(element);
            });
            item.serial_no_selected_count = item.serial_no_selected.length;
          }
        });
      }

      return old_invoice;
    },

    async new_order(data = {}) {
      let old_invoice = null;
      evntBus.$emit("set_customer_readonly", false);
      this.expanded = [];
      this.posa_offers = [];
      evntBus.$emit("set_pos_coupons", []);
      this.posa_coupons = [];
      this.return_doc = "";
      if (!data.name && !data.is_return) {
        this.items = [];
        this.customer = this.pos_profile.customer;
        this.invoice_doc = "";
        this.discount_amount = 0;
        this.additional_discount_percentage = 0;
        this.invoiceType = "Invoice";
        this.invoiceTypes = ["Invoice", "Order"];
      } else {
        if (data.is_return) {
          evntBus.$emit("set_customer_readonly", true);
          this.invoiceType = "Return";
          this.invoiceTypes = ["Return"];
        }
        this.invoice_doc = data;
        this.items = data.items;
        this.update_items_details(this.items);
        this.posa_offers = data.posa_offers || [];
        this.items.forEach((item) => {
          if (!item.posa_row_id) {
            item.posa_row_id = this.makeid(20);
          }
          if (item.batch_no) {
            this.set_batch_qty(item, item.batch_no);
          }
        });
        this.customer = data.customer;
        this.posting_date = data.posting_date || frappe.datetime.nowdate();
        this.discount_amount = data.discount_amount;
        this.additional_discount_percentage =
          data.additional_discount_percentage;
        this.items.forEach((item) => {
          if (item.serial_no) {
            item.serial_no_selected = [];
            const serial_list = item.serial_no.split("\n");
            serial_list.forEach((element) => {
              if (element.length) {
                item.serial_no_selected.push(element);
              }
            });
            item.serial_no_selected_count = item.serial_no_selected.length;
          }
        });
      }
      return old_invoice;
    },

    get_invoice_doc() {
      let doc = {};
      if (this.invoice_doc.name) {
        doc = { ...this.invoice_doc };
      }
      doc.doctype = "Sales Invoice";
      doc.is_pos = 1;
      doc.ignore_pricing_rule = 1;
      doc.company = doc.company || this.pos_profile.company;
      doc.pos_profile = doc.pos_profile || this.pos_profile.name;
      doc.campaign = doc.campaign || this.pos_profile.campaign;
      doc.currency = doc.currency || this.pos_profile.currency;
      doc.naming_series = doc.naming_series || this.pos_profile.naming_series;
      doc.customer = this.customer;
      doc.items = this.get_invoice_items();
      doc.total = this.subtotal;
      doc.discount_amount = flt(this.discount_amount);
      doc.additional_discount_percentage = flt(
        this.additional_discount_percentage
      );
      doc.posa_pos_opening_shift = this.pos_opening_shift.name;
      doc.payments = this.get_payments();
      doc.taxes = [];
      doc.is_return = this.invoice_doc.is_return;
      doc.return_against = this.invoice_doc.return_against;
      doc.posa_offers = this.posa_offers;
      doc.posa_coupons = this.posa_coupons;
      doc.posa_delivery_charges = this.selcted_delivery_charges.name;
      doc.posa_delivery_charges_rate = this.delivery_charges_rate || 0;
      doc.posting_date = this.posting_date;
      return doc;
    },

    async get_invoice_from_order_doc() {
      let doc = {};
      if (this.invoice_doc && this.invoice_doc.relay_offline_order) {
        const tokenId = String(
          this.invoice_doc.token_id ||
            this.invoice_doc.sales_order ||
            this.invoice_doc.sales_order_name ||
            this.invoice_doc.name ||
            ""
        ).trim();
        doc = {
          ...this.invoice_doc,
          name: "",
          doctype: "Sales Invoice",
          docstatus: 0,
          is_pos: 1,
          update_stock: 1,
          customer: this.customer,
          customer_name:
            (this.customer_info && this.customer_info.customer_name) ||
            this.invoice_doc.customer_name ||
            this.customer,
          company: this.pos_profile.company,
          pos_profile: this.pos_profile.name,
          currency: this.pos_profile.currency,
          token_id: tokenId,
          sales_order: tokenId,
          sales_order_name: tokenId,
        };
      } else if (this.invoice_doc.doctype == "Sales Order") {
        await frappe.call({
          method:
            "posawesome.posawesome.api.posapp.create_sales_invoice_from_order",
          args: {
            sales_order: this.invoice_doc.name,
          },
          // async: false,
          callback: function (r) {
            if (r.message) {
              doc = r.message;
            }
          },
        });
      } else {
        doc = this.invoice_doc;
      }
      const Items = [];
      const updatedItemsData = this.get_invoice_items();
      doc.items.forEach((item) => {
        const updatedData = updatedItemsData.find(
          (updatedItem) => updatedItem.item_code === item.item_code
        );
        if (updatedData) {
          item.item_code = updatedData.item_code;
          item.posa_row_id = updatedData.posa_row_id;
          item.posa_offers = updatedData.posa_offers;
          item.posa_offer_applied = updatedData.posa_offer_applied;
          item.posa_is_offer = updatedData.posa_is_offer;
          item.posa_is_replace = updatedData.posa_is_replace;
          item.is_free_item = updatedData.is_free_item;
          item.qty = flt(updatedData.qty);
          item.rate = flt(updatedData.rate);
          item.uom = updatedData.uom;
          item.amount = flt(updatedData.qty) * flt(updatedData.rate);
          item.conversion_factor = updatedData.conversion_factor;
          item.serial_no = updatedData.serial_no;
          item.discount_percentage = flt(updatedData.discount_percentage);
          item.discount_amount = flt(updatedData.discount_amount);
          item.batch_no = updatedData.batch_no;
          item.posa_notes = updatedData.posa_notes;
          item.posa_delivery_date = updatedData.posa_delivery_date;
          item.price_list_rate = updatedData.price_list_rate;
          Items.push(item);
        }
      });

      doc.items = Items;
      const newItems = [...doc.items];
      const existingItemCodes = new Set(newItems.map((item) => item.item_code));
      updatedItemsData.forEach((updatedItem) => {
        if (!existingItemCodes.has(updatedItem.item_code)) {
          newItems.push(updatedItem);
        }
      });
      const tokenId = String(
        (this.invoice_doc &&
          (this.invoice_doc.token_id ||
            this.invoice_doc.sales_order ||
            this.invoice_doc.sales_order_name ||
            this.invoice_doc.name)) ||
          ""
      ).trim();
      if (this.invoice_doc && this.invoice_doc.relay_offline_order && tokenId) {
        newItems.forEach((item) => {
          item.sales_order = item.sales_order || tokenId;
        });
        doc.token_id = doc.token_id || tokenId;
        doc.sales_order = doc.sales_order || tokenId;
        doc.sales_order_name = doc.sales_order_name || tokenId;
      }
      doc.items = newItems;
      doc.update_stock = 1;
      doc.is_pos = 1;
      doc.payments = this.get_payments();
      return doc;
    },

    get_invoice_items() {
      const items_list = [];
      this.items.forEach((item) => {
        const new_item = {
          item_code: item.item_code,
          posa_row_id: item.posa_row_id,
          posa_offers: item.posa_offers,
          posa_offer_applied: item.posa_offer_applied,
          posa_is_offer: item.posa_is_offer,
          posa_is_replace: item.posa_is_replace,
          is_free_item: item.is_free_item,
          qty: flt(item.qty),
          rate: flt(item.rate),
          uom: item.uom,
          amount: flt(item.qty) * flt(item.rate),
          conversion_factor: item.conversion_factor,
          serial_no: item.serial_no,
          discount_percentage: flt(item.discount_percentage),
          discount_amount: flt(item.discount_amount),
          batch_no: item.batch_no,
          posa_notes: item.posa_notes,
          posa_delivery_date: item.posa_delivery_date,
          price_list_rate: item.price_list_rate,
        };
        items_list.push(new_item);
      });

      return items_list;
    },

    get_order_items() {
      const items_list = [];
      this.items.forEach((item) => {
        const new_item = {
          item_code: item.item_code,
          posa_row_id: item.posa_row_id,
          posa_offers: item.posa_offers,
          posa_offer_applied: item.posa_offer_applied,
          posa_is_offer: item.posa_is_offer,
          posa_is_replace: item.posa_is_replace,
          is_free_item: item.is_free_item,
          qty: flt(item.qty),
          rate: flt(item.rate),
          uom: item.uom,
          amount: flt(item.qty) * flt(item.rate),
          conversion_factor: item.conversion_factor,
          serial_no: item.serial_no,
          discount_percentage: flt(item.discount_percentage),
          discount_amount: flt(item.discount_amount),
          batch_no: item.batch_no,
          posa_notes: item.posa_notes,
          posa_delivery_date: item.posa_delivery_date,
          price_list_rate: item.price_list_rate,
        };
        items_list.push(new_item);
      });

      return items_list;
    },

    get_payments() {
      const payments = [];
      this.pos_profile.payments.forEach((payment) => {
        payments.push({
          amount: 0,
          mode_of_payment: payment.mode_of_payment,
          default: payment.default,
          account: "",
        });
      });
      return payments;
    },

    update_invoice(doc) {
      const vm = this;
      frappe.call({
        method: "posawesome.posawesome.api.posapp.update_invoice",
        args: { data: doc },
        async: false,
        callback: function (r) {
          if (r.message) {
            vm.invoice_doc = r.message;
          }
        },
      });

	      const relayEnabled = parseInt(this.pos_profile.custom_have_token || 0, 10) === 1;
	      const relayBaseUrl = this.get_relay_base_url();
	      if (relayEnabled && relayBaseUrl && this.invoice_doc && this.invoice_doc.docstatus === 0) {
	        const tokenId = this.get_explicit_token_ref(this.invoice_doc);
	        if (!tokenId) return this.invoice_doc;
	        const tokenPayload = {
	          token_id: tokenId,
	          pos_profile_id: this.pos_profile.name,
          cashier_user_id: frappe.session.user,
          role: this.current_role || this.get_current_role() || "",
          customer_id: this.invoice_doc.customer,
          customer_name: this.invoice_doc.customer_name,
          items: (this.invoice_doc.items || []).map((row) => ({
            item_code: row.item_code,
            item_name: row.item_name,
            qty: row.qty,
            uom: row.uom,
            rate: row.rate,
            amount: row.amount,
          })),
        };

        fetch(`${relayBaseUrl.replace(/\/$/, "")}/relay/token/create`, {
          method: "POST",
          headers: this.get_relay_client_headers({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(tokenPayload),
        }).catch(() => {
          // non-blocking: token sync is best-effort at draft stage
        });
      }
      return this.invoice_doc;
    },

    update_invoice_from_order(doc) {
      const vm = this;
      frappe.call({
        method: "posawesome.posawesome.api.posapp.update_invoice_from_order",
        args: {
          data: doc,
        },
        async: false,
        callback: function (r) {
          if (r.message) {
            vm.invoice_doc = r.message;
          }
        },
      });
      return this.invoice_doc;
    },

    process_invoice() {
      const doc = this.get_invoice_doc();
      if (doc.name) {
        return this.update_invoice(doc);
      } else {
        return this.update_invoice(doc);
      }
    },

    async process_invoice_from_order() {
      const doc = await this.get_invoice_from_order_doc();
      if (this.invoice_doc && this.invoice_doc.relay_offline_order) {
        return doc;
      }
      var up_invoice;
      if (doc.name) {
        up_invoice = await this.update_invoice_from_order(doc);
        return up_invoice;
      } else {
        return this.update_invoice_from_order(doc);
      }
    },

    async show_payment() {
      this.current_role = this.get_current_role();
      if (this.is_sales_associate_role) {
        evntBus.$emit("show_mesage", {
          text: __(
            "Sales Associate can prepare the cart and token, but payment must be done by a Cashier."
          ),
          color: "warning",
        });
        frappe.utils.play_sound("error");
        return;
      }
      if (!this.customer) {
        evntBus.$emit("show_mesage", {
          text: __(`There is no Customer !`),
          color: "error",
        });
        return;
      }
      if (!this.items.length) {
        evntBus.$emit("show_mesage", {
          text: __(`There is no Items !`),
          color: "error",
        });
        return;
      }
      if (!this.validate()) {
        return;
      }
      if (this.invoice_doc.doctype == "Sales Order") {
        evntBus.$emit("show_payment", "true");
        const invoice_doc = await this.process_invoice_from_order();
        evntBus.$emit("send_invoice_doc_payment", invoice_doc);
      } else if (this.invoice_doc.doctype == "Sales Invoice") {
        const sales_invoice_item = this.invoice_doc.items[0];
        var sales_invoice_item_doc = {};
        frappe.call({
          method:
            "posawesome.posawesome.api.posapp.get_sales_invoice_child_table",
          args: {
            sales_invoice: this.invoice_doc.name,
            sales_invoice_item: sales_invoice_item.name,
          },
          async: false,
          callback: function (r) {
            if (r.message) {
              sales_invoice_item_doc = r.message;
            }
          },
        });
        if (sales_invoice_item_doc.sales_order) {
          evntBus.$emit("show_payment", "true");
          const invoice_doc = await this.process_invoice_from_order();
          evntBus.$emit("send_invoice_doc_payment", invoice_doc);
        } else {
          evntBus.$emit("show_payment", "true");
          const invoice_doc = this.process_invoice();
          evntBus.$emit("send_invoice_doc_payment", invoice_doc);
        }
      } else {
        evntBus.$emit("show_payment", "true");
        const invoice_doc = this.process_invoice();
        evntBus.$emit("send_invoice_doc_payment", invoice_doc);
      }
    },

    validate() {
      let value = true;
      this.items.forEach((item) => {
        if (
          this.pos_profile.posa_max_discount_allowed &&
          !item.posa_offer_applied
        ) {
          if (item.discount_amount && this.flt(item.discount_amount) > 0) {
            // calc discount percentage
            const discount_percentage =
              (this.flt(item.discount_amount) * 100) /
              this.flt(item.price_list_rate);
            if (
              discount_percentage > this.pos_profile.posa_max_discount_allowed
            ) {
              evntBus.$emit("show_mesage", {
                text: __(
                  `Discount percentage for item '{0}' cannot be greater than {1}%`,
                  [item.item_name, this.pos_profile.posa_max_discount_allowed]
                ),
                color: "error",
              });
              value = false;
            }
          }
        }
        if (this.stock_settings.allow_negative_stock != 1) {
          if (
            this.invoiceType == "Invoice" &&
            ((item.is_stock_item && item.stock_qty && !item.actual_qty) ||
              (item.is_stock_item && item.stock_qty > item.actual_qty))
          ) {
            evntBus.$emit("show_mesage", {
              text: __(
                `The existing quantity '{0}' for item '{1}' is not enough`,
                [item.actual_qty, item.item_name]
              ),
              color: "error",
            });
            value = false;
          }
        }
        if (item.qty == 0) {
          evntBus.$emit("show_mesage", {
            text: __(`Quantity for item '{0}' cannot be Zero (0)`, [
              item.item_name,
            ]),
            color: "error",
          });
          value = false;
        }
        if (
          item.max_discount > 0 &&
          item.discount_percentage > item.max_discount
        ) {
          evntBus.$emit("show_mesage", {
            text: __(`Maximum discount for Item {0} is {1}%`, [
              item.item_name,
              item.max_discount,
            ]),
            color: "error",
          });
          value = false;
        }
        if (item.has_serial_no) {
          if (
            !this.invoice_doc.is_return &&
            (!item.serial_no_selected ||
              item.stock_qty != item.serial_no_selected.length)
          ) {
            evntBus.$emit("show_mesage", {
              text: __(`Selected serial numbers of item {0} is incorrect`, [
                item.item_name,
              ]),
              color: "error",
            });
            value = false;
          }
        }
        if (item.has_batch_no) {
          if (item.stock_qty > item.actual_batch_qty) {
            evntBus.$emit("show_mesage", {
              text: __(
                `The existing batch quantity of item {0} is not enough`,
                [item.item_name]
              ),
              color: "error",
            });
            value = false;
          }
        }
        if (this.pos_profile.posa_allow_user_to_edit_additional_discount) {
          const clac_percentage = (this.discount_amount / this.Total) * 100;
          if (clac_percentage > this.pos_profile.posa_max_discount_allowed) {
            evntBus.$emit("show_mesage", {
              text: __(`The discount should not be higher than {0}%`, [
                this.pos_profile.posa_max_discount_allowed,
              ]),
              color: "error",
            });
            value = false;
          }
        }
        if (this.invoice_doc.is_return) {
          if (this.subtotal >= 0) {
            evntBus.$emit("show_mesage", {
              text: __(`Return Invoice Total Not Correct`),
              color: "error",
            });
            value = false;
            return value;
          }
          if (Math.abs(this.subtotal) > Math.abs(this.return_doc.total)) {
            evntBus.$emit("show_mesage", {
              text: __(`Return Invoice Total should not be higher than {0}`, [
                this.return_doc.total,
              ]),
              color: "error",
            });
            value = false;
            return value;
          }
          this.items.forEach((item) => {
            const return_item = this.return_doc.items.find(
              (element) => element.item_code == item.item_code
            );

            if (!return_item) {
              evntBus.$emit("show_mesage", {
                text: __(
                  `The item {0} cannot be returned because it is not in the invoice {1}`,
                  [item.item_name, this.return_doc.name]
                ),
                color: "error",
              });
              value = false;
              return value;
            } else if (
              Math.abs(item.qty) > Math.abs(return_item.qty) ||
              Math.abs(item.qty) == 0
            ) {
              evntBus.$emit("show_mesage", {
                text: __(`The QTY of the item {0} cannot be greater than {1}`, [
                  item.item_name,
                  return_item.qty,
                ]),
                color: "error",
              });
              value = false;
              return value;
            }
          });
        }
      });
      return value;
    },

    get_draft_invoices() {
      const vm = this;
      frappe.call({
        method: "posawesome.posawesome.api.posapp.get_draft_invoices",
        args: {
          pos_opening_shift: this.pos_opening_shift.name,
        },
        async: false,
        callback: function (r) {
          if (r.message) {
            evntBus.$emit("open_drafts", r.message);
          }
        },
      });
    },

    get_draft_orders() {
      const vm = this;
      const policy = this.so_lookup_policy();
      frappe.call({
        method: "posawesome.posawesome.api.posapp.search_orders",
        args: {
          company: this.pos_profile.company,
          currency: this.pos_profile.currency,
          pos_profile: this.pos_profile.name,
          days_back: policy.maxAgeDays,
          allow_stale: policy.allowStale ? 1 : 0,
          history_days: policy.historyDays,
        },
        async: true,
        callback: async function (r) {
          if (r && !r.exc && r.message) {
            const cloudRows = Array.isArray(r.message) ? r.message : [];
            if (cloudRows.length > 0) {
              let rows = cloudRows;
              if (vm.relayWorkflowEnabled() && vm.get_relay_base_url()) {
                try {
                  const relayRows = await vm.fetch_open_orders_from_relay("");
                  rows = vm.merge_sales_order_rows(cloudRows, relayRows);
                } catch (e) {
                  rows = cloudRows;
                }
              }
              evntBus.$emit("open_orders", rows);
              if (cloudRows.some((row) => Number(row && row.is_stale ? 1 : 0) === 1)) {
                evntBus.$emit("show_mesage", {
                  text: __("Some Sales Orders are stale (allowed by profile policy)."),
                  color: "warning",
                });
              }
              return;
            }
            if (!vm.relayWorkflowEnabled() || !vm.get_relay_base_url()) {
              evntBus.$emit("open_orders", cloudRows);
              return;
            }
          }
          if (!vm.relayWorkflowEnabled() || !vm.get_relay_base_url()) {
            evntBus.$emit("show_mesage", {
              text: __("Unable to load Sales Orders."),
              color: "error",
            });
            return;
          }
          try {
            const relayRows = await vm.fetch_open_orders_from_relay("");
            evntBus.$emit("open_orders", relayRows);
            evntBus.$emit("show_mesage", {
              text: __("Loaded Sales Orders from local relay (cloud unavailable)."),
              color: "warning",
            });
            if (relayRows.some((row) => Number(row && row.is_stale ? 1 : 0) === 1)) {
              evntBus.$emit("show_mesage", {
                text: __("Some Sales Orders are stale (allowed by profile policy)."),
                color: "warning",
              });
            }
          } catch (e) {
            evntBus.$emit("show_mesage", {
              text: (e && e.message) || __("Unable to load Sales Orders from relay."),
              color: "error",
            });
          }
        },
        error: async function () {
          if (!vm.relayWorkflowEnabled() || !vm.get_relay_base_url()) {
            evntBus.$emit("show_mesage", {
              text: __("Unable to load Sales Orders."),
              color: "error",
            });
            return;
          }
          try {
            const relayRows = await vm.fetch_open_orders_from_relay("");
            evntBus.$emit("open_orders", relayRows);
            evntBus.$emit("show_mesage", {
              text: __("Loaded Sales Orders from local relay (cloud unavailable)."),
              color: "warning",
            });
          } catch (e) {
            evntBus.$emit("show_mesage", {
              text: (e && e.message) || __("Unable to load Sales Orders from relay."),
              color: "error",
            });
          }
        },
      });
    },
    get_draft_quotations() {
      const vm = this;
      if (!this.can_use_quotation_actions) {
        evntBus.$emit("show_mesage", {
          text: __("Quotation actions are disabled for this role/profile."),
          color: "warning",
        });
        return;
      }
      const policy = this.so_lookup_policy();
      frappe.call({
        method: "posawesome.posawesome.api.posapp.search_quotations",
        args: {
          company: this.pos_profile.company,
          currency: this.pos_profile.currency,
          pos_profile: this.pos_profile.name,
          allow_stale: policy.allowStale ? 1 : 0,
          history_days: policy.historyDays,
        },
        async: true,
        callback: async function (r) {
          if (r && !r.exc && r.message) {
            const cloudRows = Array.isArray(r.message) ? r.message : [];
            if (cloudRows.length > 0 || !vm.relayWorkflowEnabled() || !vm.get_relay_base_url()) {
              evntBus.$emit("open_quotations", cloudRows);
              return;
            }
          }
          if (!vm.relayWorkflowEnabled() || !vm.get_relay_base_url()) {
            evntBus.$emit("show_mesage", {
              text: __("Unable to load Quotations."),
              color: "error",
            });
            return;
          }
          try {
            const relayRows = await vm.fetch_quotes_from_relay("");
            evntBus.$emit("open_quotations", relayRows.map((row) => ({ ...row, relay_offline_quote: 1 })));
            evntBus.$emit("show_mesage", {
              text: __("Loaded Quotations from local relay (cloud unavailable)."),
              color: "warning",
            });
          } catch (e) {
            evntBus.$emit("show_mesage", {
              text: (e && e.message) || __("Unable to load Quotations from relay."),
              color: "error",
            });
          }
        },
        error: async function () {
          if (!vm.relayWorkflowEnabled() || !vm.get_relay_base_url()) {
            evntBus.$emit("show_mesage", {
              text: __("Unable to load Quotations."),
              color: "error",
            });
            return;
          }
          try {
            const relayRows = await vm.fetch_quotes_from_relay("");
            evntBus.$emit("open_quotations", relayRows.map((row) => ({ ...row, relay_offline_quote: 1 })));
            evntBus.$emit("show_mesage", {
              text: __("Loaded Quotations from local relay (cloud unavailable)."),
              color: "warning",
            });
          } catch (e) {
            evntBus.$emit("show_mesage", {
              text: (e && e.message) || __("Unable to load Quotations from relay."),
              color: "error",
            });
          }
        },
      });
    },

    open_returns() {
      evntBus.$emit("open_returns", this.pos_profile.company);
    },

    close_payments() {
      evntBus.$emit("show_payment", "false");
    },

    update_items_details(items) {
      if (!items.length > 0) {
        return;
      }
      const vm = this;
      if (!vm.pos_profile) return;
      frappe.call({
        method: "posawesome.posawesome.api.posapp.get_items_details",
        async: false,
        args: {
          pos_profile: vm.pos_profile,
          items_data: items,
        },
        callback: function (r) {
          if (r.message) {
            items.forEach((item) => {
              const updated_item = r.message.find(
                (element) => element.posa_row_id == item.posa_row_id
              );
              item.actual_qty = updated_item.actual_qty;
              item.serial_no_data = updated_item.serial_no_data;
              item.batch_no_data = updated_item.batch_no_data;
              item.item_uoms = updated_item.item_uoms;
              item.has_batch_no = updated_item.has_batch_no;
              item.has_serial_no = updated_item.has_serial_no;
            });
          }
        },
      });
    },

    update_item_detail(item) {
      if (!item.item_code || this.invoice_doc.is_return) {
        return;
      }
      const vm = this;
      frappe.call({
        method: "posawesome.posawesome.api.posapp.get_item_detail",
        args: {
          warehouse: this.pos_profile.warehouse,
          doc: this.get_invoice_doc(),
          price_list: this.pos_profile.price_list,
          item: {
            item_code: item.item_code,
            customer: this.customer,
            doctype: "Sales Invoice",
            name: "New Sales Invoice 1",
            company: this.pos_profile.company,
            conversion_rate: 1,
            qty: item.qty,
            price_list_rate: item.price_list_rate,
            child_docname: "New Sales Invoice Item 1",
            cost_center: this.pos_profile.cost_center,
            currency: this.pos_profile.currency,
            // plc_conversion_rate: 1,
            pos_profile: this.pos_profile.name,
            uom: item.uom,
            tax_category: "",
            transaction_type: "selling",
            update_stock: this.pos_profile.update_stock,
            price_list: this.get_price_list(),
            has_batch_no: item.has_batch_no,
            serial_no: item.serial_no,
            batch_no: item.batch_no,
            is_stock_item: item.is_stock_item,
          },
        },
        callback: function (r) {
          if (r.message) {
            const data = r.message;
            if (data.batch_no_data) {
              item.batch_no_data = data.batch_no_data;
            }
            if (
              item.has_batch_no &&
              vm.pos_profile.posa_auto_set_batch &&
              !item.batch_no &&
              data.batch_no_data
            ) {
              item.batch_no_data = data.batch_no_data;
              vm.set_batch_qty(item, item.batch_no, false);
            }
            if (data.has_pricing_rule) {
            } else if (
              vm.pos_profile.posa_apply_customer_discount &&
              vm.customer_info.posa_discount > 0 &&
              vm.customer_info.posa_discount <= 100
            ) {
              if (
                item.posa_is_offer == 0 &&
                !item.posa_is_replace &&
                item.posa_offer_applied == 0
              ) {
                if (item.max_discount > 0) {
                  item.discount_percentage =
                    item.max_discount < vm.customer_info.posa_discount
                      ? item.max_discount
                      : vm.customer_info.posa_discount;
                } else {
                  item.discount_percentage = vm.customer_info.posa_discount;
                }
              }
            }
            if (!item.batch_price) {
              if (
                !item.is_free_item &&
                !item.posa_is_offer &&
                !item.posa_is_replace
              ) {
                item.price_list_rate = data.price_list_rate;
              }
            }
            item.last_purchase_rate = data.last_purchase_rate;
            item.projected_qty = data.projected_qty;
            item.reserved_qty = data.reserved_qty;
            item.conversion_factor = data.conversion_factor;
            item.stock_qty = data.stock_qty;
            item.actual_qty = data.actual_qty;
            item.stock_uom = data.stock_uom;
            (item.has_serial_no = data.has_serial_no),
              (item.has_batch_no = data.has_batch_no),
              vm.calc_item_price(item);
          }
        },
      });
    },

    fetch_customer_details() {
      const vm = this;
      if (this.customer) {
        if (
          String(this.customer || "").startsWith("LCUST-") &&
          this.relay_customer_fallback_enabled()
        ) {
          this.fetch_customer_details_from_relay().then((loaded) => {
            if (!loaded) {
              vm.update_price_list();
            }
          });
          return;
        }
        frappe.call({
          method: "posawesome.posawesome.api.posapp.get_customer_info",
          args: {
            customer: vm.customer,
          },
          async: false,
          callback: (r) => {
            const message = r.message;
            if (!r.exc && message) {
              vm.customer_info = {
                ...message,
              };
              vm.update_price_list();
              return;
            }
            vm.fetch_customer_details_from_relay().then((loaded) => {
              if (!loaded) {
                vm.update_price_list();
              }
            });
          },
          error: () => {
            vm.fetch_customer_details_from_relay().then((loaded) => {
              if (!loaded) {
                vm.update_price_list();
              }
            });
          },
        });
      }
    },

    get_price_list() {
      let price_list = this.pos_profile.selling_price_list;
      if (this.customer_info && this.pos_profile) {
        const { customer_price_list, customer_group_price_list } =
          this.customer_info;
        const pos_price_list = this.pos_profile.selling_price_list;
        if (customer_price_list && customer_price_list != pos_price_list) {
          price_list = customer_price_list;
        } else if (
          customer_group_price_list &&
          customer_group_price_list != pos_price_list
        ) {
          price_list = customer_group_price_list;
        }
      }
      return price_list;
    },

    update_price_list() {
      let price_list = this.get_price_list();
      if (price_list == this.pos_profile.selling_price_list) {
        price_list = null;
      }
      evntBus.$emit("update_customer_price_list", price_list);
    },
    update_discount_umount() {
      const value = flt(this.additional_discount_percentage);
      if (value >= -100 && value <= 100) {
        this.discount_amount = (this.Total * value) / 100;
      } else {
        this.additional_discount_percentage = 0;
        this.discount_amount = 0;
      }
    },

    updateItemQty(item, value) {
      const normalized = this.normalizeFixedPrecisionNumber(value, 2, false, flt(item.qty || 0));
      this.setFormatedFloat(item, "qty", 2, false, normalized);
      this.calc_stock_qty(item, normalized);
    },

    updateItemRate(item, value) {
      const normalized = this.normalizeFixedPrecisionNumber(value, 2, false, flt(item.rate || 0));
      this.setFormatedCurrency(item, "rate", 2, false, normalized);
      this.calc_prices(item, normalized, "rate");
    },

    calc_prices(item, value, fieldName) {
      const activeField =
        fieldName ||
        (((typeof event !== "undefined" && event && event.target) || {}).id ? event.target.id : "");
      if (activeField === "rate") {
        item.discount_percentage = 0;
        if (value < item.price_list_rate) {
          item.discount_amount = this.flt(
            this.flt(item.price_list_rate) - flt(value),
            this.currency_precision
          );
        } else if (value < 0) {
          item.rate = item.price_list_rate;
          item.discount_amount = 0;
        } else if (value > item.price_list_rate) {
          item.discount_amount = 0;
        }
      } else if (activeField === "discount_amount") {
        if (value < 0) {
          item.discount_amount = 0;
          item.discount_percentage = 0;
        } else {
          item.rate = flt(item.price_list_rate) - flt(value);
          item.discount_percentage = 0;
        }
      } else if (activeField === "discount_percentage") {
        if (value < 0) {
          item.discount_amount = 0;
          item.discount_percentage = 0;
        } else {
          item.rate = this.flt(
            flt(item.price_list_rate) -
              (flt(item.price_list_rate) * flt(value)) / 100,
            this.currency_precision
          );
          item.discount_amount = this.flt(
            flt(item.price_list_rate) - flt(+item.rate),
            this.currency_precision
          );
        }
      }
    },

    calc_item_price(item) {
      if (!item.posa_offer_applied) {
        if (item.price_list_rate) {
          item.rate = item.price_list_rate;
        }
      }
      if (item.discount_percentage) {
        item.rate =
          flt(item.price_list_rate) -
          (flt(item.price_list_rate) * flt(item.discount_percentage)) / 100;
        item.discount_amount = this.flt(
          flt(item.price_list_rate) - flt(item.rate),
          this.currency_precision
        );
      } else if (item.discount_amount) {
        item.rate = this.flt(
          flt(item.price_list_rate) - flt(item.discount_amount),
          this.currency_precision
        );
      }
    },

    calc_uom(item, value) {
      const new_uom = item.item_uoms.find((element) => element.uom == value);
      item.conversion_factor = new_uom.conversion_factor;
      if (!item.posa_offer_applied) {
        item.discount_amount = 0;
        item.discount_percentage = 0;
      }
      if (item.batch_price) {
        item.price_list_rate = item.batch_price * new_uom.conversion_factor;
      }
      this.update_item_detail(item);
    },

    calc_stock_qty(item, value) {
      item.stock_qty = item.conversion_factor * value;
    },

    set_serial_no(item) {
      if (!item.has_serial_no) return;
      item.serial_no = "";
      item.serial_no_selected.forEach((element) => {
        item.serial_no += element + "\n";
      });
      item.serial_no_selected_count = item.serial_no_selected.length;
      if (item.serial_no_selected_count != item.stock_qty) {
        item.qty = item.serial_no_selected_count;
        this.calc_stock_qty(item, item.qty);
        this.$forceUpdate();
      }
    },

    set_batch_qty(item, value, update = true) {
      const existing_items = this.items.filter(
        (element) =>
          element.item_code == item.item_code &&
          element.posa_row_id != item.posa_row_id
      );
      const used_batches = {};
      item.batch_no_data.forEach((batch) => {
        used_batches[batch.batch_no] = {
          ...batch,
          used_qty: 0,
          remaining_qty: batch.batch_qty,
        };
        existing_items.forEach((element) => {
          if (element.batch_no && element.batch_no == batch.batch_no) {
            used_batches[batch.batch_no].used_qty += element.qty;
            used_batches[batch.batch_no].remaining_qty -= element.qty;
            used_batches[batch.batch_no].batch_qty -= element.qty;
          }
        });
      });

      // set item batch_no based on:
      // 1. if batch has expiry_date we should use the batch with the nearest expiry_date
      // 2. if batch has no expiry_date we should use the batch with the earliest manufacturing_date
      // 3. we should not use batch with remaining_qty = 0
      // 4. we should the highest remaining_qty
      const batch_no_data = Object.values(used_batches)
        .filter((batch) => batch.remaining_qty > 0)
        .sort((a, b) => {
          if (a.expiry_date && b.expiry_date) {
            return a.expiry_date - b.expiry_date;
          } else if (a.expiry_date) {
            return -1;
          } else if (b.expiry_date) {
            return 1;
          } else if (a.manufacturing_date && b.manufacturing_date) {
            return a.manufacturing_date - b.manufacturing_date;
          } else if (a.manufacturing_date) {
            return -1;
          } else if (b.manufacturing_date) {
            return 1;
          } else {
            return b.remaining_qty - a.remaining_qty;
          }
        });
      if (batch_no_data.length > 0) {
        let batch_to_use = null;
        if (value) {
          batch_to_use = batch_no_data.find((batch) => batch.batch_no == value);
        }
        if (!batch_to_use) {
          batch_to_use = batch_no_data[0];
        }
        item.batch_no = batch_to_use.batch_no;
        item.actual_batch_qty = batch_to_use.batch_qty;
        item.batch_no_expiry_date = batch_to_use.expiry_date;
        if (batch_to_use.batch_price) {
          item.batch_price = batch_to_use.batch_price;
          item.price_list_rate = batch_to_use.batch_price;
          item.rate = batch_to_use.batch_price;
        } else if (update) {
          item.batch_price = null;
          this.update_item_detail(item);
        }
      } else {
        item.batch_no = null;
        item.actual_batch_qty = null;
        item.batch_no_expiry_date = null;
        item.batch_price = null;
      }
      // update item batch_no_data from batch_no_data
      item.batch_no_data = batch_no_data;
    },

    shortOpenPayment(e) {
      if (e.key === "s" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        this.show_payment();
      }
    },

    shortDeleteFirstItem(e) {
      if (e.key === "d" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        this.remove_item(this.items[0]);
      }
    },

    shortOpenFirstItem(e) {
      if (e.key === "a" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        this.expanded = [];
        this.expanded.push(this.items[0]);
      }
    },

    shortSelectDiscount(e) {
      if (e.key === "z" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        this.$refs.discount.focus();
      }
    },

    makeid(length) {
      let result = "";
      const characters = "abcdefghijklmnopqrstuvwxyz0123456789";
      const charactersLength = characters.length;
      for (var i = 0; i < length; i++) {
        result += characters.charAt(
          Math.floor(Math.random() * charactersLength)
        );
      }
      return result;
    },

    checkOfferIsAppley(item, offer) {
      let applied = false;
      const item_offers = JSON.parse(item.posa_offers);
      for (const row_id of item_offers) {
        const exist_offer = this.posa_offers.find((el) => row_id == el.row_id);
        if (exist_offer && exist_offer.offer_name == offer.name) {
          applied = true;
          break;
        }
      }
      return applied;
    },

    handelOffers() {
      const offers = [];
      this.posOffers.forEach((offer) => {
        if (offer.apply_on === "Item Code") {
          const itemOffer = this.getItemOffer(offer);
          if (itemOffer) {
            offers.push(itemOffer);
          }
        } else if (offer.apply_on === "Item Group") {
          const groupOffer = this.getGroupOffer(offer);
          if (groupOffer) {
            offers.push(groupOffer);
          }
        } else if (offer.apply_on === "Brand") {
          const brandOffer = this.getBrandOffer(offer);
          if (brandOffer) {
            offers.push(brandOffer);
          }
        } else if (offer.apply_on === "Transaction") {
          const transactionOffer = this.getTransactionOffer(offer);
          if (transactionOffer) {
            offers.push(transactionOffer);
          }
        }
      });

      this.setItemGiveOffer(offers);
      this.updatePosOffers(offers);
    },

    setItemGiveOffer(offers) {
      // Set item give offer for replace
      offers.forEach((offer) => {
        if (
          offer.apply_on == "Item Code" &&
          offer.apply_type == "Item Code" &&
          offer.replace_item
        ) {
          offer.give_item = offer.item;
          offer.apply_item_code = offer.item;
        } else if (
          offer.apply_on == "Item Group" &&
          offer.apply_type == "Item Group" &&
          offer.replace_cheapest_item
        ) {
          const offerItemCode = this.getCheapestItem(offer).item_code;
          offer.give_item = offerItemCode;
          offer.apply_item_code = offerItemCode;
        }
      });
    },

    getCheapestItem(offer) {
      let itemsRowID;
      if (typeof offer.items === "string") {
        itemsRowID = JSON.parse(offer.items);
      } else {
        itemsRowID = offer.items;
      }
      const itemsList = [];
      itemsRowID.forEach((row_id) => {
        itemsList.push(this.getItemFromRowID(row_id));
      });
      const result = itemsList.reduce(function (res, obj) {
        return !obj.posa_is_replace &&
          !obj.posa_is_offer &&
          obj.price_list_rate < res.price_list_rate
          ? obj
          : res;
      });
      return result;
    },

    getItemFromRowID(row_id) {
      const item = this.items.find((el) => el.posa_row_id == row_id);
      return item;
    },

    checkQtyAnountOffer(offer, qty, amount) {
      let min_qty = false;
      let max_qty = false;
      let min_amt = false;
      let max_amt = false;
      const applys = [];

      if (offer.min_qty || offer.min_qty == 0) {
        if (qty >= offer.min_qty) {
          min_qty = true;
        }
        applys.push(min_qty);
      }

      if (offer.max_qty > 0) {
        if (qty <= offer.max_qty) {
          max_qty = true;
        }
        applys.push(max_qty);
      }

      if (offer.min_amt > 0) {
        if (amount >= offer.min_amt) {
          min_amt = true;
        }
        applys.push(min_amt);
      }

      if (offer.max_amt > 0) {
        if (amount <= offer.max_amt) {
          max_amt = true;
        }
        applys.push(max_amt);
      }
      let apply = false;
      if (!applys.includes(false)) {
        apply = true;
      }
      const res = {
        apply: apply,
        conditions: { min_qty, max_qty, min_amt, max_amt },
      };
      return res;
    },

    checkOfferCoupon(offer) {
      if (offer.coupon_based) {
        const coupon = this.posa_coupons.find(
          (el) => offer.name == el.pos_offer
        );
        if (coupon) {
          offer.coupon = coupon.coupon;
          return true;
        } else {
          return false;
        }
      } else {
        offer.coupon = null;
        return true;
      }
    },

    getItemOffer(offer) {
      let apply_offer = null;
      if (offer.apply_on === "Item Code") {
        if (this.checkOfferCoupon(offer)) {
          this.items.forEach((item) => {
            if (!item.posa_is_offer && item.item_code === offer.item) {
              const items = [];
              if (
                offer.offer === "Item Price" &&
                item.posa_offer_applied &&
                !this.checkOfferIsAppley(item, offer)
              ) {
              } else {
                const res = this.checkQtyAnountOffer(
                  offer,
                  item.stock_qty,
                  item.stock_qty * item.price_list_rate
                );
                if (res.apply) {
                  items.push(item.posa_row_id);
                  offer.items = items;
                  apply_offer = offer;
                }
              }
            }
          });
        }
      }
      return apply_offer;
    },

    getGroupOffer(offer) {
      let apply_offer = null;
      if (offer.apply_on === "Item Group") {
        if (this.checkOfferCoupon(offer)) {
          const items = [];
          let total_count = 0;
          let total_amount = 0;
          this.items.forEach((item) => {
            if (!item.posa_is_offer && item.item_group === offer.item_group) {
              if (
                offer.offer === "Item Price" &&
                item.posa_offer_applied &&
                !this.checkOfferIsAppley(item, offer)
              ) {
              } else {
                total_count += item.stock_qty;
                total_amount += item.stock_qty * item.price_list_rate;
                items.push(item.posa_row_id);
              }
            }
          });
          if (total_count || total_amount) {
            const res = this.checkQtyAnountOffer(
              offer,
              total_count,
              total_amount
            );
            if (res.apply) {
              offer.items = items;
              apply_offer = offer;
            }
          }
        }
      }
      return apply_offer;
    },

    getBrandOffer(offer) {
      let apply_offer = null;
      if (offer.apply_on === "Brand") {
        if (this.checkOfferCoupon(offer)) {
          const items = [];
          let total_count = 0;
          let total_amount = 0;
          this.items.forEach((item) => {
            if (!item.posa_is_offer && item.brand === offer.brand) {
              if (
                offer.offer === "Item Price" &&
                item.posa_offer_applied &&
                !this.checkOfferIsAppley(item, offer)
              ) {
              } else {
                total_count += item.stock_qty;
                total_amount += item.stock_qty * item.price_list_rate;
                items.push(item.posa_row_id);
              }
            }
          });
          if (total_count || total_amount) {
            const res = this.checkQtyAnountOffer(
              offer,
              total_count,
              total_amount
            );
            if (res.apply) {
              offer.items = items;
              apply_offer = offer;
            }
          }
        }
      }
      return apply_offer;
    },
    getTransactionOffer(offer) {
      let apply_offer = null;
      if (offer.apply_on === "Transaction") {
        if (this.checkOfferCoupon(offer)) {
          let total_qty = 0;
          this.items.forEach((item) => {
            if (!item.posa_is_offer && !item.posa_is_replace) {
              total_qty += item.stock_qty;
            }
          });
          const items = [];
          const total_count = total_qty;
          const total_amount = this.Total;
          if (total_count || total_amount) {
            const res = this.checkQtyAnountOffer(
              offer,
              total_count,
              total_amount
            );
            if (res.apply) {
              this.items.forEach((item) => {
                items.push(item.posa_row_id);
              });
              offer.items = items;
              apply_offer = offer;
            }
          }
        }
      }
      return apply_offer;
    },

    updatePosOffers(offers) {
      evntBus.$emit("update_pos_offers", offers);
    },

    updateInvoiceOffers(offers) {
      this.posa_offers.forEach((invoiceOffer) => {
        const existOffer = offers.find(
          (offer) => invoiceOffer.row_id == offer.row_id
        );
        if (!existOffer) {
          this.removeApplyOffer(invoiceOffer);
        }
      });
      offers.forEach((offer) => {
        const existOffer = this.posa_offers.find(
          (invoiceOffer) => invoiceOffer.row_id == offer.row_id
        );
        if (existOffer) {
          existOffer.items = JSON.stringify(offer.items);
          if (
            existOffer.offer === "Give Product" &&
            existOffer.give_item &&
            existOffer.give_item != offer.give_item
          ) {
            const item_to_remove = this.items.find(
              (item) => item.posa_row_id == existOffer.give_item_row_id
            );
            if (item_to_remove) {
              const updated_item_offers = offer.items.filter(
                (row_id) => row_id != item_to_remove.posa_row_id
              );
              offer.items = updated_item_offers;
              this.remove_item(item_to_remove);
              existOffer.give_item_row_id = null;
              existOffer.give_item = null;
            }
            const newItemOffer = this.ApplyOnGiveProduct(offer);
            if (offer.replace_cheapest_item) {
              const cheapestItem = this.getCheapestItem(offer);
              const oldBaseItem = this.items.find(
                (el) => el.posa_row_id == item_to_remove.posa_is_replace
              );
              newItemOffer.qty = item_to_remove.qty;
              if (oldBaseItem && !oldBaseItem.posa_is_replace) {
                oldBaseItem.qty += item_to_remove.qty;
              } else {
                const restoredItem = this.ApplyOnGiveProduct(
                  {
                    given_qty: item_to_remove.qty,
                  },
                  item_to_remove.item_code
                );
                restoredItem.posa_is_offer = 0;
                this.items.unshift(restoredItem);
              }
              newItemOffer.posa_is_offer = 0;
              newItemOffer.posa_is_replace = cheapestItem.posa_row_id;
              const diffQty = cheapestItem.qty - newItemOffer.qty;
              if (diffQty <= 0) {
                newItemOffer.qty += diffQty;
                this.remove_item(cheapestItem);
                newItemOffer.posa_row_id = cheapestItem.posa_row_id;
                newItemOffer.posa_is_replace = newItemOffer.posa_row_id;
              } else {
                cheapestItem.qty = diffQty;
              }
            }
            this.items.unshift(newItemOffer);
            existOffer.give_item_row_id = newItemOffer.posa_row_id;
            existOffer.give_item = newItemOffer.item_code;
          } else if (
            existOffer.offer === "Give Product" &&
            existOffer.give_item &&
            existOffer.give_item == offer.give_item &&
            (offer.replace_item || offer.replace_cheapest_item)
          ) {
            this.$nextTick(function () {
              const offerItem = this.getItemFromRowID(
                existOffer.give_item_row_id
              );
              const diff = offer.given_qty - offerItem.qty;
              if (diff > 0) {
                const itemsRowID = JSON.parse(existOffer.items);
                const itemsList = [];
                itemsRowID.forEach((row_id) => {
                  itemsList.push(this.getItemFromRowID(row_id));
                });
                const existItem = itemsList.find(
                  (el) =>
                    el.item_code == offerItem.item_code &&
                    el.posa_is_replace != offerItem.posa_row_id
                );
                if (existItem) {
                  const diffExistQty = existItem.qty - diff;
                  if (diffExistQty > 0) {
                    offerItem.qty += diff;
                    existItem.qty -= diff;
                  } else {
                    offerItem.qty += existItem.qty;
                    this.remove_item(existItem);
                  }
                }
              }
            });
          } else if (existOffer.offer === "Item Price") {
            this.ApplyOnPrice(offer);
          } else if (existOffer.offer === "Grand Total") {
            this.ApplyOnTotal(offer);
          }
          this.addOfferToItems(existOffer);
        } else {
          this.applyNewOffer(offer);
        }
      });
    },

    removeApplyOffer(invoiceOffer) {
      if (invoiceOffer.offer === "Item Price") {
        this.RemoveOnPrice(invoiceOffer);
        const index = this.posa_offers.findIndex(
          (el) => el.row_id === invoiceOffer.row_id
        );
        this.posa_offers.splice(index, 1);
      }
      if (invoiceOffer.offer === "Give Product") {
        const item_to_remove = this.items.find(
          (item) => item.posa_row_id == invoiceOffer.give_item_row_id
        );
        const index = this.posa_offers.findIndex(
          (el) => el.row_id === invoiceOffer.row_id
        );
        this.posa_offers.splice(index, 1);
        this.remove_item(item_to_remove);
      }
      if (invoiceOffer.offer === "Grand Total") {
        this.RemoveOnTotal(invoiceOffer);
        const index = this.posa_offers.findIndex(
          (el) => el.row_id === invoiceOffer.row_id
        );
        this.posa_offers.splice(index, 1);
      }
      if (invoiceOffer.offer === "Loyalty Point") {
        const index = this.posa_offers.findIndex(
          (el) => el.row_id === invoiceOffer.row_id
        );
        this.posa_offers.splice(index, 1);
      }
      this.deleteOfferFromItems(invoiceOffer);
    },

    applyNewOffer(offer) {
      if (offer.offer === "Item Price") {
        this.ApplyOnPrice(offer);
      }
      if (offer.offer === "Give Product") {
        let itemsRowID;
        if (typeof offer.items === "string") {
          itemsRowID = JSON.parse(offer.items);
        } else {
          itemsRowID = offer.items;
        }
        if (
          offer.apply_on == "Item Code" &&
          offer.apply_type == "Item Code" &&
          offer.replace_item
        ) {
          const item = this.ApplyOnGiveProduct(offer, offer.item);
          item.posa_is_replace = itemsRowID[0];
          const baseItem = this.items.find(
            (el) => el.posa_row_id == item.posa_is_replace
          );
          const diffQty = baseItem.qty - offer.given_qty;
          item.posa_is_offer = 0;
          if (diffQty <= 0) {
            item.qty = baseItem.qty;
            this.remove_item(baseItem);
            item.posa_row_id = item.posa_is_replace;
          } else {
            baseItem.qty = diffQty;
          }
          this.items.unshift(item);
          offer.give_item_row_id = item.posa_row_id;
        } else if (
          offer.apply_on == "Item Group" &&
          offer.apply_type == "Item Group" &&
          offer.replace_cheapest_item
        ) {
          const itemsList = [];
          itemsRowID.forEach((row_id) => {
            itemsList.push(this.getItemFromRowID(row_id));
          });
          const baseItem = itemsList.find(
            (el) => el.item_code == offer.give_item
          );
          const item = this.ApplyOnGiveProduct(offer, offer.give_item);
          item.posa_is_offer = 0;
          item.posa_is_replace = baseItem.posa_row_id;
          const diffQty = baseItem.qty - offer.given_qty;
          if (diffQty <= 0) {
            item.qty = baseItem.qty;
            this.remove_item(baseItem);
            item.posa_row_id = item.posa_is_replace;
          } else {
            baseItem.qty = diffQty;
          }
          this.items.unshift(item);
          offer.give_item_row_id = item.posa_row_id;
        } else {
          const item = this.ApplyOnGiveProduct(offer);
          this.items.unshift(item);
          if (item) {
            offer.give_item_row_id = item.posa_row_id;
          }
        }
      }
      if (offer.offer === "Grand Total") {
        this.ApplyOnTotal(offer);
      }
      if (offer.offer === "Loyalty Point") {
        evntBus.$emit("show_mesage", {
          text: __("Loyalty Point Offer Applied"),
          color: "success",
        });
      }

      const newOffer = {
        offer_name: offer.name,
        row_id: offer.row_id,
        apply_on: offer.apply_on,
        offer: offer.offer,
        items: JSON.stringify(offer.items),
        give_item: offer.give_item,
        give_item_row_id: offer.give_item_row_id,
        offer_applied: offer.offer_applied,
        coupon_based: offer.coupon_based,
        coupon: offer.coupon,
      };
      this.posa_offers.push(newOffer);
      this.addOfferToItems(newOffer);
    },

    ApplyOnGiveProduct(offer, item_code) {
      if (!item_code) {
        item_code = offer.give_item;
      }
      const items = this.allItems;
      const item = items.find((item) => item.item_code == item_code);
      if (!item) {
        return;
      }
      const new_item = { ...item };
      new_item.qty = offer.given_qty;
      new_item.stock_qty = offer.given_qty;
      new_item.rate = offer.discount_type === "Rate" ? offer.rate : item.rate;
      new_item.discount_amount =
        offer.discount_type === "Discount Amount" ? offer.discount_amount : 0;
      new_item.discount_percentage =
        offer.discount_type === "Discount Percentage"
          ? offer.discount_percentage
          : 0;
      new_item.discount_amount_per_item = 0;
      new_item.uom = item.uom ? item.uom : item.stock_uom;
      new_item.actual_batch_qty = "";
      new_item.conversion_factor = 1;
      new_item.posa_offers = JSON.stringify([]);
      new_item.posa_offer_applied = 0;
      new_item.posa_is_offer = 1;
      new_item.posa_is_replace = null;
      new_item.posa_notes = "";
      new_item.posa_delivery_date = "";
      new_item.is_free_item =
        (offer.discount_type === "Rate" && !offer.rate) ||
        (offer.discount_type === "Discount Percentage" &&
          offer.discount_percentage == 0)
          ? 1
          : 0;
      new_item.posa_row_id = this.makeid(20);
      new_item.price_list_rate =
        (offer.discount_type === "Rate" && !offer.rate) ||
        (offer.discount_type === "Discount Percentage" &&
          offer.discount_percentage == 0)
          ? 0
          : item.rate;
      if (
        (!this.pos_profile.posa_auto_set_batch && new_item.has_batch_no) ||
        new_item.has_serial_no
      ) {
        this.expanded.push(new_item);
      }
      this.update_item_detail(new_item);
      return new_item;
    },

    ApplyOnPrice(offer) {
      this.items.forEach((item) => {
        if (offer.items.includes(item.posa_row_id)) {
          const item_offers = JSON.parse(item.posa_offers);
          if (!item_offers.includes(offer.row_id)) {
            if (offer.discount_type === "Rate") {
              item.rate = offer.rate;
            } else if (offer.discount_type === "Discount Percentage") {
              item.discount_percentage += offer.discount_percentage;
            } else if (offer.discount_type === "Discount Amount") {
              item.discount_amount += offer.discount_amount;
            }
            item.posa_offer_applied = 1;
            this.calc_item_price(item);
          }
        }
      });
    },

    RemoveOnPrice(offer) {
      this.items.forEach((item) => {
        const item_offers = JSON.parse(item.posa_offers);
        if (item_offers.includes(offer.row_id)) {
          const originalOffer = this.posOffers.find(
            (el) => el.name == offer.offer_name
          );
          if (originalOffer) {
            if (originalOffer.discount_type === "Rate") {
              item.rate = item.price_list_rate;
            } else if (originalOffer.discount_type === "Discount Percentage") {
              item.discount_percentage -= offer.discount_percentage;
              if (!item.discount_percentage) {
                item.discount_percentage = 0;
                item.discount_amount = 0;
                item.rate = item.price_list_rate;
              }
            } else if (originalOffer.discount_type === "Discount Amount") {
              item.discount_amount -= offer.discount_amount;
            }
            this.calc_item_price(item);
          }
        }
      });
    },

    ApplyOnTotal(offer) {
      if (!offer.name) {
        offer = this.posOffers.find((el) => el.name == offer.offer_name);
      }
      if (
        (!this.discount_percentage_offer_name ||
          this.discount_percentage_offer_name == offer.name) &&
        offer.discount_percentage > 0 &&
        offer.discount_percentage <= 100
      ) {
        this.discount_amount = this.flt(
          (flt(this.Total) * flt(offer.discount_percentage)) / 100,
          this.currency_precision
        );
        this.discount_percentage_offer_name = offer.name;
      }
    },

    RemoveOnTotal(offer) {
      if (
        this.discount_percentage_offer_name &&
        this.discount_percentage_offer_name == offer.offer_name
      ) {
        this.discount_amount = 0;
        this.discount_percentage_offer_name = null;
      }
    },

    addOfferToItems(offer) {
      const offer_items = JSON.parse(offer.items);
      offer_items.forEach((el) => {
        this.items.forEach((exist_item) => {
          if (exist_item.posa_row_id == el) {
            const item_offers = JSON.parse(exist_item.posa_offers);
            if (!item_offers.includes(offer.row_id)) {
              item_offers.push(offer.row_id);
              if (offer.offer === "Item Price") {
                exist_item.posa_offer_applied = 1;
              }
            }
            exist_item.posa_offers = JSON.stringify(item_offers);
          }
        });
      });
    },

    deleteOfferFromItems(offer) {
      const offer_items = JSON.parse(offer.items);
      offer_items.forEach((el) => {
        this.items.forEach((exist_item) => {
          if (exist_item.posa_row_id == el) {
            const item_offers = JSON.parse(exist_item.posa_offers);
            const updated_item_offers = item_offers.filter(
              (row_id) => row_id != offer.row_id
            );
            if (offer.offer === "Item Price") {
              exist_item.posa_offer_applied = 0;
            }
            exist_item.posa_offers = JSON.stringify(updated_item_offers);
          }
        });
      });
    },

    validate_due_date(item) {
      const today = frappe.datetime.now_date();
      const parse_today = Date.parse(today);
      const new_date = Date.parse(item.posa_delivery_date);
      if (new_date < parse_today) {
        setTimeout(() => {
          item.posa_delivery_date = today;
        }, 0);
      }
    },
    load_print_page(invoice_name) {
      const print_format =
        this.pos_profile.print_format_for_online ||
        this.pos_profile.print_format;
      const letter_head = this.pos_profile.letter_head || 0;
      const url =
        frappe.urllib.get_base_url() +
        "/printview?doctype=Sales%20Invoice&name=" +
        invoice_name +
        "&trigger_print=1" +
        "&format=" +
        print_format +
        "&no_letterhead=" +
        letter_head;
      const printWindow = window.open(url, "Print");
      printWindow.addEventListener(
        "load",
        function () {
          printWindow.print();
          // printWindow.close();
          // NOTE : uncomoent this to auto closing printing window
        },
        true
      );
    },

    print_draft_invoice() {
      if (!this.pos_profile.posa_allow_print_draft_invoices) {
        evntBus.$emit("show_mesage", {
          text: __(`You are not allowed to print draft invoices`),
          color: "error",
        });
        return;
      }
      let invoice_name = this.invoice_doc.name;
      frappe.run_serially([
        () => {
          const invoice_doc = this.new_invoice();
          invoice_name = invoice_doc.name ? invoice_doc.name : invoice_name;
        },
        () => {
          this.load_print_page(invoice_name);
        },
      ]);
    },
    set_delivery_charges() {
      const vm = this;
      if (
        !this.pos_profile ||
        !this.customer ||
        !this.pos_profile.posa_use_delivery_charges
      ) {
        this.delivery_charges = [];
        this.delivery_charges_rate = 0;
        this.selcted_delivery_charges = {};
        return;
      }
      this.delivery_charges_rate = 0;
      this.selcted_delivery_charges = {};
      frappe.call({
        method:
          "posawesome.posawesome.api.posapp.get_applicable_delivery_charges",
        args: {
          company: this.pos_profile.company,
          pos_profile: this.pos_profile.name,
          customer: this.customer,
        },
        async: true,
        callback: function (r) {
          if (r.message) {
            vm.delivery_charges = r.message;
          }
        },
      });
    },
    deliveryChargesFilter(item, queryText, itemText) {
      const textOne = item.name.toLowerCase();
      const searchText = queryText.toLowerCase();
      return textOne.indexOf(searchText) > -1;
    },
    update_delivery_charges() {
      if (this.selcted_delivery_charges) {
        this.delivery_charges_rate = this.selcted_delivery_charges.rate;
      } else {
        this.delivery_charges_rate = 0;
      }
    },
  },

  mounted() {
    evntBus.$on("register_pos_profile", (data) => {
      this.pos_profile = data.pos_profile;
      this.current_role = this.get_current_role();
      this.customer = data.pos_profile.customer;
      this.pos_opening_shift = data.pos_opening_shift;
      this.stock_settings = data.stock_settings;
      this.float_precision =
        frappe.defaults.get_default("float_precision") || 2;
      this.currency_precision =
        frappe.defaults.get_default("currency_precision") || 2;
      this.invoiceType = this.pos_profile.posa_default_sales_order
        ? "Order"
        : "Invoice";
    });
    evntBus.$on("add_item", (item) => {
      this.add_item(item);
    });
    evntBus.$on("update_customer", (customer) => {
      this.customer = customer;
    });
    evntBus.$on("fetch_customer_details", () => {
      this.fetch_customer_details();
    });
    evntBus.$on("new_invoice", () => {
      this.invoice_doc = "";
      this.cancel_invoice();
    });
    evntBus.$on("load_invoice", (data) => {
      this.new_invoice(data);

      if (this.invoice_doc.is_return) {
        this.discount_amount = -data.discount_amount;
        this.additional_discount_percentage =
          -data.additional_discount_percentage;
        this.return_doc = data;
      } else {
        evntBus.$emit("set_pos_coupons", data.posa_coupons);
      }
    });
    evntBus.$on("load_order", (data) => {
      this.new_order(data);
      // evntBus.$emit("set_pos_coupons", data.posa_coupons);
    });
    evntBus.$on("set_offers", (data) => {
      this.posOffers = data;
    });
    evntBus.$on("update_invoice_offers", (data) => {
      this.updateInvoiceOffers(data);
    });
    evntBus.$on("update_invoice_coupons", (data) => {
      this.posa_coupons = data;
      this.handelOffers();
    });
    evntBus.$on("set_all_items", (data) => {
      this.allItems = data;
      this.items.forEach((item) => {
        this.update_item_detail(item);
      });
    });
    evntBus.$on("relay_status_changed", (statusPayload) => {
      this.relay_status = {
        enabled: !!statusPayload.enabled,
        connected: !!statusPayload.connected,
        profile_relay_url: statusPayload.profile_relay_url || "",
      };
    });
    evntBus.$on("load_return_invoice", (data) => {
      this.new_invoice(data.invoice_doc);
      this.discount_amount = -data.return_doc.discount_amount;
      this.additional_discount_percentage =
        -data.return_doc.additional_discount_percentage;
      this.return_doc = data.return_doc;
    });
    evntBus.$on("set_new_line", (data) => {
      this.new_line = data;
    });
  },
  beforeDestroy() {
    evntBus.$off("register_pos_profile");
    evntBus.$off("add_item");
    evntBus.$off("update_customer");
    evntBus.$off("fetch_customer_details");
    evntBus.$off("new_invoice");
    evntBus.$off("set_offers");
    evntBus.$off("update_invoice_offers");
    evntBus.$off("update_invoice_coupons");
    evntBus.$off("set_all_items");
    evntBus.$off("relay_status_changed");
  },
  created() {
    this.current_role = this.get_current_role();
    document.addEventListener("keydown", this.shortOpenPayment.bind(this));
    document.addEventListener("keydown", this.shortDeleteFirstItem.bind(this));
    document.addEventListener("keydown", this.shortOpenFirstItem.bind(this));
    document.addEventListener("keydown", this.shortSelectDiscount.bind(this));
  },
  destroyed() {
    document.removeEventListener("keydown", this.shortOpenPayment);
    document.removeEventListener("keydown", this.shortDeleteFirstItem);
    document.removeEventListener("keydown", this.shortOpenFirstItem);
    document.removeEventListener("keydown", this.shortSelectDiscount);
  },
  watch: {
    customer() {
      this.close_payments();
      evntBus.$emit("set_customer", this.customer);
      this.fetch_customer_details();
      this.set_delivery_charges();
    },
    customer_info() {
      evntBus.$emit("set_customer_info_to_edit", this.customer_info);
    },
    expanded(data_value) {
      // this.update_items_details(data_value);
      if (data_value.length > 0) {
        this.update_item_detail(data_value[0]);
      }
    },
    discount_percentage_offer_name() {
      evntBus.$emit("update_discount_percentage_offer_name", {
        value: this.discount_percentage_offer_name,
      });
    },
    items: {
      deep: true,
      handler(items) {
        this.handelOffers();
        this.$forceUpdate();
      },
    },
    invoiceType() {
      evntBus.$emit("update_invoice_type", this.invoiceType);
    },
    discount_amount() {
      if (!this.discount_amount || this.discount_amount == 0) {
        this.additional_discount_percentage = 0;
      } else if (this.pos_profile.posa_use_percentage_discount) {
        this.additional_discount_percentage =
          (this.discount_amount / this.Total) * 100;
      } else {
        this.additional_discount_percentage = 0;
      }
    },
  },
};
</script>

<style scoped>
.border_line_bottom {
  border-bottom: 1px solid lightgray;
}
.disable-events {
  pointer-events: none;
}
</style>
