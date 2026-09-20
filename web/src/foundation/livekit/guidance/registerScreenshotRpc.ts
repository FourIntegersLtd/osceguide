import type { LocalParticipant } from "livekit-client";
import html2canvas from "html2canvas";
import {
  RPC_METHOD_SCREENSHOT_CHUNKED,
  DATA_TYPE_SCREENSHOT_CHUNK,
  screenshotChunkedRpcRequestSchema,
  screenshotChunkedRpcResponseSchema,
} from "./contracts";
export type RegisterScreenshotRpcOptions = {
  /** Element to capture; default document.body. Prefer viewport-sized capture. */ captureRoot?:
    | HTMLElement
    | (() => HTMLElement);
  ignoreElements?: (element: Element) => boolean;
};
function resolveDomCaptureRoot(
  options?: RegisterScreenshotRpcOptions,
): HTMLElement {
  const configuredCaptureRoot = options?.captureRoot;
  if (typeof configuredCaptureRoot === "function")
    return configuredCaptureRoot();
  return configuredCaptureRoot ?? document.body;
} /** Max base64 characters per data-channel message (wire field `d`). */
const SCREENSHOT_BASE64_CHUNK_CHAR_LENGTH = 12_000;
/** Downscale capture so the agent image stays readable but not enormous. */
const MAX_CAPTURE_IMAGE_WIDTH_PX = 1200; /** * Registers LiveKit RPC `getScreenshotForGuidanceV2` On the local participant. * * Protocol: * 1. Agent sends RPC with { screenshotId } in the payload. * 2. Browser captures a full-quality screenshot (no compression loop needed. * there is no payload size constraint on the data channel). * 3. Browser streams base64 chunks via publishData({ type:"sc_chunk", … }). * 4. Browser returns only dimension metadata via the RPC response. * 5. Agent reassembles chunks → full-quality image → sends to Claude. * * Coordinate contract: image is at most MAX_CAPTURE_IMAGE_WIDTH_PX wide (aspect preserved). * captureWidth × captureHeight in the RPC response reflect the actual image dimensions. * Agent maps Claude coords: x_vp = x * viewportWidth / captureWidth (same for y). */
export function registerScreenshotRpc(
  localParticipant: LocalParticipant,
  options?: RegisterScreenshotRpcOptions,
): void {
  localParticipant.registerRpcMethod(
    RPC_METHOD_SCREENSHOT_CHUNKED,
    async (rpcInvocation) => {
      const { screenshotId } = screenshotChunkedRpcRequestSchema.parse(
        JSON.parse(rpcInvocation.payload || "{}"),
      );
      const domRootToRasterize = resolveDomCaptureRoot(options);
      const viewportWidthCss = window.innerWidth;
      const viewportHeightCss = window.innerHeight;
      const fullViewportCanvas = await html2canvas(domRootToRasterize, {
        width: viewportWidthCss,
        height: viewportHeightCss,
        windowWidth: viewportWidthCss,
        windowHeight: viewportHeightCss,
        scrollX: -window.scrollX,
        scrollY: -window.scrollY,
        scale: 1,
        useCORS: true,
        logging: false,
        ignoreElements: options?.ignoreElements,
        backgroundColor: "#ffffff",
      });
      const downscaleFactor = Math.min(
        1,
        MAX_CAPTURE_IMAGE_WIDTH_PX / fullViewportCanvas.width,
      );
      const captureWidthPx = Math.round(
        fullViewportCanvas.width * downscaleFactor,
      );
      const captureHeightPx = Math.round(
        fullViewportCanvas.height * downscaleFactor,
      );
      const scaledCanvas = document.createElement("canvas");
      scaledCanvas.width = captureWidthPx;
      scaledCanvas.height = captureHeightPx;
      const scaledCanvasContext = scaledCanvas.getContext("2d");
      if (!scaledCanvasContext) throw new Error("2d context unavailable");
      scaledCanvasContext.drawImage(
        fullViewportCanvas,
        0,
        0,
        captureWidthPx,
        captureHeightPx,
      );
      const jpegDataUrl = scaledCanvas.toDataURL("image/jpeg", 0.82);
      const fullImageBase64 = jpegDataUrl.includes(",")
        ? (jpegDataUrl.split(",")[1] ?? "")
        : jpegDataUrl;
      const totalChunkCount = Math.ceil(
        fullImageBase64.length / SCREENSHOT_BASE64_CHUNK_CHAR_LENGTH,
      );
      for (let chunkIndex = 0; chunkIndex < totalChunkCount; chunkIndex++) {
        const base64Fragment = fullImageBase64.slice(
          chunkIndex * SCREENSHOT_BASE64_CHUNK_CHAR_LENGTH,
          (chunkIndex + 1) * SCREENSHOT_BASE64_CHUNK_CHAR_LENGTH,
        );
        const dataChannelPayloadJson = JSON.stringify({
          type: DATA_TYPE_SCREENSHOT_CHUNK,
          id: screenshotId,
          i: chunkIndex,
          n: totalChunkCount,
          d: base64Fragment,
        });
        await localParticipant.publishData(
          new TextEncoder().encode(dataChannelPayloadJson),
          { reliable: true },
        );
      }
      const rpcResponseMetadata = screenshotChunkedRpcResponseSchema.parse({
        totalChunks: totalChunkCount,
        viewportWidth: viewportWidthCss,
        viewportHeight: viewportHeightCss,
        captureWidth: captureWidthPx,
        captureHeight: captureHeightPx,
        mediaType: "image/jpeg",
      });
      return JSON.stringify(rpcResponseMetadata);
    },
  );
}
