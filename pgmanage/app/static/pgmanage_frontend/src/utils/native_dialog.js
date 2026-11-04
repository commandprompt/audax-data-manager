import { showToast } from "../notification_control";

const mimeByExtension = {
  sql: "application/sql",
  tar: "application/x-tar",
};

function fileType(path) {
  const ext = path.split(".").pop().toLowerCase();
  return mimeByExtension[ext] ?? "";
}

// Resolves to { path, type } or null when the dialog is cancelled.
// kind: "select_file" | "select_folder" | "create_file"
export function pickNativePath(kind, title) {
  if (window.__TAURI__?.core) {
    return window.__TAURI__.core
      .invoke("pick_path", { kind, title: title ?? null })
      .then((path) => (path ? { path, type: fileType(path) } : null));
  }

  // legacy NW.js file input
  return new Promise((resolve) => {
    const inputEl = document.createElement("input");
    inputEl.setAttribute("type", "file");
    if (kind === "select_folder") {
      inputEl.setAttribute("nwdirectory", "");
    } else if (kind === "create_file") {
      inputEl.setAttribute("nwsaveas", "");
    }
    inputEl.onchange = (e) => resolve(e.target.files[0] ?? null);
    inputEl.dispatchEvent(new MouseEvent("click"));
  });
}

// Saves a Blob/File the page generated (snippets, query files, images).
// Desktop shell: the native save dialog is opened by the host and the file is written there.
// Browser / NW.js: a normal download. Resolves to the saved path in the shell, otherwise undefined.
export async function saveBlobAs(blob, fileName) {
  if (!window.__TAURI__?.core) {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = fileName;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 60000);
    return;
  }

  const bytes = new Uint8Array(await blob.arrayBuffer());
  try {
    return await window.__TAURI__.core.invoke("save_file", bytes, {
      headers: { "x-file-name": encodeURIComponent(fileName) },
    });
  } catch (error) {
    showToast("error", `Could not save the file: ${error}`);
  }
}

