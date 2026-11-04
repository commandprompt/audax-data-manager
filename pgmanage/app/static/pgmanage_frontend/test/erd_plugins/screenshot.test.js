import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { toPng } from "html-to-image";
import { capture } from "@src/erd_plugins/screenshot";
import { saveBlobAs } from "@src/utils/native_dialog";

vi.mock("html-to-image", () => ({
  toPng: vi.fn(),
}));

vi.mock("@src/utils/native_dialog", () => ({
  saveBlobAs: vi.fn(),
}));

describe("capture", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ blob: async () => new Blob(["png-bytes"]) }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("returns null and never calls toPng when no element is given", async () => {
    const result = await capture(null);

    expect(result).toBeNull();
    expect(toPng).not.toHaveBeenCalled();
  });

  it("captures the given element with the default options", async () => {
    toPng.mockResolvedValueOnce("data:image/png;base64,xyz");
    const el = document.createElement("div");

    await capture(el);

    expect(toPng).toHaveBeenCalledTimes(1);
    const [passedEl, passedOptions] = toPng.mock.calls[0];
    expect(passedEl).toBe(el);
    expect(passedOptions).toMatchObject({
      cacheBust: true,
      pixelRatio: 2,
      filter: expect.any(Function),
    });
  });

  it("lets caller-supplied options override the defaults", async () => {
    toPng.mockResolvedValueOnce("data:image/png;base64,xyz");

    await capture(document.createElement("div"), { pixelRatio: 4 });

    const passedOptions = toPng.mock.calls[0][1];
    expect(passedOptions.pixelRatio).toBe(4);
    expect(passedOptions.cacheBust).toBe(true);
  });

  it("resolves with the data url produced by toPng", async () => {
    toPng.mockResolvedValueOnce("data:image/png;base64,xyz");

    const result = await capture(document.createElement("div"));

    expect(result).toBe("data:image/png;base64,xyz");
  });

  it("filters out the vue-flow background node but keeps everything else", async () => {
    toPng.mockResolvedValueOnce("data:image/png;base64,xyz");

    await capture(document.createElement("div"));

    const { filter } = toPng.mock.calls[0][1];
    const backgroundNode = {
      classList: { contains: (name) => name === "vue-flow__background" },
    };
    const regularNode = { classList: { contains: () => false } };
    const nodeWithoutClassList = {};

    expect(filter(backgroundNode)).toBe(false);
    expect(filter(regularNode)).toBe(true);
    expect(filter(nodeWithoutClassList)).toBe(true);
  });

  it("does not trigger a download unless shouldDownload is set", async () => {
    toPng.mockResolvedValueOnce("data:image/png;base64,xyz");

    await capture(document.createElement("div"));

    expect(saveBlobAs).not.toHaveBeenCalled();
  });

  it("saves a timestamped PNG when shouldDownload is true", async () => {
    vi.spyOn(Date, "now").mockReturnValue(1234567890);
    toPng.mockResolvedValueOnce("data:image/png;base64,xyz");

    await capture(document.createElement("div"), { shouldDownload: true });

    // the save runs in the background, capture() does not wait for it
    await vi.waitFor(() => expect(saveBlobAs).toHaveBeenCalledTimes(1));
    expect(fetch).toHaveBeenCalledWith("data:image/png;base64,xyz");
    const [blob, fileName] = saveBlobAs.mock.calls[0];
    expect(blob).toBeInstanceOf(Blob);
    expect(fileName).toBe("erd-screenshot-1234567890.png");
  });
});
