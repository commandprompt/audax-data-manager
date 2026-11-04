import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { saveBlobAs, pickNativePath } from "@src/utils/native_dialog";
import { showToast } from "@src/notification_control";

vi.mock("@src/notification_control", () => ({
  showToast: vi.fn(),
}));

describe("native_dialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    delete window.__TAURI__;
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe("saveBlobAs", () => {
    it("falls back to a normal download outside the desktop shell", async () => {
      URL.createObjectURL = vi.fn(() => "blob:test");
      URL.revokeObjectURL = vi.fn();
      const clickSpy = vi
        .spyOn(HTMLAnchorElement.prototype, "click")
        .mockImplementation(function () {
          expect(this.download).toBe("query.sql");
          expect(this.href).toBe("blob:test");
        });

      const result = await saveBlobAs(new Blob(["select 1"]), "query.sql");

      expect(clickSpy).toHaveBeenCalledTimes(1);
      expect(result).toBeUndefined();
    });

    it("sends the bytes and the encoded file name to the shell", async () => {
      const bytes = new TextEncoder().encode("select 1");
      const invoke = vi.fn().mockResolvedValue("/home/user/query.sql");
      window.__TAURI__ = { core: { invoke } };
      const blob = { arrayBuffer: async () => bytes.buffer };

      const result = await saveBlobAs(blob, "my query.sql");

      expect(invoke).toHaveBeenCalledTimes(1);
      const [cmd, payload, options] = invoke.mock.calls[0];
      expect(cmd).toBe("save_file");
      expect(Array.from(payload)).toEqual(Array.from(bytes));
      expect(options).toEqual({
        headers: { "x-file-name": encodeURIComponent("my query.sql") },
      });
      expect(result).toBe("/home/user/query.sql");
    });

    it("resolves to null when the dialog is cancelled", async () => {
      window.__TAURI__ = { core: { invoke: vi.fn().mockResolvedValue(null) } };
      const blob = { arrayBuffer: async () => new ArrayBuffer(1) };

      expect(await saveBlobAs(blob, "a.sql")).toBeNull();
      expect(showToast).not.toHaveBeenCalled();
    });

    it("shows an error toast when the shell fails to save", async () => {
      window.__TAURI__ = {
        core: { invoke: vi.fn().mockRejectedValue("disk full") },
      };
      const blob = { arrayBuffer: async () => new ArrayBuffer(1) };

      await saveBlobAs(blob, "a.sql");

      expect(showToast).toHaveBeenCalledWith(
        "error",
        expect.stringContaining("disk full"),
      );
    });
  });

  describe("pickNativePath", () => {
    it("returns the path and a mime type derived from the extension", async () => {
      const invoke = vi.fn().mockResolvedValue("/tmp/dump.sql");
      window.__TAURI__ = { core: { invoke } };

      const file = await pickNativePath("create_file", "Choose");

      expect(invoke).toHaveBeenCalledWith("pick_path", {
        kind: "create_file",
        title: "Choose",
      });
      expect(file).toEqual({ path: "/tmp/dump.sql", type: "application/sql" });
    });

    it("maps .tar and unknown extensions", async () => {
      const invoke = vi
        .fn()
        .mockResolvedValueOnce("/tmp/a.tar")
        .mockResolvedValueOnce("/tmp/a.custom");
      window.__TAURI__ = { core: { invoke } };

      expect((await pickNativePath("select_file")).type).toBe("application/x-tar");
      expect((await pickNativePath("select_file")).type).toBe("");
    });

    it("returns null when the dialog is cancelled", async () => {
      window.__TAURI__ = { core: { invoke: vi.fn().mockResolvedValue(null) } };

      expect(await pickNativePath("select_folder")).toBeNull();
    });
  });
});
