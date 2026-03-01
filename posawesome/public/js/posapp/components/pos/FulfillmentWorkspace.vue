<template>
  <div class="mt-3">
    <v-row dense>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title class="py-2">
            <div class="d-flex align-center justify-space-between" style="width:100%">
              <div>
                <div class="text-subtitle-1 font-weight-bold">{{ roleTitle }}</div>
                <div class="caption grey--text">{{ profileName || __('No POS Profile') }}</div>
              </div>
              <v-btn icon small :disabled="queueLoading" @click="refreshAll">
                <v-icon :class="{ 'spin': queueLoading || detailLoading }">mdi-refresh</v-icon>
              </v-btn>
            </div>
          </v-card-title>
          <v-card-text class="pt-0">
            <div class="d-flex align-center justify-space-between mb-2">
              <v-btn-toggle
                v-model="viewMode"
                dense
                mandatory
                class="fulfillment-view-toggle"
                data-cy="fulfillment-view-mode"
              >
                <v-btn small value="detailed" data-cy="fulfillment-view-detailed">
                  {{ __('Detailed') }}
                </v-btn>
                <v-btn small value="simple" data-cy="fulfillment-view-simple">
                  {{ __('Simple') }}
                </v-btn>
              </v-btn-toggle>
              <div class="caption grey--text">
                {{ isDetailedView ? __('Detailed view (default)') : __('Simple view') }}
              </div>
            </div>
            <v-alert dense outlined type="info" class="mb-2">
              {{ __('Paper-first picking with line-wise edits for exceptions. Picked qty defaults to ordered qty and keeps order UOM/conversion factor.') }}
            </v-alert>
            <div v-if="errorText" class="red--text mb-2">{{ errorText }}</div>
            <div v-if="canDispatch && isDetailedView" class="mb-2">
              <v-row dense>
                <v-col cols="6" sm="4">
                  <v-card outlined class="pa-2">
                    <div class="caption grey--text">{{ __('Ready') }}</div>
                    <div class="text-subtitle-2 font-weight-bold success--text">{{ dispatchQueueStats.ready_count }}</div>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4">
                  <v-card outlined class="pa-2">
                    <div class="caption grey--text">{{ __('Picking') }}</div>
                    <div class="text-subtitle-2 font-weight-bold primary--text">{{ dispatchQueueStats.picking_count }}</div>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="4">
                  <v-card outlined class="pa-2">
                    <div class="caption grey--text">{{ __('Exceptions') }}</div>
                    <div class="text-subtitle-2 font-weight-bold error--text">{{ dispatchQueueStats.exception_count }}</div>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="6">
                  <v-card outlined class="pa-2">
                    <div class="caption grey--text">{{ __('Avg Wait (Ready)') }}</div>
                    <div class="text-subtitle-2 font-weight-bold">{{ dispatchQueueStats.avg_ready_wait_label }}</div>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="6">
                  <v-card outlined class="pa-2">
                    <div class="caption grey--text">{{ __('Oldest Open') }}</div>
                    <div class="text-subtitle-2 font-weight-bold">{{ dispatchQueueStats.oldest_open_age_label }}</div>
                  </v-card>
                </v-col>
                <v-col cols="6" sm="6">
                  <v-card outlined class="pa-2">
                    <div class="caption grey--text">{{ __('Over SLA') }}</div>
                    <div class="text-subtitle-2 font-weight-bold error--text">{{ dispatchQueueStats.over_sla_count }}</div>
                  </v-card>
                </v-col>
              </v-row>
            </div>
            <div v-if="canDispatch && isDetailedView" class="caption grey--text mb-2">
              {{ __('Dispatch queue is auto-sorted by SLA urgency and time waiting in current phase (oldest first).') }}
            </div>
            <v-text-field
              v-model="queueSearch"
              dense
              outlined
              hide-details
              clearable
              prepend-inner-icon="mdi-magnify"
              :label="__('Search LSR / SO / customer')"
              class="mb-2"
            />
            <div class="d-flex flex-wrap mb-2">
              <v-chip
                v-for="f in filters"
                :key="f.value"
                small
                class="mr-1 mb-1"
                :outlined="queueFilter !== f.value"
                :color="queueFilter === f.value ? f.color : ''"
                @click="queueFilter = f.value"
              >
                {{ f.label }}
              </v-chip>
            </div>
            <div class="queue-list">
              <v-list dense>
                <v-list-item
                  v-for="row in filteredRows"
                  :key="row.local_sale_ref"
                  :class="{ active: selectedRef === row.local_sale_ref }"
                  @click="selectRow(row)"
                >
                  <v-list-item-content>
                    <v-list-item-title class="font-weight-bold">
                      {{ row.customer_name || __('Unknown Customer') }}
                    </v-list-item-title>
                    <v-list-item-subtitle>{{ row.local_sale_ref }}</v-list-item-subtitle>
                    <v-list-item-subtitle v-if="row.token_id">{{ __('SO') }}: {{ row.token_id }}</v-list-item-subtitle>
                    <v-list-item-subtitle class="d-flex align-center flex-wrap mt-1">
                      <v-chip x-small class="mr-1 mb-1" :color="pickColor(row.pick_status)" text-color="white">
                        {{ row.pick_status }}
                      </v-chip>
                      <v-chip x-small class="mr-1 mb-1" :color="dispatchColor(row.dispatch_status)" text-color="white">
                        {{ row.dispatch_status }}
                      </v-chip>
                      <v-chip
                        x-small
                        class="mr-1 mb-1"
                        :color="queueSlaChipColor(row)"
                        :outlined="queueSlaChipColor(row) === 'grey'"
                        :text-color="queueSlaChipColor(row) === 'grey' ? '' : 'white'"
                      >
                        {{ queueSlaLabel(row) }}
                      </v-chip>
                      <v-chip
                        x-small
                        class="mr-1 mb-1"
                        :color="queueRowIsStale(row) ? 'warning' : 'success'"
                        :outlined="!queueRowIsStale(row)"
                        :text-color="queueRowIsStale(row) ? 'white' : ''"
                      >
                        {{ queueRowIsStale(row) ? __('Stale') : __('Fresh') }}
                      </v-chip>
                      <span class="caption grey--text">{{ money(row.total) }}</span>
                    </v-list-item-subtitle>
                    <v-list-item-subtitle class="caption mt-1" :class="queueSlaTextClass(row)">
                      {{ __('Age') }}: {{ queueAgeLabel(row) }}
                      <span class="mx-1">|</span>
                      {{ queuePhaseLabel(row) }}: {{ queuePhaseAgeLabel(row) }}
                    </v-list-item-subtitle>
                    <v-list-item-subtitle
                      v-if="String(row.dispatch_exception_state || 'NONE') !== 'NONE'"
                      class="caption error--text mt-1"
                    >
                      {{ row.dispatch_exception_state }}
                      <span v-if="Number(row.cashier_adjustment_required || 0) === 1">
                        | {{ __('Cashier Adjustment Required') }}
                      </span>
                    </v-list-item-subtitle>
                  </v-list-item-content>
                </v-list-item>
              </v-list>
              <div v-if="!queueLoading && !filteredRows.length" class="text-center grey--text py-3">
                {{ __('No rows') }}
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card>
          <v-card-title class="py-2">
            <div class="d-flex align-center justify-space-between" style="width:100%">
              <div>
                <div class="text-subtitle-1 font-weight-bold">{{ __('Fulfillment Detail') }}</div>
                <div class="caption grey--text">{{ selectedRef || __('Select a queue row') }}</div>
              </div>
              <div class="d-flex align-center" v-if="detail && detail.sale">
                <v-chip small class="mr-1" :color="pickColor(detail.sale.pick_status)" text-color="white">
                  {{ detail.sale.pick_status }}
                </v-chip>
                <v-chip small class="mr-1" :color="dispatchColor(detail.sale.dispatch_status)" text-color="white">
                  {{ detail.sale.dispatch_status }}
                </v-chip>
                <v-chip small :color="syncColor(detail.sale.cloud_sync_status)" text-color="white">
                  {{ detail.sale.cloud_sync_status }}
                </v-chip>
                <v-chip
                  v-if="String(detail.sale.dispatch_exception_state || 'NONE') !== 'NONE'"
                  small
                  class="ml-1"
                  color="error"
                  text-color="white"
                >
                  {{ detail.sale.dispatch_exception_state }}
                </v-chip>
                <v-chip
                  v-if="Number(detail.sale.cashier_adjustment_required || 0) === 1"
                  small
                  class="ml-1"
                  color="warning"
                  text-color="white"
                >
                  {{ __('Cashier Adjustment Required') }}
                </v-chip>
                <v-chip
                  small
                  class="ml-1"
                  :color="queueRowIsStale(detail.sale) ? 'warning' : 'success'"
                  :outlined="!queueRowIsStale(detail.sale)"
                  :text-color="queueRowIsStale(detail.sale) ? 'white' : ''"
                >
                  {{ queueRowIsStale(detail.sale) ? __('Stale') : __('Fresh') }}
                </v-chip>
              </div>
            </div>
          </v-card-title>
          <v-card-text class="pt-0">
            <div v-if="detailError" class="red--text mb-2">{{ detailError }}</div>
            <div v-if="detailLoading" class="text-center py-4">
              <v-progress-circular indeterminate color="primary"></v-progress-circular>
            </div>
            <template v-else-if="detail && detail.sale">
              <v-row dense>
                <v-col cols="12" sm="6">
                  <v-card outlined>
                    <v-card-text class="py-2">
                      <div><strong>{{ __('LSR') }}:</strong> {{ detail.sale.local_sale_ref }}</div>
                      <div><strong>{{ __('SO/Token') }}:</strong> {{ detail.sale.token_id || '-' }}</div>
                      <div><strong>{{ __('Cloud SI') }}:</strong> {{ detail.sale.cloud_invoice_name || '-' }}</div>
                      <div><strong>{{ __('Customer') }}:</strong> {{ detail.sale.customer_name || detail.sale.customer_id || '-' }}</div>
                      <div><strong>{{ __('Cashier') }}:</strong> {{ detail.sale.cashier_user_id || '-' }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="12" sm="6">
                  <v-card outlined>
                    <v-card-text class="py-2">
                      <div><strong>{{ __('Total') }}:</strong> {{ money(detail.sale.total) }}</div>
                      <div><strong>{{ __('Created') }}:</strong> {{ dt(detail.sale.created_at) }}</div>
                      <div><strong>{{ __('Updated') }}:</strong> {{ dt(detail.sale.updated_at) }}</div>
                      <div><strong>{{ __('Released By') }}:</strong> {{ detail.sale.released_by || '-' }}</div>
                      <div><strong>{{ __('Released At') }}:</strong> {{ dt(detail.sale.released_at) }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>

              <v-alert v-if="hasDispatchProofOnSale && isDetailedView" dense outlined type="success" class="mt-2 mb-2">
                <strong>{{ __('Dispatch Proof') }}:</strong> {{ dispatchProofSummaryText }}
              </v-alert>
              <v-alert v-if="queueRowIsStale(detail.sale)" dense outlined type="warning" class="mt-2 mb-2">
                {{ __('Source Sales Order age exceeds profile max lookup age.') }}
                {{ __('Age') }}: {{ queueOrderAgeDays(detail.sale) }} {{ __('day(s)') }}
              </v-alert>

              <v-card outlined class="mt-2 mb-2" v-if="isDetailedView && detailPhaseTimeline.length">
                <v-card-title class="py-2 text-subtitle-2">{{ __('Phase Timeline (Dispatch Monitor)') }}</v-card-title>
                <v-card-text class="pt-0">
                  <v-row dense class="mb-1" v-if="detailMonitorSnapshot">
                    <v-col cols="12" sm="6" md="3">
                      <v-card outlined class="pa-2 fill-height">
                        <div class="caption grey--text">{{ __('Current Phase') }}</div>
                        <div class="text-body-2 font-weight-medium">{{ detailMonitorSnapshot.phase_label }}</div>
                      </v-card>
                    </v-col>
                    <v-col cols="12" sm="6" md="3">
                      <v-card outlined class="pa-2 fill-height">
                        <div class="caption grey--text">{{ __('Current Phase Age') }}</div>
                        <div class="text-body-2 font-weight-medium">{{ detailMonitorSnapshot.phase_age_label }}</div>
                      </v-card>
                    </v-col>
                    <v-col cols="12" sm="6" md="3">
                      <v-card outlined class="pa-2 fill-height">
                        <div class="caption grey--text">{{ __('Open Age') }}</div>
                        <div class="text-body-2 font-weight-medium">{{ detailMonitorSnapshot.open_age_label }}</div>
                      </v-card>
                    </v-col>
                    <v-col cols="12" sm="6" md="3">
                      <v-card outlined class="pa-2 fill-height">
                        <div class="caption grey--text">{{ __('SLA') }}</div>
                        <div class="text-body-2 font-weight-medium" :class="queueSlaTextClass(detail.sale)">
                          {{ detailMonitorSnapshot.sla_label }}
                        </div>
                      </v-card>
                    </v-col>
                  </v-row>
                  <v-row dense>
                    <v-col cols="12" sm="6" md="4" v-for="row in detailPhaseTimeline" :key="row.key">
                      <v-card outlined class="pa-2 fill-height">
                        <div class="caption grey--text">{{ row.label }}</div>
                        <div class="text-body-2 font-weight-medium">{{ row.at_label }}</div>
                        <div class="caption" v-if="row.duration_label">
                          {{ __('Duration') }}: {{ row.duration_label }}
                        </div>
                      </v-card>
                    </v-col>
                  </v-row>
                  <div class="caption grey--text mt-1" v-if="detailPhaseSummaryLines.length">
                    <div v-for="line in detailPhaseSummaryLines" :key="line">{{ line }}</div>
                  </div>
                </v-card-text>
              </v-card>

              <div class="d-flex flex-wrap align-center mt-2 mb-2" v-if="canPick || canDispatch">
                <v-btn v-if="canPick" small text color="primary" class="mr-1 mb-1" @click="markAllPicked">{{ __('Mark All Picked') }}</v-btn>
                <v-btn v-if="canPick" small color="primary" class="mr-1 mb-1" :loading="actionLoading" @click="pickUpdate('PICK_IN_PROGRESS')">{{ __('Start/Save Picking') }}</v-btn>
                <v-btn v-if="canPick" small color="success" class="mr-1 mb-1" :loading="actionLoading" @click="markPickedReady">{{ __('Mark Picked Ready') }}</v-btn>
                <v-btn v-if="canPick" small color="warning" class="mr-1 mb-1" :loading="actionLoading" @click="pickUpdate('PICK_EXCEPTION')">{{ __('Flag Exception') }}</v-btn>
                <v-btn
                  v-if="canDispatch"
                  small
                  color="success"
                  class="mr-1 mb-1"
                  :loading="actionLoading"
                  :disabled="!canRelease"
                  data-cy="dispatch-release-button"
                  @click="releaseSale"
                >
                  {{ __('Release Goods') }}
                </v-btn>
                <v-btn
                  v-if="canDispatch"
                  small
                  color="warning"
                  class="mr-1 mb-1"
                  :loading="actionLoading"
                  :disabled="!selectedRef || String((detail && detail.sale && detail.sale.dispatch_status) || '').toUpperCase() === 'RELEASED'"
                  data-cy="dispatch-flag-mismatch"
                  @click="flagMismatch"
                >
                  {{ __('Flag Mismatch') }}
                </v-btn>
                <v-checkbox
                  v-if="canDispatch"
                  v-model="allowPartialRelease"
                  dense
                  hide-details
                  class="mt-0 ml-2"
                  :label="__('Allow partial/exception release')"
                />
              </div>

              <v-row dense>
                <v-col cols="12" md="7">
                  <v-card outlined>
                    <v-card-title class="py-2 text-subtitle-2">{{ __('Line Items') }}</v-card-title>
                    <v-card-text class="pt-0 px-2">
                      <div class="lines-wrap">
                        <v-simple-table dense>
                          <thead>
                            <tr>
                              <th>{{ __('Item') }}</th>
                              <th class="text-right">{{ __('Ord Qty') }}</th>
                              <th>{{ __('UOM') }}</th>
                              <th class="text-right">{{ __('Conv') }}</th>
                              <th class="text-right">{{ __('Ord Stock') }}</th>
                              <th class="text-right">{{ __('Picked Qty') }}</th>
                              <th class="text-right">{{ __('Picked Stock') }}</th>
                              <th>{{ __('Status') }}</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="line in lineRows" :key="line.id">
                              <td>
                                <div class="font-weight-medium">{{ line.item_code }}</div>
                                <div class="caption grey--text">{{ line.item_name || '-' }}</div>
                                <div class="caption grey--text" v-if="line.stock_uom">{{ __('Stock') }}: {{ line.stock_uom }}</div>
                              </td>
                              <td class="text-right">{{ qty(line.ordered_qty) }}</td>
                              <td>{{ line.uom }}</td>
                              <td class="text-right">{{ qty(line.conversion_factor, 6) }}</td>
                              <td class="text-right">{{ qty(line.ordered_stock_qty) }}</td>
                              <td class="text-right" style="min-width:110px">
                                <v-text-field
                                  v-model="line.picked_qty_input"
                                  dense
                                  hide-details
                                  outlined
                                  type="number"
                                  step="any"
                                  :disabled="!canPick"
                                  @change="onQtyChange(line)"
                                />
                              </td>
                              <td class="text-right">{{ qty(line.picked_stock_qty) }}</td>
                              <td style="min-width:140px">
                                <v-select
                                  v-model="line.pick_status"
                                  dense
                                  hide-details
                                  outlined
                                  :items="lineStatusOptions"
                                  :disabled="!canPick"
                                />
                              </td>
                            </tr>
                          </tbody>
                        </v-simple-table>
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="12" md="5">
                  <v-card outlined class="mb-2" v-if="canDispatch">
                    <v-card-title class="py-2 text-subtitle-2">{{ __('Dispatch Release Proof') }}</v-card-title>
                    <v-card-text class="pt-0">
                      <v-text-field
                        v-model="dispatchProofAckName"
                        dense
                        outlined
                        hide-details
                        data-cy="dispatch-proof-ack"
                        :label="__('Acknowledged By (required)')"
                        class="mb-2"
                      />
                      <v-select
                        v-model="dispatchProofMode"
                        :items="dispatchProofModeOptions"
                        item-text="text"
                        item-value="value"
                        dense
                        outlined
                        hide-details
                        data-cy="dispatch-proof-mode"
                        :label="__('Proof Mode (required)')"
                        class="mb-2"
                      />
                      <v-text-field
                        v-model="dispatchProofRefNo"
                        dense
                        outlined
                        hide-details
                        data-cy="dispatch-proof-ref"
                        :label="__('Reference No (optional)')"
                        class="mb-2"
                      />
                      <v-textarea
                        v-model="dispatchProofNotes"
                        rows="2"
                        dense
                        outlined
                        auto-grow
                        hide-details
                        data-cy="dispatch-proof-notes"
                        :label="__('Proof Notes (optional)')"
                      />
                      <div class="caption red--text mt-2" v-if="!dispatchProofValid">
                        {{ __('Release requires Acknowledged By and Proof Mode.') }}
                      </div>
                    </v-card-text>
                  </v-card>
                  <v-card outlined class="mb-2" v-if="canDispatch">
                    <v-card-title class="py-2 text-subtitle-2">{{ __('Dispatch Mismatch') }}</v-card-title>
                    <v-card-text class="pt-0">
                      <v-select
                        v-model="mismatchReasonCode"
                        :items="mismatchReasonOptions"
                        item-text="text"
                        item-value="value"
                        dense
                        outlined
                        hide-details
                        data-cy="dispatch-mismatch-code"
                        :label="__('Reason Code')"
                        class="mb-2"
                      />
                      <v-textarea
                        v-model="mismatchReasonText"
                        rows="2"
                        dense
                        outlined
                        auto-grow
                        hide-details
                        data-cy="dispatch-mismatch-text"
                        :label="__('Reason Details')"
                        class="mb-2"
                      />
                      <v-checkbox
                        v-model="mismatchRequiresCashierAdjustment"
                        dense
                        hide-details
                        data-cy="dispatch-mismatch-cashier-adjustment"
                        :label="__('Requires cashier adjustment')"
                      />
                    </v-card-text>
                  </v-card>
                  <v-card outlined class="mb-2">
                    <v-card-title class="py-2 text-subtitle-2">{{ __('Notes') }}</v-card-title>
                    <v-card-text class="pt-0">
                      <v-textarea v-model="pickNotes" v-if="canPick" rows="2" dense outlined auto-grow hide-details :label="__('Picker notes')" class="mb-2"/>
                      <v-textarea v-model="dispatchNotes" v-if="canDispatch" rows="2" dense outlined auto-grow hide-details :label="__('Dispatch notes')" />
                    </v-card-text>
                  </v-card>
                  <v-card outlined class="mb-2" v-if="isDetailedView">
                    <v-card-title class="py-2 text-subtitle-2">{{ __('Pick History') }}</v-card-title>
                    <v-card-text class="pt-0 events-wrap">
                      <div v-if="!detail.pick_events.length" class="grey--text">{{ __('No pick events') }}</div>
                      <div v-for="e in detail.pick_events.slice().reverse()" :key="`p-${e.id}`" class="mb-2">
                        <div class="caption font-weight-bold">{{ e.event_type }} | {{ dt(e.created_at) }}</div>
                        <div class="caption grey--text">{{ e.picker_user_id || '-' }}</div>
                        <div class="caption" v-if="e.notes">{{ e.notes }}</div>
                      </div>
                    </v-card-text>
                  </v-card>
                  <v-card outlined v-if="isDetailedView">
                    <v-card-title class="py-2 text-subtitle-2">{{ __('Dispatch + Sync') }}</v-card-title>
                    <v-card-text class="pt-0 events-wrap">
                      <div v-for="e in detail.dispatch_events.slice().reverse()" :key="`d-${e.id}`" class="mb-2">
                        <div class="caption font-weight-bold">{{ e.event_type }} | {{ dt(e.created_at) }}</div>
                        <div class="caption grey--text">{{ e.dispatcher_user_id || '-' }}</div>
                        <div class="caption" v-if="e.notes">{{ e.notes }}</div>
                      </div>
                      <div v-if="!detail.dispatch_events.length" class="grey--text mb-2">{{ __('No dispatch events') }}</div>
                      <div class="caption font-weight-bold mt-2">{{ __('Outbox') }}</div>
                      <div v-for="o in detail.outbox_events.slice().reverse()" :key="`o-${o.event_id}`" class="caption mb-1">
                        {{ o.event_type }} | {{ o.status }} <span v-if="o.cloud_ref">| {{ o.cloud_ref }}</span>
                      </div>
                      <div v-if="!detail.outbox_events.length" class="grey--text">{{ __('No outbox events') }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </template>
            <div v-else class="grey--text text-center py-4">{{ __('Select a queue row') }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script>
import { evntBus } from "../../bus";
import format from "../../format";

export default {
  name: "FulfillmentWorkspace",
  mixins: [format],
  props: {
    pos_profile: { type: [Object, String], default: null },
    current_role: { type: String, default: "" },
  },
  data() {
    return {
      queueRows: [],
      queueLoading: false,
      detailLoading: false,
      actionLoading: false,
      errorText: "",
      detailError: "",
      queueSearch: "",
      queueFilter: "all",
      selectedRef: "",
      detail: null,
      lineDrafts: {},
      pickNotes: "",
      dispatchNotes: "",
      viewMode: "detailed",
      dispatchProofAckName: "",
      dispatchProofMode: "counter",
      dispatchProofRefNo: "",
      dispatchProofNotes: "",
      mismatchReasonCode: "ITEM_MISMATCH",
      mismatchReasonText: "",
      mismatchRequiresCashierAdjustment: true,
      allowPartialRelease: false,
      pollTimer: null,
      lineStatusOptions: ["NOT_PICKED", "PICKED", "PARTIAL", "EXCEPTION"],
      mismatchReasonOptions: [
        { text: __("Item mismatch"), value: "ITEM_MISMATCH" },
        { text: __("Qty mismatch"), value: "QTY_MISMATCH" },
        { text: __("Damaged goods"), value: "DAMAGED_GOODS" },
        { text: __("Customer request"), value: "CUSTOMER_REQUEST" },
        { text: __("Other"), value: "OTHER" },
      ],
      dispatchProofModeOptions: [
        { text: __("Counter pickup"), value: "counter" },
        { text: __("Delivery handover"), value: "delivery" },
        { text: __("Other"), value: "other" },
      ],
    };
  },
  computed: {
    roleCode() {
      const p = (this.current_role || "").trim();
      if (p) return p;
      try {
        const stored = (localStorage.getItem("pos_current_role") || "").trim();
        if (stored) return stored;
      } catch (e) {}
      try {
        const sourceRoles = [];
        if (typeof frappe !== "undefined" && Array.isArray(frappe.user_roles)) {
          sourceRoles.push(...frappe.user_roles);
        }
        if (
          typeof frappe !== "undefined" &&
          frappe.boot &&
          frappe.boot.user &&
          Array.isArray(frappe.boot.user.roles)
        ) {
          sourceRoles.push(...frappe.boot.user.roles);
        }
        const operationalRoles = Array.from(
          new Set(
            sourceRoles
              .map((r) => String(r || "").trim())
              .filter(Boolean)
              .filter((r) =>
                [
                  "cline-Sales Associate",
                  "cline-Cashier",
                  "cline-Picker",
                  "cline-Dispatch",
                  "cline-Supervisor",
                ].includes(r)
              )
          )
        );
        if (operationalRoles.length === 1) {
          try {
            localStorage.setItem("pos_current_role", operationalRoles[0]);
          } catch (e) {}
          return operationalRoles[0];
        }
      } catch (e) {}
      return "";
    },
    canPick() {
      return ["cline-Picker", "cline-Supervisor"].includes(this.roleCode);
    },
    canDispatch() {
      return ["cline-Dispatch", "cline-Supervisor"].includes(this.roleCode);
    },
    roleTitle() {
      if (this.roleCode === "cline-Picker") return __("Picker Queue");
      if (this.roleCode === "cline-Dispatch") return __("Dispatch Queue");
      if (this.roleCode === "cline-Supervisor") return __("Supervisor Fulfillment");
      return __("Fulfillment Queue");
    },
    profileName() {
      if (!this.pos_profile) return "";
      if (typeof this.pos_profile === "string") return this.pos_profile;
      return (this.pos_profile.name || "").trim();
    },
    soAgeMaxDays() {
      const raw =
        this.pos_profile && typeof this.pos_profile === "object"
          ? this.pos_profile.posa_sales_order_lookup_max_age_days
          : 1;
      return Math.max(0, Number(raw || 1) || 1);
    },
    relayBase() {
      const v =
        this.pos_profile && typeof this.pos_profile === "object"
          ? (this.pos_profile.custom_edge_relay_url || "").trim()
          : "";
      return (v || "http://127.0.0.1:8787").replace(/\/$/, "");
    },
    filters() {
      const rows = [{ value: "all", label: __("All"), color: "primary" }];
      if (this.canPick) {
        rows.push(
          { value: "pending", label: __("Pending"), color: "warning" },
          { value: "in_progress", label: __("In Progress"), color: "primary" },
          { value: "exception", label: __("Exception"), color: "error" },
          { value: "picked_ready", label: __("Picked Ready"), color: "success" }
        );
      }
      if (this.canDispatch) {
        rows.push({ value: "dispatch_ready", label: __("Dispatch Ready"), color: "success" });
      }
      return rows.filter((r, i, a) => a.findIndex((x) => x.value === r.value) === i);
    },
    filteredRows() {
      const s = (this.queueSearch || "").toLowerCase();
      const rows = (this.queueRows || []).filter((r) => {
        const pick = String(r.pick_status || "").toUpperCase();
        const dispatch = String(r.dispatch_status || "").toUpperCase();
        if (this.queueFilter === "pending" && pick !== "PAID_PENDING_PICK") return false;
        if (this.queueFilter === "in_progress" && pick !== "PICK_IN_PROGRESS") return false;
        if (this.queueFilter === "exception" && pick !== "PICK_EXCEPTION") return false;
        if (this.queueFilter === "picked_ready" && pick !== "PICKED_READY_FOR_RELEASE") return false;
        if (this.queueFilter === "dispatch_ready" && !(pick === "PICKED_READY_FOR_RELEASE" && dispatch !== "RELEASED")) return false;
        if (!s) return true;
        return [r.local_sale_ref, r.token_id, r.customer_id, r.customer_name].filter(Boolean).join(" ").toLowerCase().includes(s);
      });
      return this.sortRowsForWorkflow(rows);
    },
    lineRows() {
      if (!this.detail || !this.detail.lines) return [];
      return this.detail.lines.map((line) => this.lineDrafts[line.id] || this.makeLineDraft(line));
    },
    canRelease() {
      if (!this.detail || !this.detail.sale) return false;
      const sale = this.detail.sale;
      if (String(sale.dispatch_status || "").toUpperCase() === "RELEASED") return false;
      const pick = String(sale.pick_status || "").toUpperCase();
      return (
        parseInt(sale.paid || 0, 10) === 1 &&
        (pick === "PICKED_READY_FOR_RELEASE" || (this.allowPartialRelease && pick === "PICK_EXCEPTION")) &&
        this.dispatchProofValid
      );
    },
    isDetailedView() {
      return String(this.viewMode || "detailed") !== "simple";
    },
    dispatchProofValid() {
      if (!this.canDispatch) return true;
      const ack = String(this.dispatchProofAckName || "").trim();
      const mode = String(this.dispatchProofMode || "").trim().toLowerCase();
      return !!ack && ["counter", "delivery", "other"].includes(mode);
    },
    hasDispatchProofOnSale() {
      const sale = (this.detail && this.detail.sale) || {};
      const proof = sale.dispatch_proof || sale.dispatch_proof_payload || {};
      return proof && typeof proof === "object" && !!String(proof.ack_name || "").trim();
    },
    dispatchProofSummaryText() {
      const sale = (this.detail && this.detail.sale) || {};
      const proof = sale.dispatch_proof || sale.dispatch_proof_payload || {};
      if (!proof || typeof proof !== "object") return "";
      const ack = String(proof.ack_name || "").trim() || "-";
      const mode = String(proof.proof_mode || "").trim() || "-";
      const ref = String(proof.proof_ref_no || "").trim();
      const at = String(proof.captured_at || "").trim();
      const parts = [`${__("Ack")}: ${ack}`, `${__("Mode")}: ${mode}`];
      if (ref) parts.push(`${__("Ref")}: ${ref}`);
      if (at) parts.push(`${__("At")}: ${this.dt(at)}`);
      return parts.join(" | ");
    },
    dispatchQueueStats() {
      const rows = Array.isArray(this.queueRows) ? this.queueRows : [];
      const stats = {
        ready_count: 0,
        picking_count: 0,
        exception_count: 0,
        over_sla_count: 0,
        avg_ready_wait_ms: 0,
        avg_ready_wait_label: "-",
        oldest_open_age_ms: 0,
        oldest_open_age_label: "-",
      };
      const nowMs = Date.now();
      let readyWaitTotal = 0;
      let readyWaitCount = 0;
      rows.forEach((r) => {
        const pick = String(r.pick_status || "").toUpperCase();
        const dispatch = String(r.dispatch_status || "").toUpperCase();
        if (dispatch === "RELEASED") return;
        if (pick === "PICKED_READY_FOR_RELEASE") {
          stats.ready_count += 1;
          const ms = this.msSince(r.updated_at, nowMs);
          if (ms > 0) {
            readyWaitTotal += ms;
            readyWaitCount += 1;
          }
        } else if (pick === "PICK_IN_PROGRESS") {
          stats.picking_count += 1;
        } else if (pick === "PICK_EXCEPTION") {
          stats.exception_count += 1;
        }
        if (this.queueSlaState(r) === "critical") stats.over_sla_count += 1;
        const age = this.msSince(r.created_at, nowMs);
        if (age > stats.oldest_open_age_ms) stats.oldest_open_age_ms = age;
      });
      if (readyWaitCount > 0) {
        stats.avg_ready_wait_ms = Math.round(readyWaitTotal / readyWaitCount);
        stats.avg_ready_wait_label = this.durationLabel(stats.avg_ready_wait_ms);
      }
      if (stats.oldest_open_age_ms > 0) {
        stats.oldest_open_age_label = this.durationLabel(stats.oldest_open_age_ms);
      }
      return stats;
    },
    detailPhaseMetrics() {
      if (!this.detail || !this.detail.sale) return null;
      const sale = this.detail.sale || {};
      const pickEvents = this.sortEventsByCreatedAt(this.detail.pick_events || []);
      const dispatchEvents = this.sortEventsByCreatedAt(this.detail.dispatch_events || []);
      const outboxEvents = this.sortEventsByCreatedAt(this.detail.outbox_events || []);

      const metrics = {
        paid_local_at:
          this.firstEventAt(outboxEvents, ["SALE_COMMITTED"]) || sale.created_at || "",
        pick_started_at: this.firstEventAt(pickEvents, ["PICK_IN_PROGRESS"]),
        pick_last_progress_at: this.lastEventAt(pickEvents, ["PICK_IN_PROGRESS"]),
        pick_ready_at: this.lastEventAt(pickEvents, ["PICKED_READY_FOR_RELEASE"]),
        pick_exception_first_at: this.firstEventAt(pickEvents, ["PICK_EXCEPTION"]),
        pick_exception_last_at: this.lastEventAt(pickEvents, ["PICK_EXCEPTION"]),
        released_at: sale.released_at || this.lastEventAt(dispatchEvents, ["RELEASED"]),
        cloud_synced_at: "",
      };

      const saleCommittedDone = [...outboxEvents]
        .reverse()
        .find(
          (o) =>
            String(o && o.event_type || "").toUpperCase() === "SALE_COMMITTED" &&
            String(o && o.status || "").toLowerCase() === "done"
        );
      metrics.cloud_synced_at =
        (saleCommittedDone && (saleCommittedDone.updated_at || saleCommittedDone.created_at)) || "";

      const phaseCandidates = [
        { key: "released", at: metrics.released_at, label: __("Released") },
        { key: "pick_exception", at: metrics.pick_exception_last_at, label: __("Pick Exception") },
        { key: "picked_ready", at: metrics.pick_ready_at, label: __("Picked Ready For Release") },
        { key: "pick_in_progress", at: metrics.pick_last_progress_at || metrics.pick_started_at, label: __("Picking In Progress") },
        { key: "paid_pending_pick", at: metrics.paid_local_at, label: __("Paid Pending Pick") },
      ];
      const activePhase =
        phaseCandidates.find((row) => this.parseIsoMs(row.at) > 0) || { key: "unknown", at: "", label: __("Unknown") };
      metrics.current_phase_key = activePhase.key;
      metrics.current_phase_label = activePhase.label;
      metrics.current_phase_started_at = activePhase.at || "";
      return metrics;
    },
    detailPhaseTimeline() {
      const m = this.detailPhaseMetrics;
      if (!m) return [];

      const rows = [];
      const add = (key, label, at, prevAt) => {
        const atMs = this.parseIsoMs(at);
        const prevMs = this.parseIsoMs(prevAt);
        rows.push({
          key,
          label,
          at_raw: at || "",
          at_label: at ? this.dt(at) : "-",
          duration_label: atMs && prevMs && atMs >= prevMs ? this.durationLabel(atMs - prevMs) : "",
        });
      };
      add("paid_local", __("Paid / Local Commit"), m.paid_local_at, "");
      add("pick_started", __("Pick Started"), m.pick_started_at, m.paid_local_at);
      add("pick_ready", __("Picked Ready"), m.pick_ready_at, m.pick_started_at || m.paid_local_at);
      if (m.pick_exception_last_at) add("pick_exception", __("Last Exception"), m.pick_exception_last_at, m.pick_started_at || m.paid_local_at);
      add("released", __("Released"), m.released_at, m.pick_ready_at || m.pick_started_at || m.paid_local_at);
      if (m.cloud_synced_at) {
        add(
          "cloud_synced",
          __("Cloud Synced (SI Submitted)"),
          m.cloud_synced_at,
          m.released_at || m.pick_ready_at || m.pick_started_at || m.paid_local_at
        );
      }
      return rows;
    },
    detailPhaseSummaryLines() {
      const m = this.detailPhaseMetrics;
      if (!m) return [];
      const createdMs = this.parseIsoMs(m.paid_local_at);
      const pickStartMs = this.parseIsoMs(m.pick_started_at);
      const pickReadyMs = this.parseIsoMs(m.pick_ready_at);
      const releasedMs = this.parseIsoMs(m.released_at);
      const cloudSyncedMs = this.parseIsoMs(m.cloud_synced_at);
      const lines = [];
      if (createdMs && pickStartMs && pickStartMs >= createdMs) {
        lines.push(`${__("Paid -> Pick Start")}: ${this.durationLabel(pickStartMs - createdMs)}`);
      }
      if (pickStartMs && pickReadyMs && pickReadyMs >= pickStartMs) {
        lines.push(`${__("Pick Start -> Picked Ready")}: ${this.durationLabel(pickReadyMs - pickStartMs)}`);
      }
      if (pickReadyMs && releasedMs && releasedMs >= pickReadyMs) {
        lines.push(`${__("Picked Ready -> Released")}: ${this.durationLabel(releasedMs - pickReadyMs)}`);
      }
      if (createdMs && releasedMs && releasedMs >= createdMs) {
        lines.push(`${__("Paid -> Released (Total)")}: ${this.durationLabel(releasedMs - createdMs)}`);
      }
      if (releasedMs && cloudSyncedMs && cloudSyncedMs >= releasedMs) {
        lines.push(`${__("Released -> Cloud Synced")}: ${this.durationLabel(cloudSyncedMs - releasedMs)}`);
      }
      if (m.current_phase_started_at) {
        lines.push(`${__("Current Phase Age")}: ${this.durationLabel(this.msSince(m.current_phase_started_at))}`);
      }
      if (!releasedMs && createdMs) {
        lines.push(`${__("Open Age")}: ${this.durationLabel(Date.now() - createdMs)}`);
      }
      return lines;
    },
    detailMonitorSnapshot() {
      if (!this.detail || !this.detail.sale) return null;
      const sale = this.detail.sale || {};
      const m = this.detailPhaseMetrics;
      const openAgeMs = this.msSince((m && m.paid_local_at) || sale.created_at);
      const phaseAgeMs = this.msSince((m && m.current_phase_started_at) || sale.updated_at || sale.created_at);
      return {
        phase_label: (m && m.current_phase_label) || this.queuePhaseLabel(sale),
        phase_age_label: this.durationLabel(phaseAgeMs),
        open_age_label: this.durationLabel(openAgeMs),
        sla_label: this.queueSlaLabel(sale),
        sla_state: this.queueSlaState(sale),
      };
    },
  },
  watch: {
    pos_profile: {
      handler() {
        this.fetchQueue(true);
      },
      deep: true,
    },
    roleCode() {
      if (this.roleCode === "cline-Dispatch" && this.queueFilter === "all") {
        this.queueFilter = "dispatch_ready";
      }
      this.fetchQueue(true);
    },
  },
  mounted() {
    if (this.roleCode === "cline-Dispatch") {
      this.queueFilter = "dispatch_ready";
    }
    this.fetchQueue(true);
    this.pollTimer = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      this.fetchQueue(false, true);
      if (this.selectedRef) this.fetchDetail(this.selectedRef, true);
    }, 5000);
  },
  beforeDestroy() {
    if (this.pollTimer) clearInterval(this.pollTimer);
  },
  methods: {
    showMessage(text, color) {
      evntBus.$emit("show_mesage", { text, color });
    },
    relayHeaders(extra = {}) {
      const headers = { ...extra };
      try {
        const relayKey = (localStorage.getItem("posa_relay_client_key") || "").trim();
        if (relayKey) headers["X-Relay-Client-Key"] = relayKey;
      } catch (e) {}
      return headers;
    },
    async getJson(path) {
      const r = await fetch(`${this.relayBase}${path}`, {
        headers: this.relayHeaders({ Accept: "application/json" }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.message || data.code || `HTTP ${r.status}`);
      return data;
    },
    async postJson(path, payload) {
      const r = await fetch(`${this.relayBase}${path}`, {
        method: "POST",
        headers: this.relayHeaders({ "Content-Type": "application/json", Accept: "application/json" }),
        body: JSON.stringify(payload || {}),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok || data.ok === false) throw new Error(data.message || data.code || `HTTP ${r.status}`);
      return data;
    },
    async fetchQueue(preferSelect, quiet) {
      if (!this.profileName) return;
      if (!quiet) this.queueLoading = true;
      this.errorText = "";
      try {
        const q = `?pos_profile_id=${encodeURIComponent(this.profileName)}&limit=200`;
        const data = await this.getJson(`/relay/pick-queue${q}`);
        this.queueRows = Array.isArray(data.rows) ? data.rows : [];
        if (!this.queueRows.some((r) => r.local_sale_ref === this.selectedRef)) {
          this.selectedRef = "";
          this.detail = null;
        }
        if ((preferSelect || !this.selectedRef) && this.filteredRows.length) {
          this.selectRow(this.filteredRows[0]);
        }
      } catch (e) {
        this.errorText = `Relay queue load failed: ${String(e.message || e)}`;
      } finally {
        this.queueLoading = false;
      }
    },
    async selectRow(row) {
      if (!row || !row.local_sale_ref) return;
      this.selectedRef = row.local_sale_ref;
      await this.fetchDetail(this.selectedRef);
    },
    async fetchDetail(localSaleRef, quiet) {
      if (!localSaleRef) return;
      if (!quiet) this.detailLoading = true;
      this.detailError = "";
      try {
        const data = await this.getJson(`/api/transactions/${encodeURIComponent(localSaleRef)}`);
        this.detail = data;
        this.buildDraftsFromDetail();
      } catch (e) {
        this.detailError = `Relay sale detail load failed: ${String(e.message || e)}`;
      } finally {
        this.detailLoading = false;
      }
    },
    buildDraftsFromDetail() {
      const next = {};
      const eventMap = {};
      (this.detail.pick_events || []).forEach((e) => {
        if (!e || !e.payload || !Array.isArray(e.payload.line_updates)) return;
        e.payload.line_updates.forEach((u) => {
          const id = parseInt(u.line_id || u.id || 0, 10);
          if (id) eventMap[id] = u;
        });
      });
      (this.detail.lines || []).forEach((line) => {
        next[line.id] = this.makeLineDraft(line, eventMap[line.id]);
      });
      this.lineDrafts = next;
      this.syncDispatchInputsFromDetail();
    },
    syncDispatchInputsFromDetail() {
      const sale = (this.detail && this.detail.sale) || {};
      const proofRaw = sale.dispatch_proof || sale.dispatch_proof_payload || {};
      const proof = proofRaw && typeof proofRaw === "object" ? proofRaw : {};
      const ack = String(proof.ack_name || "").trim();
      const mode = String(proof.proof_mode || "").trim().toLowerCase();
      const refNo = String(proof.proof_ref_no || "").trim();
      const notes = String(proof.proof_notes || "").trim();

      this.dispatchProofAckName = ack || this.dispatchProofAckName || "";
      this.dispatchProofMode = ["counter", "delivery", "other"].includes(mode)
        ? mode
        : this.dispatchProofMode || "counter";
      this.dispatchProofRefNo = refNo || "";
      this.dispatchProofNotes = notes || "";
      this.mismatchRequiresCashierAdjustment = Number(sale.cashier_adjustment_required || 0) === 1;
    },
    makeLineDraft(line, fallback) {
      const payload = line && typeof line.payload === "object" ? line.payload : {};
      const picker = payload && typeof payload.picker === "object" ? payload.picker : {};
      const fb = fallback || {};
      const orderedQty = this.num(line.qty, 0);
      const conv = this.lineConversion(line);
      const ordStock = this.num(payload.stock_qty, orderedQty * conv);
      const pickedQty = this.num(picker.picked_qty != null ? picker.picked_qty : fb.picked_qty, orderedQty);
      const pickedStock = this.num(
        picker.picked_stock_qty != null ? picker.picked_stock_qty : fb.picked_stock_qty,
        pickedQty * conv
      );
      return {
        id: line.id,
        item_code: line.item_code || "",
        item_name: line.item_name || "",
        ordered_qty: orderedQty,
        uom: line.uom || "",
        conversion_factor: conv,
        stock_uom: String(payload.stock_uom || "").trim(),
        ordered_stock_qty: ordStock,
        picked_qty: pickedQty,
        picked_qty_input: String(pickedQty),
        picked_stock_qty: pickedStock,
        pick_status: String(picker.pick_status || fb.pick_status || line.pick_status || "").toUpperCase() || (Math.abs(pickedQty - orderedQty) < 1e-9 ? "PICKED" : "PARTIAL"),
      };
    },
    lineConversion(line) {
      const payload = line && typeof line.payload === "object" ? line.payload : {};
      const direct = parseFloat(payload.conversion_factor);
      if (!isNaN(direct) && direct) return direct;
      const qty = this.num(line.qty, 0);
      const stockQty = parseFloat(payload.stock_qty);
      if (qty && !isNaN(stockQty)) return stockQty / qty;
      return 1;
    },
    num(v, fb) {
      const n = parseFloat(v);
      return isNaN(n) ? (fb == null ? 0 : fb) : n;
    },
    onQtyChange(line) {
      const q = Math.max(0, this.num(line.picked_qty_input, line.ordered_qty));
      line.picked_qty = q;
      line.picked_qty_input = String(q);
      line.picked_stock_qty = q * this.num(line.conversion_factor, 1);
      if (line.pick_status !== "EXCEPTION") {
        line.pick_status = Math.abs(q - line.ordered_qty) < 1e-9 ? "PICKED" : q > 0 ? "PARTIAL" : "NOT_PICKED";
      }
      this.$set(this.lineDrafts, line.id, { ...line });
    },
    markAllPicked() {
      this.lineRows.forEach((line) => {
        line.picked_qty = this.num(line.ordered_qty, 0);
        line.picked_qty_input = String(line.picked_qty);
        line.picked_stock_qty = line.picked_qty * this.num(line.conversion_factor, 1);
        if (line.pick_status !== "EXCEPTION") line.pick_status = "PICKED";
        this.$set(this.lineDrafts, line.id, { ...line });
      });
    },
    buildLineUpdates() {
      return this.lineRows.map((line) => ({
        line_id: line.id,
        item_code: line.item_code,
        item_name: line.item_name || "",
        ordered_qty: this.num(line.ordered_qty, 0),
        ordered_uom: line.uom || "",
        picked_qty: this.num(line.picked_qty, this.num(line.ordered_qty, 0)),
        picked_uom: line.uom || "",
        conversion_factor: this.num(line.conversion_factor, 1),
        picked_stock_qty: this.num(line.picked_stock_qty, 0),
        pick_status: String(line.pick_status || "").toUpperCase(),
      }));
    },
    buildLineSnapshot() {
      return this.lineRows.map((line) => ({
        line_id: line.id,
        item_code: line.item_code || "",
        item_name: line.item_name || "",
        ordered_qty: this.num(line.ordered_qty, 0),
        ordered_uom: line.uom || "",
        picked_qty: this.num(line.picked_qty, this.num(line.ordered_qty, 0)),
        picked_uom: line.uom || "",
        conversion_factor: this.num(line.conversion_factor, 1),
        picked_stock_qty: this.num(line.picked_stock_qty, 0),
        pick_status: String(line.pick_status || "").toUpperCase(),
      }));
    },
    lineSummary(updates) {
      const s = { total_count: updates.length, picked_count: 0, partial_count: 0, exception_count: 0, not_picked_count: 0 };
      updates.forEach((u) => {
        const k = String(u.pick_status || "").toUpperCase();
        if (k === "PICKED") s.picked_count += 1;
        else if (k === "PARTIAL") s.partial_count += 1;
        else if (k === "EXCEPTION") s.exception_count += 1;
        else if (k === "NOT_PICKED") s.not_picked_count += 1;
      });
      return s;
    },
    async pickUpdate(status) {
      if (!this.selectedRef) return;
      this.actionLoading = true;
      try {
        const line_updates = this.buildLineUpdates();
        const payload = {
          local_sale_ref: this.selectedRef,
          picking_status: status,
          picker_user_id: (frappe.session && frappe.session.user) || "",
          pos_profile_id: this.profileName,
          role: this.roleCode,
          notes: this.pickNotes || "",
          line_updates,
          line_summary: this.lineSummary(line_updates),
        };
        const r = await this.postJson("/relay/pick/update", payload);
        this.showMessage(`Pick status updated: ${r.pick_status || status}`, "success");
        await this.fetchDetail(this.selectedRef);
        await this.fetchQueue(false);
      } catch (e) {
        this.showMessage(`Pick update failed: ${String(e.message || e)}`, "error");
      } finally {
        this.actionLoading = false;
      }
    },
    markPickedReady() {
      if (this.lineRows.some((l) => ["EXCEPTION", "NOT_PICKED"].includes(String(l.pick_status || "").toUpperCase()))) {
        this.showMessage(__("Cannot mark picked-ready while any line is EXCEPTION/NOT_PICKED."), "warning");
        return;
      }
      this.pickUpdate("PICKED_READY_FOR_RELEASE");
    },
    async releaseSale() {
      if (!this.selectedRef) return;
      if (!this.dispatchProofValid) {
        this.showMessage(__("Dispatch proof is required before release."), "warning");
        return;
      }
      this.actionLoading = true;
      try {
        const line_updates = this.buildLineUpdates();
        const line_snapshot = this.buildLineSnapshot();
        const r = await this.postJson("/relay/dispatch/release", {
          local_sale_ref: this.selectedRef,
          dispatcher_user_id: (frappe.session && frappe.session.user) || "",
          allow_partial: !!this.allowPartialRelease,
          notes: this.dispatchNotes || "",
          proof_ack_name: String(this.dispatchProofAckName || "").trim(),
          proof_mode: String(this.dispatchProofMode || "").trim().toLowerCase(),
          proof_ref_no: String(this.dispatchProofRefNo || "").trim(),
          proof_notes: String(this.dispatchProofNotes || "").trim(),
          line_snapshot,
          role: this.roleCode,
          line_summary: this.lineSummary(line_updates),
        });
        this.showMessage(`Dispatch updated: ${r.dispatch_status || "RELEASED"}`, "success");
        await this.fetchDetail(this.selectedRef);
        await this.fetchQueue(false);
      } catch (e) {
        this.showMessage(`Dispatch failed: ${String(e.message || e)}`, "error");
      } finally {
        this.actionLoading = false;
      }
    },
    async flagMismatch() {
      if (!this.selectedRef) return;
      const reasonCode = String(this.mismatchReasonCode || "").trim().toUpperCase();
      const reasonText = String(this.mismatchReasonText || "").trim();
      if (!reasonCode && !reasonText) {
        this.showMessage(__("Mismatch reason is required."), "warning");
        return;
      }
      this.actionLoading = true;
      try {
        const line_snapshot = this.buildLineSnapshot();
        const payload = {
          local_sale_ref: this.selectedRef,
          dispatcher_user_id: (frappe.session && frappe.session.user) || "",
          reason_code: reasonCode,
          reason_text: reasonText,
          requires_cashier_adjustment: !!this.mismatchRequiresCashierAdjustment,
          pos_profile_id: this.profileName,
          role: this.roleCode,
          notes: this.dispatchNotes || reasonText,
          line_snapshot,
        };
        const r = await this.postJson("/relay/dispatch/mismatch", payload);
        this.showMessage(
          `Dispatch mismatch flagged: ${r.dispatch_exception_state || "MISMATCH_RETURNED_TO_PICKER"}`,
          "warning"
        );
        this.mismatchReasonText = "";
        await this.fetchDetail(this.selectedRef);
        await this.fetchQueue(false);
      } catch (e) {
        this.showMessage(`Dispatch mismatch failed: ${String(e.message || e)}`, "error");
      } finally {
        this.actionLoading = false;
      }
    },
    refreshAll() {
      this.fetchQueue(false);
      if (this.selectedRef) this.fetchDetail(this.selectedRef);
    },
    sortEventsByCreatedAt(events) {
      return (Array.isArray(events) ? [...events] : []).sort((a, b) => {
        const am = this.parseIsoMs(a && a.created_at);
        const bm = this.parseIsoMs(b && b.created_at);
        return am - bm;
      });
    },
    parseIsoMs(v) {
      if (!v) return 0;
      const t = new Date(v).getTime();
      return isNaN(t) ? 0 : t;
    },
    msSince(v, nowMs) {
      const t = this.parseIsoMs(v);
      if (!t) return 0;
      const diff = (nowMs || Date.now()) - t;
      return diff > 0 ? diff : 0;
    },
    durationLabel(ms) {
      const n = Math.max(0, parseInt(ms || 0, 10));
      if (!n) return "0m";
      const totalSec = Math.floor(n / 1000);
      const d = Math.floor(totalSec / 86400);
      const h = Math.floor((totalSec % 86400) / 3600);
      const m = Math.floor((totalSec % 3600) / 60);
      if (d > 0) return `${d}d ${h}h`;
      if (h > 0) return `${h}h ${m}m`;
      return `${m}m`;
    },
    queueAgeLabel(row) {
      return this.durationLabel(this.msSince(row && row.created_at));
    },
    queueOrderAgeDays(row) {
      if (!row) return 0;
      const explicit = Number(row.order_age_days);
      if (!isNaN(explicit) && explicit >= 0) return explicit;
      const createdMs = this.parseIsoMs(row.created_at);
      if (!createdMs) return 0;
      return Math.max(0, Math.floor((Date.now() - createdMs) / (24 * 60 * 60 * 1000)));
    },
    queueRowIsStale(row) {
      return this.queueOrderAgeDays(row) > this.soAgeMaxDays;
    },
    queuePhaseAnchorAt(row) {
      if (!row) return "";
      const pick = String(row.pick_status || "").toUpperCase();
      const dispatch = String(row.dispatch_status || "").toUpperCase();
      if (dispatch === "RELEASED") return row.released_at || row.updated_at || row.created_at || "";
      if (pick === "PICKED_READY_FOR_RELEASE") return row.updated_at || row.created_at || "";
      if (pick === "PICK_EXCEPTION") return row.updated_at || row.created_at || "";
      if (pick === "PICK_IN_PROGRESS") return row.updated_at || row.created_at || "";
      return row.created_at || row.updated_at || "";
    },
    queuePhaseAgeMs(row) {
      return this.msSince(this.queuePhaseAnchorAt(row));
    },
    queuePhaseAgeLabel(row) {
      return this.durationLabel(this.queuePhaseAgeMs(row));
    },
    queuePhaseLabel(row) {
      if (!row) return __("Time In Current Phase");
      const pick = String(row.pick_status || "").toUpperCase();
      const dispatch = String(row.dispatch_status || "").toUpperCase();
      if (dispatch === "RELEASED") return __("Released For");
      if (pick === "PICKED_READY_FOR_RELEASE") return __("Wait For Dispatch");
      if (pick === "PICK_EXCEPTION") return __("Exception For");
      if (pick === "PICK_IN_PROGRESS") return __("Picking For");
      if (pick === "PAID_PENDING_PICK") return __("Wait For Pick");
      return __("Time In Current Phase");
    },
    queueSlaState(row) {
      const pick = String((row && row.pick_status) || "").toUpperCase();
      const dispatch = String((row && row.dispatch_status) || "").toUpperCase();
      const phaseAge = this.queuePhaseAgeMs(row);
      if (dispatch === "RELEASED") return "ok";
      if (pick === "PICK_EXCEPTION") return "critical";
      if (pick === "PICKED_READY_FOR_RELEASE") {
        if (phaseAge >= 20 * 60 * 1000) return "critical";
        if (phaseAge >= 10 * 60 * 1000) return "warn";
        return "ok";
      }
      if (pick === "PICK_IN_PROGRESS") {
        if (phaseAge >= 30 * 60 * 1000) return "critical";
        if (phaseAge >= 15 * 60 * 1000) return "warn";
        return "ok";
      }
      if (pick === "PAID_PENDING_PICK") {
        if (phaseAge >= 20 * 60 * 1000) return "critical";
        if (phaseAge >= 8 * 60 * 1000) return "warn";
        return "ok";
      }
      return "ok";
    },
    queueSlaLabel(row) {
      const state = this.queueSlaState(row);
      if (state === "critical") return __("SLA: High");
      if (state === "warn") return __("SLA: Watch");
      return __("SLA: OK");
    },
    queueSlaChipColor(row) {
      const state = this.queueSlaState(row);
      if (state === "critical") return "error";
      if (state === "warn") return "warning";
      return "grey";
    },
    queueSlaTextClass(row) {
      const state = this.queueSlaState(row);
      if (state === "critical") return "error--text";
      if (state === "warn") return "warning--text";
      return "grey--text";
    },
    queuePriorityRank(row) {
      const pick = String((row && row.pick_status) || "").toUpperCase();
      const dispatch = String((row && row.dispatch_status) || "").toUpperCase();
      if (dispatch === "RELEASED") return 99;
      if (pick === "PICK_EXCEPTION") return 0;
      if (pick === "PICKED_READY_FOR_RELEASE") return 1;
      if (pick === "PICK_IN_PROGRESS") return 2;
      if (pick === "PAID_PENDING_PICK") return 3;
      return 4;
    },
    compareQueueRows(a, b) {
      const priorityA = this.queuePriorityRank(a);
      const priorityB = this.queuePriorityRank(b);
      if (priorityA !== priorityB) return priorityA - priorityB;

      const slaScore = { ok: 0, warn: 1, critical: 2 };
      const slaA = slaScore[this.queueSlaState(a)] || 0;
      const slaB = slaScore[this.queueSlaState(b)] || 0;
      if (slaA !== slaB) return slaB - slaA;

      const phaseAgeA = this.queuePhaseAgeMs(a);
      const phaseAgeB = this.queuePhaseAgeMs(b);
      if (phaseAgeA !== phaseAgeB) return phaseAgeB - phaseAgeA;

      const ageA = this.msSince(a && a.created_at);
      const ageB = this.msSince(b && b.created_at);
      if (ageA !== ageB) return ageB - ageA;

      return String((a && a.local_sale_ref) || "").localeCompare(String((b && b.local_sale_ref) || ""));
    },
    sortRowsForWorkflow(rows) {
      const list = Array.isArray(rows) ? [...rows] : [];
      if (!list.length) return list;
      if (this.canDispatch || this.canPick) return list.sort((a, b) => this.compareQueueRows(a, b));
      return list.sort((a, b) => this.msSince(b && b.created_at) - this.msSince(a && a.created_at));
    },
    firstEventAt(events, types) {
      const wanted = (types || []).map((t) => String(t || "").toUpperCase());
      const rows = this.sortEventsByCreatedAt(events);
      for (let i = 0; i < rows.length; i += 1) {
        const e = rows[i] || {};
        const et = String(e.event_type || "").toUpperCase();
        if (wanted.includes(et) && e.created_at) return e.created_at;
      }
      return "";
    },
    lastEventAt(events, types) {
      const wanted = (types || []).map((t) => String(t || "").toUpperCase());
      const rows = this.sortEventsByCreatedAt(events);
      for (let i = rows.length - 1; i >= 0; i -= 1) {
        const e = rows[i] || {};
        const et = String(e.event_type || "").toUpperCase();
        if (wanted.includes(et) && e.created_at) return e.created_at;
      }
      return "";
    },
    dt(v) {
      if (!v) return "-";
      try {
        if (frappe.datetime && frappe.datetime.str_to_user) return frappe.datetime.str_to_user(v);
      } catch (e) {}
      return String(v);
    },
    money(v) {
      const c = (this.pos_profile && this.pos_profile.currency) || "";
      return `${this.currencySymbol(c)} ${this.formtCurrency(this.num(v, 0))}`;
    },
    qty(v, p) {
      return this.formtFloat(this.num(v, 0), p || this.float_precision || 2);
    },
    pickColor(s) {
      const v = String(s || "").toUpperCase();
      if (v === "PAID_PENDING_PICK") return "warning";
      if (v === "PICK_IN_PROGRESS") return "primary";
      if (v === "PICK_EXCEPTION") return "error";
      if (v === "PICKED_READY_FOR_RELEASE") return "success";
      return "grey";
    },
    dispatchColor(s) {
      return String(s || "").toUpperCase() === "RELEASED" ? "success" : "warning";
    },
    syncColor(s) {
      return String(s || "").toUpperCase() === "SALE_SYNCED_SI_SUBMITTED" ? "success" : "warning";
    },
  },
};
</script>

<style scoped>
.queue-list {
  max-height: 65vh;
  overflow-y: auto;
  border: 1px solid rgba(0,0,0,.06);
  border-radius: 6px;
}
.active {
  background: rgba(33, 150, 243, .08);
}
.lines-wrap {
  max-height: 36vh;
  overflow: auto;
}
.events-wrap {
  max-height: 26vh;
  overflow-y: auto;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
