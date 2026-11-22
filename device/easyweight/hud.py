"""Drawing the mirror display.

Text is collected into a list while drawing and rendered in one pass at the
end, so Pillow only has to convert the frame once.
"""
import functools
import time
from pathlib import Path

import cv2
import numpy as np

from .config import EXERCISES

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    ImageFont = None

# Colors are BGR (OpenCV's order). Behind a two way mirror only bright colors
# show through, so the HUD uses nothing darker than LIGHT_GRAY
WHITE = (255, 255, 255)
GREEN = (90, 255, 120)
CYAN = (255, 210, 60)
LIGHT_GRAY = (200, 200, 200)
AMBER = (69, 200, 255)  # feedback on the reps

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


@functools.cache
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
        for (text, x, y, _, color, align), font in zip(texts, fonts, strict=True):
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


def draw_hud(canvas, texts, workout, now, flash, cue=None, summary=None):
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
        if summary:  # from the coach: how the set went, and what to do next
            done, advice = summary
            add_text(texts, done, cx, H * 0.24 + 180 * s, 30 * s, WHITE)
            add_text(texts, advice, cx, H * 0.24 + 225 * s, 30 * s,
                     WHITE if advice.startswith("Tip") else AMBER)
    else:
        reps = max(left.reps, right.reps)
        add_text(texts, str(reps), cx, H * 0.24, 190 * s, GREEN if flash else WHITE)
        add_text(texts, f"SET {workout.set}", cx, H * 0.24 + 120 * s,
                 30 * s, LIGHT_GRAY)
        if cue:  # from the coach, like "Curl all the way up"
            add_text(texts, cue, cx, H * 0.24 + 180 * s, 30 * s, AMBER)


def draw_camera(canvas, frame):
    """Paste the webcam image (mirrored and darkened) behind the HUD"""
    H, W = canvas.shape[:2]
    fh, fw = frame.shape[:2]
    scale = min(W / fw, H / fh)
    dw, dh = int(fw * scale), int(fh * scale)
    x0, y0 = (W - dw) // 2, (H - dh) // 2
    view = cv2.resize(cv2.flip(frame, 1), (dw, dh))
    canvas[y0:y0 + dh, x0:x0 + dw] = cv2.convertScaleAbs(view, alpha=0.45)


def render(size, workout, now, flash, frame=None, cue=None, summary=None):
    """A full HUD image of size (width, height). frame is the camera picture to
    show behind it, or None for a black background. cue is the coach's
    feedback to show under the count, and summary its (how it went, what to do
    next) to show during the rest, if any"""
    W, H = size
    canvas = np.zeros((H, W, 3), np.uint8)
    texts = []
    if frame is not None:
        draw_camera(canvas, frame)
    draw_hud(canvas, texts, workout, now, flash, cue, summary)
    draw_texts(canvas, texts)
    return canvas
