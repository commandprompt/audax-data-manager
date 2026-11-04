import { toPng as ElToPng } from "html-to-image";
import { saveBlobAs } from "../utils/native_dialog";
import { handleError } from "../logging/utils";

// starting from html-to-image@1.11.12 there is a background rendering issue
// https://github.com/bubkoo/html-to-image/issues/506

const filter = (node) => {
  const exclusionClasses = ["vue-flow__background"];
  return !exclusionClasses.some((classname) =>
    node.classList?.contains(classname),
  );
};

async function download(dataUrl, fileName) {
  const blob = await (await fetch(dataUrl)).blob();
  await saveBlobAs(blob, `${fileName}.png`);
}

async function capture(el, options = {}) {
  if (!el) {
    return null;
  }

  const fileName = `erd-screenshot-${Date.now()}`;

  const dataUrl = await ElToPng(el, {
    cacheBust: true,
    pixelRatio: 2,
    filter: filter,
    ...options,
  });

  if (options.shouldDownload && fileName !== "") {
    // Not awaited: the busy state ends once the image is rendered, as it always did.
    // The save dialog is modal, so nothing else can start while it is open.
    download(dataUrl, fileName).catch((error) => handleError(error));
  }

  return dataUrl;
}

export { capture };
