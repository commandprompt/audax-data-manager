import { setActivePinia, createPinia } from "pinia";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { useMessageModalStore } from "@src/stores/message_modal";

describe("messageModal store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("initializes with default state", () => {
    const store = useMessageModalStore();
    expect(store.visible).toBe(false);
    expect(store.message).toBe("");
    expect(store.successFunc).toBeInstanceOf(Function);
    expect(store.cancelFunc).toBeInstanceOf(Function);
    expect(store.closable).toBe(true);
    expect(store.checkboxes).toEqual([]);
    expect(store.okOnly).toBe(false);
    expect(store.messageHtml).toBe("");
    expect(store.hasInput).toBe(false);
    expect(store.inputValue).toBe("");
    expect(store.inputPlaceholder).toBe("");
  });

  it("shows modal and sets the correct state", () => {
    const store = useMessageModalStore();
    const message = "Test message";
    const successFunc = vi.fn();
    const cancelFunc = vi.fn();
    const checkboxes = ["option1", "option2"];

    store.showModal(message, successFunc, cancelFunc, false, checkboxes);

    expect(store.message).toBe(message);
    expect(store.successFunc).toBe(successFunc);
    expect(store.cancelFunc).toBe(cancelFunc);
    expect(store.closable).toBe(false);
    expect(store.checkboxes).toEqual(checkboxes);
    expect(store.okOnly).toBe(false);
    expect(store.visible).toBe(true);
  });

  it("shows an alert modal with okOnly set and no cancel function", () => {
    const store = useMessageModalStore();
    const successFunc = vi.fn();

    store.showAlertModal("Test message", successFunc);

    expect(store.message).toBe("Test message");
    expect(store.successFunc).toBe(successFunc);
    expect(store.cancelFunc).toBe(null);
    expect(store.closable).toBe(true);
    expect(store.checkboxes).toEqual([]);
    expect(store.okOnly).toBe(true);
    expect(store.visible).toBe(true);
  });

  it("shows an html alert modal and keeps the plain message empty", () => {
    const store = useMessageModalStore();
    const successFunc = vi.fn();

    store.showAlertHtmlModal("<b>Test</b> message", successFunc);

    expect(store.messageHtml).toBe("<b>Test</b> message");
    expect(store.message).toBe("");
    expect(store.successFunc).toBe(successFunc);
    expect(store.cancelFunc).toBe(null);
    expect(store.okOnly).toBe(true);
    expect(store.visible).toBe(true);
  });

  it("clears messageHtml when a plain message modal is shown", () => {
    const store = useMessageModalStore();

    store.showAlertHtmlModal("<b>Test</b> message");
    store.showAlertModal("Plain message");

    expect(store.messageHtml).toBe("");
    expect(store.message).toBe("Plain message");
  });

  it("resets messageHtml once the modal has finished hiding", () => {
    const store = useMessageModalStore();

    store.showAlertHtmlModal("<b>Test</b> message");
    store.hideModal();
    expect(store.messageHtml).toBe("<b>Test</b> message");

    store.resetModal();
    expect(store.messageHtml).toBe("");
  });

  it("keeps okOnly set while the modal hides so the buttons do not flicker", () => {
    const store = useMessageModalStore();

    store.showAlertModal("Test message");
    store.hideModal();

    expect(store.visible).toBe(false);
    expect(store.okOnly).toBe(true);

    store.resetModal();
    expect(store.okOnly).toBe(false);
  });

  it("hides modal and resets the state", () => {
    const store = useMessageModalStore();

    store.showModal("Test message", vi.fn(), vi.fn(), false, ["option1"]);
    store.hideModal();
    store.resetModal();

    expect(store.visible).toBe(false);
    expect(store.message).toBe("");
    expect(store.successFunc).toBeInstanceOf(Function);
    expect(store.cancelFunc).toBeInstanceOf(Function);
    expect(store.closable).toBe(true);
    expect(store.checkboxes).toEqual([]);
  });

  it("shows a prompt modal with an input and Ok/Cancel labels", () => {
    const store = useMessageModalStore();
    const successFunc = vi.fn();

    store.showPromptModal("Rename", "My Tab", successFunc, null, "Tab name");

    expect(store.message).toBe("Rename");
    expect(store.hasInput).toBe(true);
    expect(store.inputValue).toBe("My Tab");
    expect(store.inputPlaceholder).toBe("Tab name");
    expect(store.visible).toBe(true);
  });

  it("passes the input value to the success function", () => {
    const store = useMessageModalStore();
    const successFunc = vi.fn();

    store.showPromptModal("", "My Tab", successFunc);
    store.inputValue = "Renamed Tab";
    store.executeSuccess();

    expect(successFunc).toHaveBeenCalledWith("Renamed Tab");
  });

  it("clears the input when a plain modal is shown after a prompt", () => {
    const store = useMessageModalStore();

    store.showPromptModal("", "My Tab", vi.fn());
    store.showModal("Plain message", vi.fn(), vi.fn());

    expect(store.hasInput).toBe(false);
    expect(store.inputValue).toBe("");
  });

  it("resets the input once the modal has finished hiding", () => {
    const store = useMessageModalStore();

    store.showPromptModal("", "My Tab", vi.fn(), null, "Tab name");
    store.hideModal();
    store.resetModal();

    expect(store.hasInput).toBe(false);
    expect(store.inputValue).toBe("");
    expect(store.inputPlaceholder).toBe("");
  });

  it("executes success function and hides modal", () => {
    const store = useMessageModalStore();
    const successFunc = vi.fn();

    store.showModal("Test message", successFunc, vi.fn());
    store.executeSuccess();

    expect(successFunc).toHaveBeenCalled();
    expect(store.visible).toBe(false);
  });

  it("executes cancel function and hides modal", () => {
    const store = useMessageModalStore();
    const cancelFunc = vi.fn();

    store.showModal("Test message", vi.fn(), cancelFunc);
    store.executeCancel();

    expect(cancelFunc).toHaveBeenCalled();
    expect(store.visible).toBe(false);
  });
});
