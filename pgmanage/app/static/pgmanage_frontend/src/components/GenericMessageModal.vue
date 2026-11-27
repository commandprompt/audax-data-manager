<template>
  <Teleport to="body">
    <div
      class="modal fade"
      id="generic_modal_message"
      tabindex="-1"
      role="dialog"
      aria-hidden="true"
    >
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header align-items-center">
            <button
              v-if="store.closable"
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
              @click="store.hideModal"
            ></button>
          </div>
          <div
            id="generic_modal_message_content"
            class="modal-body"
            style="word-break: break-word"
          >
            <span v-if="safeMessageHtml" v-html="safeMessageHtml"></span>
            <span v-else style="white-space: pre-line">{{ textMessage }}</span>
            <input
              v-if="store.hasInput"
              ref="messageInput"
              id="generic_modal_message_input"
              type="text"
              class="form-control"
              v-model="store.inputValue"
              :placeholder="store.inputPlaceholder"
              @keyup.enter="store.executeSuccess"
            />
            <div
              v-for="(checkbox, index) in store.checkboxes"
              :key="index"
              class="form-check form-switch"
            >
              <input
                class="form-check-input"
                type="checkbox"
                :id="`generic_modal_message_content_${index}`"
                v-model="checkbox.checked"
              />
              <label
                class="form-check-label"
                :for="`generic_modal_message_content_${index}`"
              >
                {{ checkbox.label }}
              </label>
            </div>
          </div>
          <div class="modal-footer">
            <button
              id="generic_modal_message_yes"
              type="button"
              class="btn"
              :class="confirmButton.class"
              data-bs-dismiss="modal"
              @click="store.executeSuccess"
            >
              {{ confirmButton.label }}
            </button>
            <button
              v-if="!store.okOnly"
              id="generic_modal_message_no"
              type="button"
              class="btn"
              :class="cancelButton.class"
              data-bs-dismiss="modal"
              @click="store.executeCancel"
            >
              {{ cancelButton.label }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { messageModalStore } from "../stores/stores_initializer";
import { isSafeHtml } from "../utils";
import { Modal } from "bootstrap";

export default {
  data() {
    return {
      modalInstance: null,
    };
  },
  computed: {
    store() {
      return messageModalStore;
    },
    safeMessageHtml() {
      const html = this.store.messageHtml;
      return html && isSafeHtml(html) ? html : "";
    },
    textMessage() {
      return this.store.messageHtml || this.store.message;
    },
    confirmButton() {
      if (this.store.okOnly || this.store.hasInput)
        return { label: "Ok", class: "btn-success" };
      return { label: "Yes", class: "btn-primary" };
    },
    cancelButton() {
      if (this.store.hasInput)
        return { label: "Cancel", class: "btn-secondary" };
      return { label: "No", class: "btn-danger" };
    },
  },
  mounted() {
    messageModalStore.$onAction((action) => {
      if (action.name === "showModal") {
        this.modalInstance = Modal.getOrCreateInstance(
          "#generic_modal_message",
          {
            backdrop: "static",
          }
        );
        this.modalInstance.show();
      }
      if (action.name === "hideModal") {
        this.modalInstance.hide();
      }
    });
    let messageModalEl = document.getElementById("generic_modal_message");

    messageModalEl.addEventListener("hidden.bs.modal", () => {
      if (this.store.visible) return;
      this.store.resetModal();
    });

    messageModalEl.addEventListener("shown.bs.modal", () => {
      if (!this.store.hasInput) return;
      this.$refs.messageInput?.focus();
      this.$refs.messageInput?.select();
    });

    messageModalEl.addEventListener("hide.bs.modal", (event) => {
      const activeEl = document.activeElement;

      const isConfirmButton =
        activeEl?.id === "generic_modal_message_yes" ||
        activeEl?.id === "generic_modal_message_no";

      if (!this.store.closable && !isConfirmButton) {
        event.preventDefault();
        return;
      }
    });
  },
};
</script>

<style>
#generic_modal_message {
  z-index: 9999;
}
</style>
