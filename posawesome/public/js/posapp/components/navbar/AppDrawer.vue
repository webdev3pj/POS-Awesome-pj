<template>
  <v-navigation-drawer
    v-model="drawerModel"
    :mini-variant.sync="miniModel"
    app
    class="primary margen-top"
    width="170"
  >
    <v-list dark>
      <v-list-item class="px-2">
        <v-list-item-avatar>
          <v-img :src="companyImg"></v-img>
        </v-list-item-avatar>

        <v-list-item-title>{{ company }}</v-list-item-title>

        <v-btn icon @click.stop="miniModel = !miniModel">
          <v-icon>mdi-chevron-left</v-icon>
        </v-btn>
      </v-list-item>
      <v-list-item-group v-model="activeItemModel" color="white">
        <v-list-item
          v-for="entry in items"
          :key="entry.text"
          @click="$emit('change-page', entry.text)"
        >
          <v-list-item-icon>
            <v-icon v-text="entry.icon"></v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title v-text="entry.text"></v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list-item-group>
      <v-divider v-if="showWorkflowMonitorToggle" class="my-2"></v-divider>
      <v-list-item
        v-if="showWorkflowMonitorToggle"
        class="workflow-monitor-drawer-item"
        @click="$emit('toggle-workflow-monitor')"
      >
        <v-list-item-icon>
          <v-badge
            :content="String(workflowMonitorPendingCount)"
            :value="workflowMonitorPendingCount > 0"
            color="error"
            overlap
          >
            <v-icon>mdi-ticket-outline</v-icon>
          </v-badge>
        </v-list-item-icon>
        <v-list-item-content>
          <v-list-item-title>{{ __('Order Monitor') }}</v-list-item-title>
          <v-list-item-subtitle>
            {{ workflowMonitorExpanded ? __('Open') : __('Show pending orders') }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script>
export default {
  props: {
    drawer: Boolean,
    mini: Boolean,
    activeItem: {
      type: Number,
      default: 0,
    },
    company: {
      type: String,
      default: '',
    },
    companyImg: {
      type: String,
      default: '',
    },
    items: {
      type: Array,
      default: () => [],
    },
    showWorkflowMonitorToggle: Boolean,
    workflowMonitorPendingCount: {
      type: Number,
      default: 0,
    },
    workflowMonitorExpanded: Boolean,
  },
  computed: {
    drawerModel: {
      get() {
        return this.drawer;
      },
      set(value) {
        this.$emit('update-drawer', value);
      },
    },
    miniModel: {
      get() {
        return this.mini;
      },
      set(value) {
        this.$emit('update-mini', value);
      },
    },
    activeItemModel: {
      get() {
        return this.activeItem;
      },
      set(value) {
        this.$emit('update-active-item', value);
      },
    },
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
