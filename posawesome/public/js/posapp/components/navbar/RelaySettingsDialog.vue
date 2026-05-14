<template>
  <v-dialog v-if="enabled" :value="value" max-width="520" @input="$emit('input', $event)">
    <v-card>
      <v-card-title class="text-subtitle-1">
        {{ __('Edge Relay Settings') }}
      </v-card-title>
      <v-card-text>
        <v-text-field
          :value="form.relay_url"
          :label="__('Relay URL')"
          dense
          outlined
          hide-details="auto"
          class="mb-3"
          placeholder="http://192.168.1.9:8787"
          @input="updateForm('relay_url', $event)"
        ></v-text-field>
        <v-select
          :value="form.connectivity_mode"
          :items="modes"
          :label="__('Connectivity Mode')"
          dense
          outlined
          hide-details="auto"
          class="mb-3"
          @input="updateForm('connectivity_mode', $event)"
        ></v-select>
        <v-text-field
          :value="form.client_key"
          :label="__('Relay Client Key')"
          dense
          outlined
          hide-details="auto"
          type="password"
          autocomplete="off"
          @input="updateForm('client_key', $event)"
        ></v-text-field>
      </v-card-text>
      <v-card-actions>
        <v-btn text color="error" @click="$emit('clear')">
          {{ __('Clear') }}
        </v-btn>
        <v-spacer></v-spacer>
        <v-btn text @click="$emit('input', false)">
          {{ __('Cancel') }}
        </v-btn>
        <v-btn color="primary" @click="$emit('save')">
          {{ __('Save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
export default {
  props: {
    value: Boolean,
    enabled: Boolean,
    form: {
      type: Object,
      default: () => ({}),
    },
    modes: {
      type: Array,
      default: () => [],
    },
  },
  methods: {
    updateForm(field, value) {
      this.$emit('update-form', {
        ...this.form,
        [field]: value,
      });
    },
  },
};
</script>
