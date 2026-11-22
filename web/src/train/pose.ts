// The MediaPipe pose model, running in the browser. The video never leaves the
// device: only the landmarks (33 points) come out, and only reps get sent.
//
// MediaPipe is loaded on demand (it's large), from files the site serves
// itself (public/mediapipe, copied by scripts/copy-mediapipe.mjs). The model is
// the same one the mirror downloads, in its "lite" size: quicker to load and
// fast enough on a phone.

import type { Landmark } from "./geometry";

export const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task";

/** Finds the person in a video frame. A fake one stands in for it in tests */
export interface PoseDetector {
  /** The 33 landmarks of the person in this frame, or null if nobody is seen.
   * timestampMs must increase from one call to the next */
  detect(video: HTMLVideoElement, timestampMs: number): Landmark[] | null;
  close(): void;
}

/** True when WebGL is drawn by the processor (SwiftShader, llvmpipe), as on
 * computers without a usable graphics card. The GPU delegate is then about 5
 * times slower than the CPU one, and it keeps the page too busy to respond */
export function softwareWebGL(): boolean {
  try {
    const gl = document.createElement("canvas").getContext("webgl");
    if (!gl) return true;
    const info = gl.getExtension("WEBGL_debug_renderer_info");
    const renderer = info ? String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)) : "";
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    return /swiftshader|llvmpipe|software/i.test(renderer);
  } catch {
    return true;
  }
}

export async function loadPoseDetector(): Promise<PoseDetector> {
  const { FilesetResolver, PoseLandmarker } = await import("@mediapipe/tasks-vision");
  const fileset = await FilesetResolver.forVisionTasks("/mediapipe");
  const create = (delegate: "GPU" | "CPU") =>
    PoseLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: MODEL_URL, delegate },
      runningMode: "VIDEO",
      numPoses: 1,
      minPoseDetectionConfidence: 0.5, // the same as the mirror
      minPosePresenceConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });
  let landmarker;
  try {
    if (softwareWebGL()) throw new Error("no graphics card");
    landmarker = await create("GPU");
  } catch {
    landmarker = await create("CPU"); // no WebGL or only a software one, e.g. some phones and VMs
  }
  return {
    detect(video, timestampMs) {
      const result = landmarker.detectForVideo(video, timestampMs);
      const person = result.landmarks[0];
      return person ? person.map((p) => ({ x: p.x, y: p.y, visibility: p.visibility })) : null;
    },
    close: () => landmarker.close(),
  };
}
