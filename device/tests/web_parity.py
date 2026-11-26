"""The browser counts reps with a TypeScript copy of the counting logic
(web/src/train). To be sure both count the same, this builds sessions of
synthetic poses, runs them through the Python Engine and Reporter, and saves
the poses with what Python made of them to web/src/train/parity.json. The web
tests replay the same poses and must get the same sets and events. The file
also holds the tuning constants and the exercises, which the web tests check
are the same as theirs.

test_web_parity.py fails when the file is out of date. To refresh it after
changing the counting logic (here or in the browser):

    python tests/web_parity.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path[:0] = [str(Path(__file__).parent), str(Path(__file__).resolve().parents[1])]

from easyweight import config as cfg  # noqa: E402
from easyweight.engine import Engine  # noqa: E402
from easyweight.exercises import EXERCISES  # noqa: E402
from easyweight.recording import Landmark  # noqa: E402
from easyweight.reporter import Reporter  # noqa: E402
from poses import (  # noqa: E402
    CURLED,
    FPS,
    HALF_SQUAT,
    HANG,
    MOUTH,
    PRESS_BOTTOM,
    PRESS_TOP,
    RAISED,
    SIZE,
    SQUAT_BOTTOM,
    body_reps,
    move,
    pose,
    pushups,
    reps,
    sideways,
    squat,
    squats,
    still,
    tween,
)

PARITY_FILE = Path(__file__).resolve().parents[2] / "web" / "src" / "train" / "parity.json"
START = 1_700_000_000.0  # a real date (November 2023)
# Only these landmarks are measured. The others all sit at FILLER
USED = [9, 10, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
FILLER = (0.5, 0.25)


def drink():
    sip = pose(CURLED, left_wrist=MOUTH, right_wrist=MOUTH)
    return move(HANG, sip, HANG)


def one_arm():
    frames = []
    for _ in range(4):
        frames += [pose(HANG)] * 8 + [pose(HANG, right=CURLED)] * 8
    return frames


def low_visibility():
    """Curls where MediaPipe loses sight of the arm now and then"""
    frames = reps(CURLED, 4)
    return [pose(HANG, visibility=0.3) if i % 7 == 0 else f for i, f in enumerate(frames)]


def flickering():
    """Curls seen only just well enough: the visibility hovers around the line"""
    levels = [0.65, 0.55, 0.45, 0.55, 0.65, 0.58]
    return [[Landmark(p.x, p.y, levels[i % len(levels)]) for p in f]
            for i, f in enumerate(reps(CURLED, 4))]


def arms_out_squats():
    """Arms held out to the sides while squatting, like a lateral raise"""
    return body_reps(lambda b: squat(b, arms=(90 * b / SQUAT_BOTTOM, 170)), 0, SQUAT_BOTTOM, 6)


def seated_curls():
    """Sitting down on a bench (like the bottom of a squat), then curls"""
    sit = tween(lambda b: squat(b), 0, SQUAT_BOTTOM)
    held = [squat(SQUAT_BOTTOM)] * (3 * FPS)
    curls = body_reps(lambda e: squat(SQUAT_BOTTOM, arms=(0, e)), 175, 30, 5, frames_each=8)
    return sit + held + curls


def sitting_down():
    """Sitting down on a bench and staying there: one move like a squat"""
    return tween(lambda b: squat(b), 0, SQUAT_BOTTOM) + [squat(SQUAT_BOTTOM)] * (3 * FPS)


SCENARIOS = {
    "curls": [reps(CURLED, 10)],
    "lateral raises": [reps(RAISED, 8)],
    "overhead press": [reps(PRESS_TOP, 6, bottom=PRESS_BOTTOM)],
    "standing still": [still(5)],
    "rest then next set": [reps(CURLED, 5), still(9), reps(CURLED, 4)],
    "switch exercise after rest": [reps(CURLED, 5), still(9), reps(RAISED, 3)],
    "drinking during rest": [reps(CURLED, 5), still(9), drink(), still(2), reps(CURLED, 3)],
    "lifting weights before a press": [move(HANG, CURLED, PRESS_BOTTOM),
                                       reps(PRESS_TOP, 5, bottom=PRESS_BOTTOM)],
    "one arm": [one_arm()],
    "walking away": [reps(CURLED, 5), still(11, landmarks=False), reps(CURLED, 2)],
    "short absence": [reps(CURLED, 5), still(3, landmarks=False), reps(CURLED, 2)],
    "long rest": [reps(CURLED, 5), still(181), reps(RAISED, 2)],
    "arm out of sight": [low_visibility()],
    "visibility around the line": [flickering()],
    "curls at 15 fps": {"segments": [reps(CURLED, 10)], "fps": 15},
    "press standing sideways": [[sideways(f) for f in reps(PRESS_TOP, 5, bottom=PRESS_BOTTOM)]],
    "squats from the front": [squats(8)],
    "squats from the side": [squats(8, "side")],
    "half squats": [squats(5, depth=HALF_SQUAT)],
    "squats with the feet out of view": [squats(5, ankles=0.2)],
    "arms out during squats": [arms_out_squats()],
    "curls then squats": [reps(CURLED, 5), still(9), squats(4)],
    "sitting down for seated curls": [seated_curls()],
    "sitting down during rest": [reps(CURLED, 5), still(9), sitting_down()],
    "push-ups": [pushups(10)],
    "push-ups with sagging hips": [pushups(6, sag=0.1)],
    "push-ups that stop at 98 degrees": [pushups(5, depth=98)],
}


def compact(landmarks):
    """The measured landmarks of a frame, rounded like a recording, or None"""
    if landmarks is None:
        return None
    for i, p in enumerate(landmarks):
        if i not in USED:
            assert (p.x, p.y) == FILLER, "a landmark the browser test doesn't rebuild moved"
    return [[round(landmarks[i].x, 5), round(landmarks[i].y, 5), landmarks[i].visibility]
            for i in USED]


def expand(frame):
    """compact() undone: all 33 landmarks"""
    if frame is None:
        return None
    points = [Landmark(*FILLER, None) for _ in range(33)]
    for i, (x, y, v) in zip(USED, frame, strict=True):
        points[i] = Landmark(x, y, v)
    return points


def run_length(frames):
    """[[count, frame], ...]: a still pose for a minute is one entry, not 1800"""
    out = []
    for frame in frames:
        if out and out[-1][1] == frame:
            out[-1][0] += 1
        else:
            out.append([1, frame])
    return out


def scenario(spec):
    segments, fps = (spec["segments"], spec["fps"]) if isinstance(spec, dict) else (spec, FPS)
    frames = [compact(f) for segment in segments for f in segment]
    engine, reporter = Engine(), Reporter()
    events, counted, t = [], [], START
    for i, frame in enumerate(frames):
        if engine.step(expand(frame), SIZE, SIZE, t):
            counted.append(i)
        events += reporter.observe(engine.workout, t)
        t += 1 / fps
    engine.reset()
    events += reporter.observe(engine.workout, t)

    ids = {}

    def label(value):
        return ids.setdefault(value, f"id{len(ids) + 1}")

    def clean(event):
        data = {k: label(v) if k.endswith("_id") else v for k, v in event["data"].items()}
        # Times as seconds since 1970: Python and JavaScript write dates differently
        return {"id": label(event["id"]), "type": event["type"],
                "at": datetime.fromisoformat(event["at"]).timestamp(), "data": data}

    return {
        "fps": fps,
        "frames": run_length(frames),
        "counted": counted,
        "history": engine.workout.history,
        "events": [clean(e) for e in events],
    }


def constants():
    """The tuning constants and landmark numbers, for the browser to compare"""
    out = {k: v for k, v in vars(cfg).items()
           if k.isupper() and isinstance(v, (int, float)) and not isinstance(v, bool)}
    out["LANDMARKS"] = cfg.LANDMARKS
    return out


def build():
    return {
        "about": "Made by device/tests/web_parity.py. Don't edit: run it again",
        "size": SIZE,
        "fps": FPS,
        "start": START,
        "used": USED,
        "filler": FILLER,
        "config": constants(),
        "exercises": EXERCISES,
        "scenarios": {name: scenario(spec) for name, spec in SCENARIOS.items()},
    }


def dump(data):
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n"


if __name__ == "__main__":
    PARITY_FILE.write_text(dump(build()), encoding="utf-8")
    print(f"Wrote {PARITY_FILE}")
