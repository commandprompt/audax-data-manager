import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import GenericMessageModal from "@src/components/GenericMessageModal.vue";
import { useMessageModalStore } from "@src/stores/message_modal";
import { Modal } from "bootstrap";

vi.mock("bootstrap", () => ({
  Modal: {
    getOrCreateInstance: vi.fn(() => ({
      show: vi.fn(),
      hide: vi.fn(),
    })),
  },
}));

describe("GenericMessageModal.vue", () => {
  let store;

  beforeEach(() => {
    store = useMessageModalStore();
    document.getElementById = vi.fn(() => ({
      addEventListener: vi.fn(),
    }));
  });

  afterEach(() => {
    store.$reset();
  });

  it("renders message and checkboxes from store", async () => {
    store.message = "Test Message";
    store.checkboxes = [
      { label: "Option 1", checked: false },
      { label: "Option 2", checked: true },
    ];

    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    expect(wrapper.text()).toContain("Test Message");
    const checkboxInputs = wrapper.findAll('input[type="checkbox"]');
    expect(checkboxInputs.length).toBe(2);
    expect(checkboxInputs[0].element.checked).toBe(false);
    expect(checkboxInputs[1].element.checked).toBe(true);
  });

  it("calls store methods on button clicks", async () => {
    store.executeSuccess = vi.fn();
    store.executeCancel = vi.fn();
    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    await wrapper.find("#generic_modal_message_yes").trigger("click");
    expect(store.executeSuccess).toHaveBeenCalled();

    await wrapper.find("#generic_modal_message_no").trigger("click");
    expect(store.executeCancel).toHaveBeenCalled();
  });

  it("renders messageHtml as markup when the tags are allowed", () => {
    store.messageHtml = "Close these first:<br><b>Edit Data</b>";

    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    const content = wrapper.find("#generic_modal_message_content");
    expect(content.find("b").text()).toBe("Edit Data");
    expect(content.find("br").exists()).toBe(true);
  });

  it("renders messageHtml as text when the tags are not allowed", () => {
    store.messageHtml = "<script>alert(1)</script>";

    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    const content = wrapper.find("#generic_modal_message_content");
    expect(content.find("script").exists()).toBe(false);
    expect(content.text()).toContain("<script>alert(1)</script>");
  });

  it("shows Yes and No buttons when okOnly is false", () => {
    store.okOnly = false;
    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    expect(wrapper.find("#generic_modal_message_yes").text()).toBe("Yes");
    expect(wrapper.find("#generic_modal_message_no").exists()).toBe(true);
  });

  it("shows a single Ok button when okOnly is true", () => {
    store.okOnly = true;
    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    expect(wrapper.find("#generic_modal_message_yes").text()).toBe("Ok");
    expect(wrapper.find("#generic_modal_message_no").exists()).toBe(false);
  });

  it("renders an input and binds it to the store when hasInput is set", async () => {
    store.hasInput = true;
    store.inputValue = "My Tab";
    store.inputPlaceholder = "Snippet Name";

    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    const input = wrapper.find("#generic_modal_message_input");
    expect(input.element.value).toBe("My Tab");
    expect(input.attributes("placeholder")).toBe("Snippet Name");

    await input.setValue("Renamed Tab");
    expect(store.inputValue).toBe("Renamed Tab");
  });

  it("does not render an input when hasInput is false", () => {
    store.hasInput = false;

    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    expect(wrapper.find("#generic_modal_message_input").exists()).toBe(false);
  });

  it("confirms when Enter is pressed in the input", async () => {
    store.hasInput = true;
    store.executeSuccess = vi.fn();

    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    await wrapper.find("#generic_modal_message_input").trigger("keyup.enter");
    expect(store.executeSuccess).toHaveBeenCalled();
  });

  it("focuses and selects the input once the modal is shown", () => {
    const listeners = {};
    document.getElementById = vi.fn(() => ({
      addEventListener: (name, handler) => {
        listeners[name] = handler;
      },
    }));
    store.hasInput = true;
    store.inputValue = "My Tab";

    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    const input = wrapper.find("#generic_modal_message_input").element;
    const focusSpy = vi.spyOn(input, "focus");
    const selectSpy = vi.spyOn(input, "select");

    listeners["shown.bs.modal"]();

    expect(focusSpy).toHaveBeenCalled();
    expect(selectSpy).toHaveBeenCalled();
  });

  it.each([
    ["a confirm", {}, ["Yes", "btn-primary"], ["No", "btn-danger"]],
    ["an alert", { okOnly: true }, ["Ok", "btn-success"], null],
    [
      "a prompt",
      { hasInput: true },
      ["Ok", "btn-success"],
      ["Cancel", "btn-secondary"],
    ],
  ])(
    "labels and colors the buttons for %s",
    (_name, state, confirm, cancel) => {
      Object.assign(store, state);

      const wrapper = mount(GenericMessageModal, {
        global: {
          stubs: {
            teleport: true,
          },
        },
      });

      const confirmButton = wrapper.find("#generic_modal_message_yes");
      expect(confirmButton.text()).toBe(confirm[0]);
      expect(confirmButton.classes()).toContain(confirm[1]);

      const cancelButton = wrapper.find("#generic_modal_message_no");
      if (!cancel) {
        expect(cancelButton.exists()).toBe(false);
        return;
      }
      expect(cancelButton.text()).toBe(cancel[0]);
      expect(cancelButton.classes()).toContain(cancel[1]);
    }
  );

  it("keeps the Ok button alone while the modal is hiding", async () => {
    const listeners = {};
    document.getElementById = vi.fn(() => ({
      addEventListener: (name, handler) => {
        listeners[name] = handler;
      },
    }));

    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    store.showAlertModal("Test message");
    await wrapper.vm.$nextTick();
    expect(wrapper.find("#generic_modal_message_no").exists()).toBe(false);

    // hideModal only starts the fade; the footer must not change until it ends
    store.hideModal();
    await wrapper.vm.$nextTick();
    expect(wrapper.find("#generic_modal_message_yes").text()).toBe("Ok");
    expect(wrapper.find("#generic_modal_message_no").exists()).toBe(false);

    listeners["hidden.bs.modal"]();
    expect(store.okOnly).toBe(false);
  });

  it("does not reset a modal that was opened while the old one was hiding", () => {
    const listeners = {};
    document.getElementById = vi.fn(() => ({
      addEventListener: (name, handler) => {
        listeners[name] = handler;
      },
    }));

    mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    store.showAlertModal("First message");
    store.hideModal();
    store.showModal("Second message", vi.fn(), vi.fn());

    listeners["hidden.bs.modal"]();

    expect(store.message).toBe("Second message");
    expect(store.visible).toBe(true);
  });

  it("conditionally shows close button when closable is true", () => {
    store.closable = true;
    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });
    const closeBtn = wrapper.find("button.btn-close");
    expect(closeBtn.exists()).toBe(true);
  });

  it("hides close button when closable is false", () => {
    store.closable = false;
    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });
    const closeBtn = wrapper.find("button.btn-close");
    expect(closeBtn.exists()).toBe(false);
  });

  it("calls store.hideModal when close button is clicked", async () => {
    const hideModalSpy = vi.spyOn(store, "hideModal");
    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });
    store.showModal("test message");
    await wrapper.find("button.btn-close").trigger("click");
    expect(hideModalSpy).toHaveBeenCalled();
  });

  it("shows modal on store.showModal and hides on store.hideModal", async () => {
    const wrapper = mount(GenericMessageModal, {
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    store.showModal("test message");

    expect(Modal.getOrCreateInstance).toHaveBeenCalled();
    expect(wrapper.vm.modalInstance.show).toHaveBeenCalled();

    store.hideModal();

    expect(wrapper.vm.modalInstance.hide).toHaveBeenCalled();
  });
});
