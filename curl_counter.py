"""
EasyWeight - rep counter for the smart mirror HUD

Counts bicep curls, lateral raises and overhead presses from your webcam (it
recognizes which one you're doing) and shows the count as bright text on a
black screen. Behind a mirror, black is invisible, so only the numbers appear
to float on the glass.

Setup (once):
    pip install -r requirements.txt

Run:
    python curl_counter.py                  # default webcam, "full" model
    python curl_counter.py --camera 1       # use a different webcam
    python curl_counter.py --model lite     # faster on slower computers
    python curl_counter.py --fullscreen     # start fullscreen (for the mirror)


Keys (also work on a Hebrew keyboard layout):
    F       fullscreen on/off
    D       show/hide the camera picture (handy while testing)
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
# The terminal prints the top angle of every rep while running.
CURL_DOWN_ANGLE = 150  # elbow angle that counts as "arm straight"
CURL_UP_ANGLE = 50     # elbow angle that counts as "fully curled"
RAISE_DOWN_ANGLE = 30  # shoulder angle (0 = arm hanging down, 90 = out level with
                       # the shoulder) that counts as "arm down" in a lateral raise
RAISE_UP_ANGLE = 75    # shoulder angle that counts as "arm raised"
RAISE_MIN_ELBOW = 120  # a lateral raise keeps the elbow at least this straight,
                       # so curls and drinking can't count as raises
RAISE_MAX_ANGLE = 140  # and stays below this shoulder angle, so an overhead press can't
PRESS_DOWN_HEIGHT = 0.5  # wrist height above the shoulder (in shoulder widths) that
                         # counts as "weights at the shoulders" in an overhead press
PRESS_UP_HEIGHT = 1.0    # wrist height above the shoulder that counts as "pressed overhead"
MIN_VISIBILITY = 0.5   # ignore an arm when MediaPipe isn't confident it can see it
SMOOTHING = 0.4        # 0-1: lower = steadier but slower to react
SET_IDLE_SECONDS = 8   # no new rep for this long = the set is over and rest starts
MAX_REST_SECONDS = 180  # resting longer than this resets the count
AWAY_RESET_SECONDS = 10  # reset the count after nobody has been seen this long
DRINK_DISTANCE = 0.52  # a lift during rest where the wrist comes closer to the mouth
                       # than this (in shoulder widths) is drinking, not a curl

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
             "pose_landmarker_{v}/float16/latest/pose_landmarker_{v}.task")
MODEL_SIZES_MB = {"lite": 6, "full": 9, "heavy": 31}

WINDOW = "EasyWeight"
DEFAULT_SIZE = (1280, 720)

# MediaPipe landmark numbers: shoulder, elbow, wrist (the person's own left/right)
ARMS = {"left": (11, 13, 15), "right": (12, 14, 16)}

# Colors are BGR (OpenCV's order). Behind a two way mirror only bright colors
# show through, so the HUD uses nothing darker than LIGHT_GRAY
WHITE = (255, 255, 255)
GREEN = (90, 255, 120)
CYAN = (255, 210, 60)
LIGHT_GRAY = (200, 200, 200)

# Bold TrueType fonts, first one found wins. Thin strokes vanish behind the glass.
# Inter Display (in the fonts folder, free under the SIL Open Font License) looks
# like Apple's San Francisco font, which can't be used outside Apple's systems
FONT_FILES = [
    str(Path(__file__).resolve().parent / "fonts" / "InterDisplay-SemiBold.ttf"),
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
            # Uncompressed 720p is too much for USB (about 4 fps on many webcams),
            # so ask for MJPG. It must come after the size or DirectShow ignores it
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
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


def arm_points(landmarks, ids, width, height):
    """Pixel positions of these landmarks, or None if MediaPipe can't see one of
    them well. Pixels, so angles aren't squashed by the frame's shape"""
    points = []
    for i in ids:
        lm = landmarks[i]
        if lm.visibility is not None and lm.visibility < MIN_VISIBILITY:
            return None
        points.append((lm.x * width, lm.y * height))
    return points


def elbow_angle(landmarks, side, width, height):
    """Elbow angle for one arm (about 180 = straight), or None if it can't be seen"""
    points = arm_points(landmarks, ARMS[side], width, height)
    return angle_at(*points) if points else None


def shoulder_angle(landmarks, side, width, height):
    """How far the upper arm is raised out to the side: 0 = hanging straight down,
    90 = level with the shoulder. Measured from straight down rather than from the
    hip, so it works when the camera doesn't see the hips"""
    points = arm_points(landmarks, ARMS[side][:2], width, height)
    if not points:
        return None
    (sx, sy), elbow = points
    return angle_at((sx, sy + 100), (sx, sy), elbow)


def joint_height(landmarks, side, joint, width, height):
    """How far a joint of the arm (1 = elbow, 2 = wrist, as in ARMS) is above the
    shoulder, in shoulder widths (negative = below it). The press uses the wrist
    height rather than an angle, because with the weights held in front the
    wrist is above the shoulder at the bottom too"""
    points = arm_points(landmarks, (ARMS[side][0], ARMS[side][joint]), width, height)
    if not points:
        return None
    shoulders = math.dist(*((landmarks[i].x * width, landmarks[i].y * height) for i in (11, 12)))
    if shoulders == 0:
        return None
    (_, shoulder_y), (_, joint_y) = points
    return (shoulder_y - joint_y) / shoulders


def mouth_distance(landmarks, side, width, height):
    """How far the wrist is from the mouth, in shoulder widths (so it doesn't
    matter how far the person stands from the camera). Drinking brings the hand
    to the mouth, a curl stops near the shoulder. The face points aren't checked
    for visibility because a bottle often covers the mouth, and MediaPipe still
    places them well"""
    p = lambda i: (landmarks[i].x * width, landmarks[i].y * height)
    mouth_l, mouth_r = p(9), p(10)
    mouth = ((mouth_l[0] + mouth_r[0]) / 2, (mouth_l[1] + mouth_r[1]) / 2)
    shoulders = math.dist(p(11), p(12))
    if shoulders == 0:
        return None
    return math.dist(p(ARMS[side][2]), mouth) / shoulders


class ArmCounter:
    """One arm doing one exercise: the angle goes past down_angle, then past
    up_angle = 1 rep. For a curl the elbow angle gets smaller on the way up, for
    a lateral raise the shoulder angle gets bigger. For an overhead press the
    "angle" is the wrist height, which also gets bigger"""

    def __init__(self, name, down_angle, up_angle, measure="angle"):
        self.name = name
        self.measure = measure  # what the angle is, for the printout
        self.down_angle, self.up_angle = down_angle, up_angle
        self.sign = 1 if down_angle > up_angle else -1  # 1 = the angle shrinks on the way up
        self.reps = 0
        self.angle = None      # smoothed angle
        self.stage = None      # "down" or "up"
        self.visible = False
        self.mouth = None      # wrist to mouth distance right now
        self.closest = math.inf  # closest the wrist came to the mouth since the arm was down
        self.top = None        # furthest up the angle got since the arm was down
        # Highest the wrist and elbow got since the arm was down (joint_height).
        # Only printed for now, to find what tells a curl from touching the face
        self.wrist_top = self.elbow_top = -math.inf

    def update(self, raw_angle, mouth=None, form_ok=True, wrist=None, elbow=None):
        """Feed one reading (or None), the mouth_distance, whether the arm's form
        fits this exercise, and the wrist and elbow joint_height. Returns True
        when this reading completes a rep"""
        self.visible = raw_angle is not None
        self.mouth = mouth
        if raw_angle is None:
            return False
        if mouth is not None:
            self.closest = min(self.closest, mouth)
        if wrist is not None:
            self.wrist_top = max(self.wrist_top, wrist)
        if elbow is not None:
            self.elbow_top = max(self.elbow_top, elbow)
        if self.angle is None:
            self.angle = raw_angle
        else:
            self.angle += SMOOTHING * (raw_angle - self.angle)
        if self.top is None or self.sign * (self.angle - self.top) < 0:
            self.top = self.angle
        if self.sign * (self.angle - self.down_angle) > 0:
            if self.stage == "up":  # a lift just ended. Printed to help with tuning
                top = f"{self.top:.0f}" if self.measure == "angle" else f"{self.top:.2f}"
                print(f"{self.name}: top {self.measure} {top}, "
                      f"wrist came {self.closest:.2f} from the mouth, "
                      f"above shoulder: wrist up to {self.wrist_top:+.2f}, "
                      f"elbow up to {self.elbow_top:+.2f}", flush=True)
            self.stage = "down"
            self.closest = math.inf
            self.top = None
            self.wrist_top = self.elbow_top = -math.inf
        elif self.sign * (self.angle - self.up_angle) < 0 and self.stage == "down" and form_ok:
            self.stage = "up"
            self.reps += 1
            return True
        return False

    def progress(self):
        """How far through the rep the arm is: 0 = down, 1 = all the way up"""
        if self.angle is None:
            return 0.0
        done = (self.down_angle - self.angle) / (self.down_angle - self.up_angle)
        return min(1.0, max(0.0, done))


EXERCISES = {"curl": "BICEP CURLS", "raise": "LATERAL RAISES", "press": "OVERHEAD PRESS"}


class Workout:
    """Splits the reps into sets and knows which exercise each set is. The first
    rep of a set decides the exercise, and only that exercise counts until the
    set ends. No new rep for SET_IDLE_SECONDS means resting, and the first rep
    after a rest starts the next set (which can be another exercise). A curl
    during rest is held back until the arm straightens, so drinking water or
    touching the face doesn't count"""

    def __init__(self):
        self.counters = {
            "curl": {side: ArmCounter(f"{side} arm curl", CURL_DOWN_ANGLE, CURL_UP_ANGLE)
                     for side in ARMS},
            "raise": {side: ArmCounter(f"{side} arm raise", RAISE_DOWN_ANGLE, RAISE_UP_ANGLE)
                      for side in ARMS},
            "press": {side: ArmCounter(f"{side} arm press", PRESS_DOWN_HEIGHT, PRESS_UP_HEIGHT,
                                       measure="height")
                      for side in ARMS},
        }
        self.reset()

    def arms(self):
        """The (left, right) counters to show: the set's exercise, or before the
        first rep, whichever exercise the arms are further into"""
        if self.exercise:
            pair = self.counters[self.exercise]
        else:
            pair = max(self.counters.values(),
                       key=lambda p: max(c.progress() for c in p.values()))
        return pair["left"], pair["right"]

    def clear_reps(self):
        for pair in self.counters.values():
            for counter in pair.values():
                counter.reps = 0

    def set_reps(self):
        return max(c.reps for c in self.counters[self.exercise].values())

    def resting(self, now):
        return self.last_rep is not None and now - self.last_rep > SET_IDLE_SECONDS

    def rest_time(self, now):
        """Seconds since the person stopped, counted from their last rep"""
        return now - self.last_rep

    def start_set(self, exercise, counter, now):
        """counter's rep is the first rep of a set of exercise. Switching exercise
        starts its sets from 1"""
        self.set = self.prev_set + 1 if exercise == self.prev_exercise else 1
        self.exercise = exercise
        self.clear_reps()
        counter.reps = 1
        self.last_rep = now
        self.pending = None
        print(f"Set {self.set}: {EXERCISES[exercise].lower()}", flush=True)

    def next_set(self, exercise, counter, now):
        """After a rest: counter's rep starts the next set"""
        self.prev_exercise, self.prev_set = self.exercise, self.set
        self.start_set(exercise, counter, now)

    def add_rep(self, now, exercise, counter):
        """Call after counter completed a rep of exercise. Returns True if it counts
        right away. A curl during rest is held back until check_pending knows it
        isn't drinking (a raise or a press can't be drinking)"""
        if self.resting(now):
            if exercise == "curl":
                counter.reps -= 1
                if self.pending is None:
                    self.pending = counter
                return False
            self.next_set(exercise, counter, now)
            return True
        if self.exercise is None:
            self.start_set(exercise, counter, now)
            return True
        if exercise == self.exercise:
            self.last_rep = now
            return True
        if self.exercise == "curl" and exercise == "press" and self.set_reps() < 2:
            # The "curl" was lifting the weights to the shoulders for a press
            self.start_set(exercise, counter, now)
            return True
        counter.reps -= 1  # not the exercise this set is doing
        return False

    def check_pending(self, now):
        """Call every frame. Returns True when a held back curl turned out to be a
        real rep and started the next set. There's no time limit: people often
        lift a bottle to the chest and pause before drinking"""
        counter = self.pending
        if counter is None:
            return False
        if counter.closest < DRINK_DISTANCE:
            print(f"Lift during rest: wrist came {counter.closest:.2f} from the mouth "
                  f"(drinking below {DRINK_DISTANCE}) -> drinking, ignored", flush=True)
            self.pending = None
            return False
        # Straight again without reaching the mouth. Checked after the line above
        # every frame, so a lift that came near the mouth never gets here
        if counter.stage == "down":
            print(f"Lift during rest: wrist stayed {DRINK_DISTANCE}+ from the mouth "
                  f"-> not drinking", flush=True)
            self.next_set("curl", counter, now)
            return True
        return False

    def reset(self):
        self.clear_reps()
        self.exercise = None   # "curl", "raise" or "press", None before the first rep
        self.set = 1
        self.prev_exercise, self.prev_set = None, 0  # the set before this one
        self.last_rep = None   # time of the latest rep, None before the first one
        self.pending = None    # counter of a curl during rest that might be drinking


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
    """Queue text centered on (x, y), or starting at x when align="left", or ending
    at x when align="right". size is in pixels"""
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
                      anchor={"center": "mm", "left": "lm", "right": "rm"}[align])
        canvas[:] = np.asarray(img)
        return
    for text, x, y, size, color, align in texts:
        scale, thickness = size / 32, max(1, round(size / 16))
        (w, h), _ = cv2.getTextSize(text, FALLBACK_FONT, scale, thickness)
        left = {"center": x - w / 2, "left": x, "right": x - w}[align]
        cv2.putText(canvas, text, (int(left), int(y + h / 2)), FALLBACK_FONT, scale,
                    color, thickness, cv2.LINE_AA)


def draw_hud(canvas, texts, workout, now, flash):
    """Draw the mirror display. Everything scales with the window size

    Only the time and date (top left) and the exercise and the count (or the
    rest timer) at the top, so the rest of the glass stays clear for your
    reflection
    """
    H, W = canvas.shape[:2]
    s = min(W / 1280, H / 720)
    cx = W / 2
    left, right = workout.arms()

    clock = time.localtime()
    add_text(texts, time.strftime("%H:%M", clock), 40 * s, H * 0.07, 40 * s, WHITE,
             align="left")
    add_text(texts, time.strftime("%d/%m/%Y", clock), 40 * s, H * 0.07 + 40 * s, 24 * s,
             LIGHT_GRAY, align="left")
    add_text(texts, "EasyWeight", W - 40 * s, H * 0.07, 34 * s, CYAN, align="right")

    if workout.exercise:  # no name until the first rep shows which exercise it is
        add_text(texts, EXERCISES[workout.exercise], cx, H * 0.07, 30 * s, LIGHT_GRAY)
    if workout.resting(now):
        minutes, seconds = divmod(int(workout.rest_time(now)), 60)
        add_text(texts, f"{minutes}:{seconds:02d}", cx, H * 0.24, 190 * s, CYAN)
        add_text(texts, f"REST - SET {workout.set} DONE", cx, H * 0.24 + 120 * s,
                 30 * s, LIGHT_GRAY)
    else:
        reps = max(left.reps, right.reps)
        add_text(texts, str(reps), cx, H * 0.24, 190 * s, GREEN if flash else WHITE)
        add_text(texts, f"SET {workout.set}", cx, H * 0.24 + 120 * s,
                 30 * s, LIGHT_GRAY)


def draw_camera(canvas, frame):
    """Paste the webcam image (mirrored and darkened) behind the HUD"""
    H, W = canvas.shape[:2]
    fh, fw = frame.shape[:2]
    scale = min(W / fw, H / fh)
    dw, dh = int(fw * scale), int(fh * scale)
    x0, y0 = (W - dw) // 2, (H - dh) // 2
    view = cv2.resize(cv2.flip(frame, 1), (dw, dh))
    canvas[y0:y0 + dh, x0:x0 + dw] = cv2.convertScaleAbs(view, alpha=0.45)



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
    p = argparse.ArgumentParser(
        description="EasyWeight rep counter: bicep curls, lateral raises, overhead presses")
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

    workout = Workout()
    fullscreen, show_camera = args.fullscreen, True
    flash_until, failed_reads = 0.0, 0
    last_seen = time.perf_counter()

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, *DEFAULT_SIZE)
    set_fullscreen(fullscreen)

    start = time.perf_counter()
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

                # MediaPipe needs RGB images and strictly increasing timestamps
                ts = max(int((now - start) * 1000), last_ts + 1)
                last_ts = ts
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = landmarker.detect_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
                landmarks = result.pose_landmarks[0] if result.pose_landmarks else None

                h, w = frame.shape[:2]
                # Every exercise is watched on both arms. A raise must keep the
                # elbow fairly straight, so a curl or a drink can't count as one,
                # and stay below shoulder RAISE_MAX_ANGLE, so a press can't either
                for side in ARMS:
                    elbow = elbow_angle(landmarks, side, w, h) if landmarks else None
                    shoulder = shoulder_angle(landmarks, side, w, h) if landmarks else None
                    wrist = joint_height(landmarks, side, 2, w, h) if landmarks else None
                    elbow_up = joint_height(landmarks, side, 1, w, h) if landmarks else None
                    mouth = mouth_distance(landmarks, side, w, h) if elbow is not None else None
                    raise_ok = (elbow is not None and elbow > RAISE_MIN_ELBOW
                                and shoulder is not None and shoulder < RAISE_MAX_ANGLE)
                    for exercise, angle, form_ok in (("curl", elbow, True),
                                                     ("raise", shoulder, raise_ok),
                                                     ("press", wrist, True)):
                        counter = workout.counters[exercise][side]
                        if (counter.update(angle, mouth, form_ok, wrist, elbow_up)
                                and workout.add_rep(now, exercise, counter)):
                            flash_until = now + 0.35
                if workout.check_pending(now):
                    flash_until = now + 0.35

                # Nobody in front of the mirror for a while, or a rest that went
                # on too long: start fresh
                if landmarks:
                    last_seen = now
                elif now - last_seen > AWAY_RESET_SECONDS:
                    workout.reset()
                if workout.resting(now) and workout.rest_time(now) > MAX_REST_SECONDS:
                    workout.reset()

                W, H = window_size()
                canvas = np.zeros((H, W, 3), np.uint8)
                texts = []
                if show_camera:
                    draw_camera(canvas, frame)
                draw_hud(canvas, texts, workout, now, flash=now < flash_until)
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
                    workout.reset()
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
