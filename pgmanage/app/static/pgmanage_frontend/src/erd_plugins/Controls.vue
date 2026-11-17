<template>
  <div class="position-relative">
    <div
      class="floating-toolbar floating-toolbar--filled floating-toolbar--right-top"
    >
      <span class="floating-toolbar__content">
        <template v-if="schemas.length">
          <div class="dropdown">
            <button
              type="button"
              class="btn btn-icon-secondary"
              title="Schemas"
              data-bs-toggle="dropdown"
              data-bs-auto-close="outside"
              data-bs-popper-config='{"strategy": "fixed"}'
              aria-expanded="false"
            >
              <i class="fa-solid fa-layer-group"></i>
            </button>
            <div class="dropdown-menu dropdown-menu-end erd-schemas">
              <div class="d-flex justify-content-between px-2">
                <button
                  type="button"
                  class="btn btn-link btn-sm"
                  :disabled="loading"
                  @click="$emit('change-schemas', schemas.map((s) => s.name_raw))"
                >
                  Select all
                </button>
                <button
                  type="button"
                  class="btn btn-link btn-sm"
                  :disabled="loading"
                  @click="$emit('change-schemas', [])"
                >
                  Clear
                </button>
              </div>
              <div class="erd-schemas__list">
                <label
                  v-for="schema in schemas"
                  :key="schema.name_raw"
                  class="dropdown-item"
                >
                  <input
                    class="form-check-input me-1"
                    type="checkbox"
                    :checked="selectedSchemas.includes(schema.name_raw)"
                    :disabled="loading"
                    @change="toggleSchema(schema.name_raw, $event.target.checked)"
                  />
                  {{ schema.name }}
                </label>
              </div>
            </div>
          </div>
          <span class="divider"></span>
        </template>
        <button
          class="btn btn-icon-secondary"
          title="Download a screenshot"
          :disabled="capturingScreenshot"
          @click="$emit('screenshot')"
        >
          <i
            v-if="capturingScreenshot"
            class="fa-solid fa-spinner fa-spin"
            role="status"
          >
            <span class="sr-only">Capturing screenshot...</span>
          </i>
          <i v-else class="fa-solid fa-camera"></i>
        </button>
        <span class="divider"></span>
        <button
          class="btn btn-icon-secondary"
          @click="$emit('reset')"
          title="Reset to default"
        >
          <i class="fa-solid fa-rotate-left"></i>
        </button>
        <button
          class="btn btn-icon-secondary"
          title="Refresh"
          :disabled="loading"
          @click="$emit('refresh')"
        >
          <i
            v-if="loading"
            class="fa-solid fa-spinner fa-spin"
            role="status"
          >
            <span class="sr-only">Loading...</span>
          </i>
          <i v-else class="fa-solid fa-arrows-rotate"></i>
        </button>

        <span class="divider"></span>

        <!-- Zoom Out -->
        <button
          class="btn btn-icon-secondary"
          @click="$emit('zoom-out')"
          title="Zoom Out"
        >
          <i class="fas fa-search-minus"></i>
        </button>
        <!-- Zoom In -->
        <button
          class="btn btn-icon-secondary"
          @click="$emit('zoom-in')"
          title="Zoom In"
        >
          <i class="fas fa-search-plus"></i>
        </button>

        <button
          type="button"
          class="btn btn-icon-secondary"
          title="Fullscreen"
          @click="$emit('toggle-fullscreen')"
        >
          <i :class="inFullscreen ? 'fas fa-compress' : 'fas fa-expand'"></i>
        </button>
      </span>
    </div>
  </div>
</template>

<script>
export default {
  name: "Controls",
  props: {
    inFullscreen: {
      type: Boolean,
      default: false,
    },
    capturingScreenshot: {
      type: Boolean,
      default: false,
    },
    schemas: {
      type: Array,
      default: () => [],
    },
    selectedSchemas: {
      type: Array,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["screenshot", "reset", "refresh", "zoom-in", "zoom-out", "toggle-fullscreen", "change-schemas"],
  methods: {
    toggleSchema(schema, checked) {
      const selected = this.selectedSchemas.filter((s) => s !== schema);
      if (checked) {
        selected.push(schema);
      }
      this.$emit("change-schemas", selected);
    },
  },
};
</script>

<style scoped>
.erd-schemas__list {
  max-height: 300px;
  overflow-y: auto;
}
</style>
