"""
EasyWeight - bicep curl counter for the smart mirror HUD

Counts bicep curls from your webcam and shows the count as bright text on a
black screen. Behind a mirror, black is invisible, so only the numbers
appear to float on the glass.

Setup (once):
    pip install -r requirements.txt

Run:
    python curl_counter.py                  # default webcam, "full" model
    python curl_counter.py --camera 1       # use a different webcam
    python curl_counter.py --model lite     # faster on slower computers
    python curl_counter.py --fullscreen     # start fullscreen (for the mirror)


Keys (also work on a Hebrew keyboard layout):
    F       fullscreen on/off
    D       show/hide the camera with the skeleton (handy while testing)
    R       reset the count
    Q, Esc  quit
"""
import argparse
import functools
import math
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path

os.environ.setdefault("GLOG_minloglevel", "2")  # hide MediaPipe's startup log noise

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    ImageFont = None

# Tuning: adjust these if reps are missed or counted when they shouldn't be.
# Press D while running to see your live elbow angles.
DOWN_ANGLE = 150       # elbow angle that counts as "arm straight"
UP_ANGLE = 50          # elbow angle that counts as "fully curled"
MIN_VISIBILITY = 0.5   # ignore an arm when MediaPipe isn't confident it can see it
SMOOTHING = 0.4        # 0-1: lower = steadier but slower to react
AWAY_RESET_SECONDS = 60  # reset the count after nobody has been seen this long

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
             "pose_landmarker_{v}/float16/latest/pose_landmarker_{v}.task")
MODEL_SIZES_MB = {"lite": 6, "full": 9, "heavy": 31}

WINDOW = "EasyWeight"
DEFAULT_SIZE = (1280, 720)

# MediaPipe landmark numbers: shoulder, elbow, wrist (the person's own left/right)
ARMS = {"left": (11, 13, 15), "right": (12, 14, 16)}
SKELETON = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24),
            (23, 24), (23, 25), (25, 27), (24, 26), (26, 28)]

# Colors are BGR (OpenCV's order). Behind a two way mirror only bright colors
# show through, so the HUD uses nothing darker than GRAY, and GRAY only for
# things that are meant to look faded (an arm the camera can't see)
WHITE = (255, 255, 255)
GREEN = (90, 255, 120)
CYAN = (255, 210, 60)
LIGHT_GRAY = (200, 200, 200)
GRAY = (140, 140, 140)

# Bold TrueType fonts, first one found wins. Thin strokes vanish behind the glass
FONT_FILES = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FALLBACK_FONT = cv2.FONT_HERSHEY_DUPLEX  # used when Pillow or a font file is missing

# Key codes. The 0x05.. codes are the Hebrew letters on the same keys,
# and "/" is where Q sits on a Hebrew keyboard
KEYS = {
    "quit": {27, ord("q"), ord("Q"), ord("/")},
    "fullscreen": {ord("f"), ord("F"), 0x05DB},  # כ
    "camera": {ord("d"), ord("D"), 0x05D2},      # ג
    "reset": {ord("r"), ord("R"), 0x05E8},       # ר
}


# Model and camera
def load_model(variant):
    """Return the model file's bytes, downloading it the first time"""
    path = Path(__file__).resolve().parent / f"pose_landmarker_{variant}.task"
    if not path.exists():
        url = MODEL_URL.format(v=variant)
        print(f"Downloading the {variant} pose model "
              f"(about {MODEL_SIZES_MB[variant]} MB), one time only...")
        tmp = path.with_name(path.name + ".part")
        try: # If download fails
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = ssl.create_default_context()
            with urllib.request.urlopen(url, context=ctx, timeout=60) as resp, \
                    open(tmp, "wb") as f:
                while chunk := resp.read(1 << 16):
                    f.write(chunk)
            tmp.replace(path)
        except Exception as e:
            tmp.unlink(missing_ok=True)
            sys.exit(f"\nCouldn't download the model: {e}\n"
                     f"Download it in your browser from:\n  {url}\n"
                     f"and save it in the same folder as this script, named {path.name}")
        print("Done.")
    # Reading the file ourselves (instead of giving MediaPipe the path) avoids
    # file path problems with non-English folder names on Windows
    return path.read_bytes()


def create_landmarker(model_bytes):
    options = vision.PoseLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_buffer=model_bytes),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5, # change this to be more/less accurate
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.PoseLandmarker.create_from_options(options)


def open_camera(index):
    # DirectShow opens most USB webcams faster and more reliably on Windows
    backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if sys.platform.startswith("win") else [cv2.CAP_ANY]
    for backend in backends:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            return cap
        cap.release()
    return None


# Rep counting, a - shoulder, b - elbow, c - wrist
def angle_at(a, b, c):
    """Angle ABC in degrees, measured at point b"""
    v1 = (a[0] - b[0], a[1] - b[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return None
    cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def elbow_angle(landmarks, side, width, height):
    """Elbow angle for one arm, or None if MediaPipe can't see that arm well"""
    points = []
    for i in ARMS[side]:
        lm = landmarks[i]
        if lm.visibility is not None and lm.visibility < MIN_VISIBILITY:
            return None
        points.append((lm.x * width, lm.y * height))  # pixels, so the angle isn't squashed
    return angle_at(*points)


class ArmCounter:
    """One arm: straight (above DOWN_ANGLE), then curled (below UP_ANGLE) = 1 rep"""

    def __init__(self):
        self.reps = 0
        self.angle = None      # smoothed elbow angle
        self.stage = None      # "down" (arm straight) or "up" (curled)
        self.visible = False

    def update(self, raw_angle):
        """Feed one reading (or None). Returns True when this reading completes a rep"""
        self.visible = raw_angle is not None
        if raw_angle is None:
            return False
        if self.angle is None:
            self.angle = raw_angle
        else:
            self.angle += SMOOTHING * (raw_angle - self.angle)
        if self.angle > DOWN_ANGLE:
            self.stage = "down"
        elif self.angle < UP_ANGLE and self.stage == "down":
            self.stage = "up"
            self.reps += 1
            return True
        return False

    def progress(self):
        """How far through the curl the arm is: 0 = straight, 1 = fully curled"""
        if self.angle is None:
            return 0.0
        return min(1.0, max(0.0, (DOWN_ANGLE - self.angle) / (DOWN_ANGLE - UP_ANGLE)))


# Drawing
# Text is collected into a list while drawing and rendered in one pass at the
# end, so Pillow only has to convert the frame once
@functools.lru_cache(maxsize=None)
def load_font(size):
    if ImageFont is None:
        return None
    for path in FONT_FILES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return None


def add_text(texts, text, x, y, size, color, align="center"):
    """Queue text centered on (x, y), or starting at x when align="left". size is in pixels"""
    texts.append((text, x, y, max(8, round(size)), color, align))


def draw_texts(canvas, texts):
    fonts = [load_font(size) for _, _, _, size, _, _ in texts]
    if all(fonts):
        # The canvas is BGR but Pillow treats it as RGB. Passing the BGR colors
        # unchanged puts each value in the right channel, so no conversion is needed
        img = Image.fromarray(canvas)
        draw = ImageDraw.Draw(img)
        for (text, x, y, _, color, align), font in zip(texts, fonts):
            draw.text((x, y), text, font=font, fill=color,
                      anchor="mm" if align == "center" else "lm")
        canvas[:] = np.asarray(img)
        return
    for text, x, y, size, color, align in texts:
        scale, thickness = size / 32, max(1, round(size / 16))
        (w, h), _ = cv2.getTextSize(text, FALLBACK_FONT, scale, thickness)
        left = x - w / 2 if align == "center" else x
        cv2.putText(canvas, text, (int(left), int(y + h / 2)), FALLBACK_FONT, scale,
                    color, thickness, cv2.LINE_AA)


def draw_hud(canvas, texts, left, right, person_found, flash, show_hints):
    """Draw the mirror display. Everything scales with the window size

    The middle of the screen stays empty so your reflection isn't covered: the
    count is at the top, the arm bars run along the edges, messages at the bottom
    """
    H, W = canvas.shape[:2]
    s = min(W / 1280, H / 720)
    t = lambda base: max(1, round(base * s))  # line thickness
    cx = W / 2

    add_text(texts, "BICEP CURLS", cx, H * 0.07, 30 * s, LIGHT_GRAY)
    reps = max(left.reps, right.reps)
    add_text(texts, str(reps), cx, H * 0.24, 190 * s, GREEN if flash else WHITE)
    add_text(texts, "REPS", cx, H * 0.24 + 120 * s, 30 * s, LIGHT_GRAY)

    # One progress bar per arm, along the edges. The left arm's bar is on the
    # left, where you see that arm in the mirror. Green means the rep counted:
    # straighten to reset. An arm the camera can't see gets no bar at all
    bar_w = max(16, int(40 * s))
    top, bottom = int(H * 0.30), int(H * 0.80)
    for counter, x, label in ((left, int(W * 0.05), "L"),
                              (right, int(W * 0.95) - bar_w, "R")):
        if counter.visible:
            cv2.rectangle(canvas, (x, top), (x + bar_w, bottom), LIGHT_GRAY, t(3))
            fill_top = int(bottom - (bottom - top) * counter.progress())
            color = GREEN if counter.stage == "up" else CYAN
            cv2.rectangle(canvas, (x, fill_top), (x + bar_w, bottom), color, -1)
        add_text(texts, f"{label} {counter.reps}", x + bar_w / 2, bottom + 40 * s, 34 * s,
                 WHITE if counter.visible else GRAY)

    if not person_found:
        add_text(texts, "Step in front of the mirror", cx, H * 0.90, 34 * s, LIGHT_GRAY)
    if show_hints:
        add_text(texts, "F fullscreen    D camera    R reset    Q quit",
                 cx, H * 0.96, 20 * s, GRAY)


def draw_camera(canvas, frame, landmarks):
    """Paste the webcam image (mirrored and darkened) behind the HUD, with the skeleton"""
    H, W = canvas.shape[:2]
    fh, fw = frame.shape[:2]
    scale = min(W / fw, H / fh)
    dw, dh = int(fw * scale), int(fh * scale)
    x0, y0 = (W - dw) // 2, (H - dh) // 2
    view = cv2.resize(cv2.flip(frame, 1), (dw, dh))
    canvas[y0:y0 + dh, x0:x0 + dw] = cv2.convertScaleAbs(view, alpha=0.45)
    if landmarks:
        pts = [(int(x0 + (1 - lm.x) * dw), int(y0 + lm.y * dh)) for lm in landmarks]
        for a, b in SKELETON:
            cv2.line(canvas, pts[a], pts[b], WHITE, 2, cv2.LINE_AA)
        for i in ARMS["left"] + ARMS["right"]:
            cv2.circle(canvas, pts[i], 6, CYAN, -1, cv2.LINE_AA)


def draw_debug_text(canvas, texts, left, right, fps):
    H, W = canvas.shape[:2]
    s = min(W / 1280, H / 720)
    fmt = lambda c: f"{c.angle:.0f}" if c.visible and c.angle is not None else "--"
    text = (f"elbow angle  L {fmt(left)}  R {fmt(right)}   "
            f"(straight > {DOWN_ANGLE}, curled < {UP_ANGLE})   {fps:.0f} fps")
    add_text(texts, text, 16 * s, H - 24 * s, 20 * s, LIGHT_GRAY, align="left")


# Window helpers
def window_size():
    try:
        _, _, w, h = cv2.getWindowImageRect(WINDOW)
        if w > 100 and h > 100:
            return w, h
    except cv2.error:
        pass
    return DEFAULT_SIZE


def set_fullscreen(on):
    cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN if on else cv2.WINDOW_NORMAL)


def window_closed():
    try:
        return cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def key_action(code):
    for action, codes in KEYS.items():
        if code in codes:
            return action
    return None


# Main loop
def parse_args():
    p = argparse.ArgumentParser(description="EasyWeight bicep curl counter")
    p.add_argument("--camera", type=int, default=0,
                   help="webcam number (try 1 or 2 if 0 is the wrong camera)")
    p.add_argument("--model", choices=["lite", "full", "heavy"], default="full",
                   help="lite = fastest, heavy = most accurate")
    p.add_argument("--fullscreen", action="store_true", help="start in fullscreen")
    return p.parse_args()


def main():
    args = parse_args()
    model = load_model(args.model)
    cap = open_camera(args.camera)
    if cap is None:
        sys.exit(f"Couldn't open webcam {args.camera}. "
                 "Is another app using it? You can also try --camera 1")

    left, right = ArmCounter(), ArmCounter()
    fullscreen, show_camera = args.fullscreen, False
    flash_until, fps, failed_reads = 0.0, 0.0, 0
    last_seen = time.perf_counter()

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, *DEFAULT_SIZE)
    set_fullscreen(fullscreen)

    start = last = time.perf_counter()
    last_ts = -1
    try:
        with create_landmarker(model) as landmarker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    failed_reads += 1
                    if failed_reads > 50:
                        print("The webcam stopped sending frames.")
                        break
                    continue
                failed_reads = 0

                now = time.perf_counter()
                dt = max(now - last, 1e-6)
                fps = 1 / dt if fps == 0 else 0.9 * fps + 0.1 / dt
                last = now

                # MediaPipe needs RGB images and strictly increasing timestamps
                ts = max(int((now - start) * 1000), last_ts + 1)
                last_ts = ts
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = landmarker.detect_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
                landmarks = result.pose_landmarks[0] if result.pose_landmarks else None

                h, w = frame.shape[:2]
                for counter, side in ((left, "left"), (right, "right")):
                    angle = elbow_angle(landmarks, side, w, h) if landmarks else None
                    if counter.update(angle):
                        flash_until = now + 0.35

                # Nobody in front of the mirror for a while: start fresh for the next person
                if landmarks:
                    last_seen = now
                elif now - last_seen > AWAY_RESET_SECONDS:
                    left.reps = right.reps = 0

                W, H = window_size()
                canvas = np.zeros((H, W, 3), np.uint8)
                texts = []
                if show_camera:
                    draw_camera(canvas, frame, landmarks)
                draw_hud(canvas, texts, left, right, landmarks is not None,
                         flash=now < flash_until, show_hints=not fullscreen)
                if show_camera:
                    draw_debug_text(canvas, texts, left, right, fps)
                draw_texts(canvas, texts)
                cv2.imshow(WINDOW, canvas)

                action = key_action(cv2.waitKeyEx(1))
                if action == "quit":
                    break
                if action == "fullscreen":
                    fullscreen = not fullscreen
                    set_fullscreen(fullscreen)
                elif action == "camera":
                    show_camera = not show_camera
                elif action == "reset":
                    left.reps = right.reps = 0
                if window_closed():
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
