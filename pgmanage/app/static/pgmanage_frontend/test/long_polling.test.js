import { beforeEach, describe, expect, it, vi } from "vitest";
import axios from "axios";
import { flushPromises } from "@vue/test-utils";
import { handleError } from "@src/logging/utils";

vi.mock("short-unique-id", () => {
  return {
    default: vi.fn().mockImplementation(function () {
      return { seq: vi.fn(() => "ABCD") };
    }),
  };
});

vi.mock("@src/logging/utils", () => ({
  handleError: vi.fn(),
}));

describe("long_polling.js", () => {
  let createContext, removeContext, createRequest, SetAcked;

  beforeEach(async () => {
    // long_polling.js keeps polling state (polling_busy, request_map) in
    // module-level variables, so each test needs a fresh module instance
    // to avoid leaking state (e.g. startup flag) into the next test.
    vi.resetModules();
    ({ createContext, removeContext, createRequest, SetAcked } = await import(
      "@src/long_polling"
    ));
  });

  it("createContext should assign generated code when context.code is missing", () => {
    const context = { context: { some: "value" } };

    const result = createContext(context);

    expect(result.code).toBe("ABCD");
  });

  it("createContext should preserve provided code", () => {
    const context = { code: "WXYZ", context: { some: "value" } };

    const result = createContext(context);

    expect(result.code).toBe("WXYZ");
  });

  it("SetAcked should mark context as acked", () => {
    const context = { acked: false };

    SetAcked(context);

    expect(context.acked).toBe(true);
  });

  it("removeContext should not throw for existing or missing context", () => {
    const ctx = { context: { x: 1 } };
    const created = createContext(ctx);

    expect(() => removeContext(created.code)).not.toThrow();
    expect(() => removeContext("UNKNOWN")).not.toThrow();
  });

  it("createRequest should create a request with generated context code and start polling", async () => {
    axios.post.mockImplementation((url, payload) => {
      if (url === "/long_polling/") {
        expect(payload).toEqual({ startup: true });
        return Promise.resolve({
          data: {
            returning_rows: [],
          },
        });
      }

      if (url === "/create_request/") {
        return Promise.resolve({});
      }

      return Promise.resolve({});
    });

    const context = { callback: vi.fn() };

    createRequest("test_type", { a: 1 }, context);
    await flushPromises();

    expect(context.code).toBe("ABCD");
    expect(axios.post).toHaveBeenCalledWith("/create_request/", {
      request_type: "test_type",
      context_code: "ABCD",
      data: { a: 1 },
    });
  });

  it("should call handleError when long polling request fails", async () => {
    axios.post.mockImplementation((url) => {
      if (url === "/long_polling/") {
        return Promise.reject(new Error("Polling failed"));
      }

      if (url === "/create_request/") {
        return Promise.resolve({});
      }

      return Promise.resolve({});
    });

    createRequest("test_type", {}, null);
    await flushPromises();

    expect(handleError).toHaveBeenCalled();
  });
});
