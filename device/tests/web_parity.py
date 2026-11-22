"""The browser counts reps with a TypeScript copy of the counting logic
(web/src/train). To be sure both count the same, this builds sessions of
synthetic poses, runs them through the Python Engine and Reporter, and saves
the poses with what Python made of them to web/src/train/parity.json. The web
tests replay the same poses and must get the same sets and events.

test_web_parity.py fails when the file is out of date. To refresh it after
changing the counting logic (here or in the browser):

    python tests/web_parity.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path[:0] = [str(Path(__file__).parent), str(Path(__file__).resolve().parents[1])]

from easyweight.engine import Engine  # noqa: E402
from easyweight.recording import Landmark  # noqa: E402
from easyweight.reporter import Reporter  # noqa: E402
from poses import (  # noqa: E402
    CURLED,
    FPS,
    HANG,
    MOUTH,
    PRESS_BOTTOM,
    PRESS_TOP,
    RAISED,
    SIZE,
    move,
    pose,
    reps,
    still,
)

PARITY_FILE = Path(__file__).resolve().parents[2] / "web" / "src" / "train" / "parity.json"
START = 1_700_000_000.0  # a real date (November 2023)
# Only these landmarks are measured. The others all sit at FILLER
USED = [9, 10, 11, 12, 13, 14, 15, 16]
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


def scenario(segments):
    frames = [compact(f) for segment in segments for f in segment]
    engine, reporter = Engine(), Reporter()
    events, counted, t = [], [], START
    for i, frame in enumerate(frames):
        if engine.step(expand(frame), SIZE, SIZE, t):
            counted.append(i)
        events += reporter.observe(engine.workout, t)
        t += 1 / FPS
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
        "frames": run_length(frames),
        "counted": counted,
        "history": engine.workout.history,
        "events": [clean(e) for e in events],
    }


def build():
    return {
        "about": "Made by device/tests/web_parity.py. Don't edit: run it again",
        "size": SIZE,
        "fps": FPS,
        "start": START,
        "used": USED,
        "filler": FILLER,
        "scenarios": {name: scenario(segments) for name, segments in SCENARIOS.items()},
    }


def dump(data):
    return json.dumps(data, separators=(",", ":")) + "\n"


if __name__ == "__main__":
    PARITY_FILE.write_text(dump(build()), encoding="utf-8")
    print(f"Wrote {PARITY_FILE}")
