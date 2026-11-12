<template>
    <div class="vue-flow__node-table__wrap">
      <div class="vue-flow__node-table__title">
        <p class="clipped-text">{{ title }}</p>
      </div>
    </div>
</template>

<script>
export default {
  name: 'TableNode',

  props: {
    id: {
      type: String,
      required: true,
    },

    data: {
      type: Object,
      required: true,
    },

    selected: {
      type: Boolean,
      default: false,
    },
  },

  computed: {
    title() {
      return this.data.schema ? `${this.data.schema}.${this.data.label}` : this.data.label;
    },
  },
}
</script>
