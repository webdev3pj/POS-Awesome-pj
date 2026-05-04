<template>
  <div class="workflow-state-block">
    <div class="workflow-ticket-current-state">
      {{ currentLabel }}
    </div>
    <div class="workflow-state-strip" :aria-label="stateAria">
      <div
        v-for="step in steps"
        :key="step.key"
        class="workflow-state-step"
        :class="'workflow-state-step-' + step.state"
      >
        <span class="workflow-state-dot">
          <v-icon x-small>{{ step.icon }}</v-icon>
        </span>
        <span class="workflow-state-label">{{ step.label }}</span>
      </div>
    </div>
    <div class="workflow-ticket-state-fields">
      <span>{{ __('Token') }}: {{ row.token_status || '-' }}</span>
      <span>{{ __('Pick') }}: {{ row.picking_status || '-' }}</span>
      <span>{{ __('Dispatch') }}: {{ row.dispatch_status || '-' }}</span>
    </div>
  </div>
</template>

<script>
import {
  workflowCurrentLabel,
  workflowStateAria,
  workflowSteps,
} from './workflowDisplay';

export default {
  props: {
    row: {
      type: Object,
      required: true,
    },
  },
  computed: {
    currentLabel() {
      return workflowCurrentLabel(this.row);
    },
    steps() {
      return workflowSteps(this.row);
    },
    stateAria() {
      return workflowStateAria(this.row);
    },
  },
};
</script>

<style scoped>
.workflow-ticket-current-state {
  margin: 2px 0 5px;
  color: #0f172a;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.25;
}

.workflow-state-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 4px;
  margin: 5px 0;
}

.workflow-state-step {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 4px 5px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
  color: #64748b;
}

.workflow-state-step-done {
  border-color: #a7f3d0;
  background: #ecfdf5;
  color: #047857;
}

.workflow-state-step-active {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.12);
}

.workflow-state-step-blocked {
  border-color: #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.workflow-state-dot {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.workflow-state-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10px;
  font-weight: 700;
}

.workflow-ticket-state-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 4px 0 5px;
}

.workflow-ticket-state-fields span {
  max-width: 100%;
  padding: 2px 5px;
  border-radius: 5px;
  background: #f1f5f9;
  color: #475569;
  font-size: 10px;
  line-height: 1.25;
}
</style>
