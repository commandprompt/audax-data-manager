// stores/modal.js
import { defineStore } from "pinia";

const useMessageModalStore = defineStore("messageModal", {
  state: () => ({
    visible: false,
    message: "",
    messageHtml: "",
    successFunc: () => {},
    cancelFunc: () => {},
    closable: true,
    checkboxes: [],
    okOnly: false,
    hasInput: false,
    inputValue: "",
    inputPlaceholder: "",
  }),
  actions: {
    showModal(
      message,
      successFunc,
      cancelFunc,
      closable = true,
      checkboxes = [],
      okOnly = false
    ) {
      this.message = message;
      this.messageHtml = "";
      this.successFunc = successFunc;
      this.cancelFunc = cancelFunc;
      this.closable = closable;
      this.checkboxes = checkboxes;
      this.okOnly = okOnly;
      this.hasInput = false;
      this.inputValue = "";
      this.inputPlaceholder = "";
      this.visible = true;
    },
    showAlertModal(message, successFunc = null, closable = true) {
      this.showModal(message, successFunc, null, closable, [], true);
    },
    showAlertHtmlModal(messageHtml, successFunc = null, closable = true) {
      this.showModal("", successFunc, null, closable, [], true);
      this.messageHtml = messageHtml;
    },
    showPromptModal(
      message,
      value,
      successFunc,
      cancelFunc = null,
      placeholder = ""
    ) {
      this.showModal(message, successFunc, cancelFunc);
      this.hasInput = true;
      this.inputValue = value;
      this.inputPlaceholder = placeholder;
    },
    hideModal() {
      this.visible = false;
    },
    executeSuccess() {
      if (!!this.successFunc && typeof this.successFunc === "function") {
        this.successFunc(this.inputValue);
      }
      this.hideModal();
    },
    executeCancel() {
      if (!!this.cancelFunc && typeof this.cancelFunc === "function") {
        this.cancelFunc();
      }
      this.hideModal();
    },
    resetModal() {
      this.message = "";
      this.messageHtml = "";
      this.successFunc = () => {};
      this.cancelFunc = () => {};
      this.closable = true;
      this.checkboxes = [];
      this.okOnly = false;
      this.hasInput = false;
      this.inputValue = "";
      this.inputPlaceholder = "";
    },
  },
});

export { useMessageModalStore };
