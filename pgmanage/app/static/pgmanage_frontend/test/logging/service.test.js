import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import axios from "axios";
import * as logging_service from "@src/logging/service";
import { requestHistory } from "@src/logging/service";
import { showAlertText, showToast } from "@src/notification_control";

Date.now = vi.fn(() => new Date("2024-08-05T12:33:37.000Z"));

vi.mock("@src/notification_control", () => ({
  showAlertText: vi.fn(),
  showToast: vi.fn(),
}));

describe("requestHistoryQueue", () => {
  it("should initialize with correct size", () => {
    const queue = new logging_service.requestHistoryQueue(3);
    expect(queue.size).toBe(3);
  });

  it("should throw an error if size is not a positive number", () => {
    expect(() => new logging_service.requestHistoryQueue(0)).toThrow(
      "Size must be a positive number"
    );
  });

  it("should enqueue and dequeue requests", () => {
    const queue = new logging_service.requestHistoryQueue(2);
    queue.enqueue("request 1");
    queue.enqueue("request 2");
    expect(queue.getLength()).toBe(2);
    queue.enqueue("request 3");
    expect(queue.getLength()).toBe(2);
    expect(queue.getData()).toEqual(["request 3", "request 2"]);
    queue.dequeue();
    expect(queue.getLength()).toBe(1);
  });

  it("should return true when the queue is empty", () => {
    const queue = new logging_service.requestHistoryQueue(2);
    expect(queue.isEmpty()).toBeTruthy();
  });
});

describe("vueHooks", () => {
  const logger = { error: vi.fn() };
  const Vue = { config: {} };
  const store = { $onAction: vi.fn() };

  it("should throw an error if logger is not provided", () => {
    expect(() => logging_service.vueHooks(null, Vue)).toThrow(
      "vueHooks must be initiate with logLevel as first argument"
    );
  });

  it("should throw an error if Vue instance is not provided", () => {
    expect(() => logging_service.vueHooks(logger, null)).toThrow(
      "vueHooks must be initiate with Vue instance as second argument"
    );
  });

  it("should set the Vue global error handler", () => {
    logging_service.vueHooks(logger, Vue);
    expect(Vue.config.errorHandler).toBeDefined();
    const error = new Error("Test error");
    Vue.config.errorHandler(error);
    expect(logger.error).toHaveBeenCalledWith(`Vue Global ${error.stack}`);
  });

  it("should set up store action error hooks if stores are provided", () => {
    logging_service.vueHooks(logger, Vue, [store]);
    expect(store.$onAction).toHaveBeenCalled();
  });
});

describe("axiosHooks", () => {
  const logger = { error: vi.fn() };
  const response = { config: { method: "get", url: "/test" }, data: {} };
  const error = {
    config: { method: "get", url: "/test" },
    response: { status: 401, data: { data: "Unauthorized" } },
    message: "Network Error",
    code: "ERR_NETWORK",
    stack: "Error stack trace",
  };

  let interceptors = {};
  axios.isAxiosError = vi.fn(() => true);

  beforeEach(() => {
    interceptors = {
      response: { use: vi.fn((resolve, reject) => ({ resolve, reject })) },
    };
    axios.interceptors = interceptors;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should save request logs and return response on success", async () => {
    const requestHistoryQueueMock = vi.spyOn(requestHistory, "enqueue");
    logging_service.axiosHooks(logger, axios);

    const onSuccess = interceptors.response.use.mock.calls[0][0];
    const result = await onSuccess(response);
    expect(result).toEqual(response);
    expect(requestHistoryQueueMock).toHaveBeenCalledOnce();
  });

  it("should show a toast when the response has a warning", async () => {
    logging_service.axiosHooks(logger, axios);

    const onSuccess = interceptors.response.use.mock.calls[0][0];
    await onSuccess({ ...response, data: { warning: "Mind the gap." } });
    expect(showToast).toHaveBeenCalledWith("info", "Mind the gap.");
  });

  it("should not show a toast when the response has no warning", async () => {
    logging_service.axiosHooks(logger, axios);

    const onSuccess = interceptors.response.use.mock.calls[0][0];
    await onSuccess(response);
    expect(showToast).not.toHaveBeenCalled();
  });

  it("should handle error and show alert on 401", async () => {
    logging_service.axiosHooks(logger, axios);
    const onError = interceptors.response.use.mock.calls[0][1];
    try {
      await onError(error);
    } catch (err) {
      expect(showAlertText).toHaveBeenCalledWith(
        "User not authenticated, please reload the page."
      );
    }
  });

  it("should handle network errors and show alert", async () => {
    logging_service.axiosHooks(logger, axios);
    const onError = interceptors.response.use.mock.calls[0][1];
    error.response.status = 500; // Set a different status
    error.code = "ERR_NETWORK";
    try {
      await onError(error);
    } catch (err) {
      expect(showAlertText).toHaveBeenCalledWith(
        `${error.message}. Try reloading the application if the issue persists.`
      );
    }
  });

  it("should log the error and save the request log", async () => {
    const requestHistoryQueueMock = vi.spyOn(requestHistory, "enqueue");

    logging_service.axiosHooks(logger, axios);
    const onError = interceptors.response.use.mock.calls[0][1];
    try {
      await onError(error);
    } catch (err) {
      expect(logger.error).toHaveBeenCalledWith(
        expect.stringContaining("previous 2 requests")
      );
      expect(requestHistoryQueueMock).toHaveBeenCalledWith(
        `[8/05/2024 15:33:37] "GET /test"\n\t\tError stack trace\n\t\trequest_data: undefined \n\t\tresponse_data: "Unauthorized"`
      );
    }
  });
});
