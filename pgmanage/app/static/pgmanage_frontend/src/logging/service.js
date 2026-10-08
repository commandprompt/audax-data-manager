import moment from "moment";
import { showAlertText, showToast } from "../notification_control";
import axios from "axios";

export class requestHistoryQueue {
  constructor(size) {
    if (typeof size !== "number" || size <= 0) {
      throw new Error("Size must be a positive number");
    }

    this.size = size;
    this.queue = [];
  }

  enqueue(requestLog) {
    if (this.queue.length === this.size) {
      this.dequeue();
    }
    this.queue.unshift(requestLog);
  }

  dequeue() {
    this.queue.pop();
  }

  isEmpty() {
    return this.queue.length === 0;
  }

  getLength() {
    return this.queue.length;
  }

  getData() {
    return this.queue;
  }
}

export const requestHistory = new requestHistoryQueue(2);

export function vueHooks(logger, Vue, stores) {
  if (!logger)
    throw new Error(
      "vueHooks must be initiate with logLevel as first argument"
    );
  if (!Vue)
    throw new Error(
      "vueHooks must be initiate with Vue instance as second argument"
    );

  // Vue Hooks
  Vue.config.errorHandler = (error, vm, info) => {
    logger.error(`Vue Global ${error.stack}`);
  };

  // Hook stores Actions
  if (stores) {
    stores.forEach((store) => {
      store.$onAction(({ onError }) => {
        onError((error) => {
          logger.error(`Pinia ${store.$id}Store ${error.stack}`);
        });
      });
    });
  }
}

export function saveRequestLog(response) {
  let timestamp = moment().format("M/DD/YYYY H:m:s");
  let requestUrl = JSON.stringify(
    `${response.config.method.toUpperCase()} ${response?.config?.url || ""}`
  );
  let requestData = response?.config?.data;
  let errorResponseData = response?.response?.data?.data
    ? response.response.data.data
    : response?.response?.data;
  let successResponseData = response?.data?.data
    ? response.data.data
    : response?.data;

  let responseData = axios.isAxiosError(response)
    ? errorResponseData
    : successResponseData;

  let errorStack = axios.isAxiosError(response)
    ? `\n\t\t${response?.stack}`
    : "";

  let requestLog = `[${timestamp}] ${requestUrl}${errorStack}\n\t\trequest_data: ${requestData} \n\t\tresponse_data: ${JSON.stringify(
    responseData
  )}`;

  requestHistory.enqueue(requestLog);
}
export function axiosHooks(logger, axiosInstance) {
  axiosInstance.interceptors.response.use(
    (response) => {
      if (response.data?.warning) {
        showToast("info", response.data.warning);
      }
      saveRequestLog(response);
      return response;
    },
    (error) => {
      let requestUrl = JSON.stringify(
        `${error.config.method.toUpperCase()} ${error?.config?.url || ""}`
      );
      let errorResponseData = error?.response?.data?.data
        ? error.response.data.data
        : error?.response?.data;

      let previous_data = requestHistory.getData();
      previous_data = previous_data.join("\n\t");
      logger.error(
        `${requestUrl} \n${error.stack} \nrequest_data: ${
          error?.config?.data
        } \nresponse_data: ${JSON.stringify(
          errorResponseData
        )} \nprevious ${requestHistory.getLength()} requests:\n\t${previous_data}`
      );
      if (error.response && error.response.status === 401) {
        showAlertText("User not authenticated, please reload the page.");
      } else if (error.code === "ERR_NETWORK") {
        showAlertText(
          `${error.message}. Try reloading the application if the issue persists.`
        );
      }
      saveRequestLog(error);
      return Promise.reject(error);
    }
  );
}
