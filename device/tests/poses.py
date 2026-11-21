"""Builds synthetic pose landmarks, so the counting logic can be tested without
a camera. The figure stands facing the camera in a 1000 x 1000 frame with its
shoulders 200 px apart, and each arm is posed by two angles:

    shoulder: 0 = hanging straight down, 90 = out level with the shoulder
    elbow:    180 = straight, smaller = more bent (the forearm bends upward)

A move is a list of (shoulder, elbow) poses the arms pass through, and frames()
turns moves into timed frames at 30 fps.
"""
import math

from easyweight.recording import Landmark

SIZE = 1000  # frame width and height in pixels
FPS = 30
SHOULDER = {"left": (0.6, 0.4), "right": (0.4, 0.4)}
OUT = {"left": 1, "right": -1}  # which way "out to the side" is in the picture
MOUTH = (0.5, 0.3)
UPPER_ARM = FOREARM = 0.15

HANG = (0, 175)          # arms hanging, almost straight
CURLED = (0, 30)         # top of a curl
RAISED = (90, 170)       # top of a lateral raise
PRESS_BOTTOM = (90, 150)  # weights at the shoulders
PRESS_TOP = (165, 175)    # pressed overhead


def _rotate(v, degrees):
    a = math.radians(degrees)
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


def arm(side, shoulder_angle, elbow_angle, wrist=None):
    """(shoulder, elbow, wrist) positions for one arm. wrist overrides where the
    wrist goes, e.g. MOUTH for drinking"""
    sx, sy = SHOULDER[side]
    out = OUT[side]
    a = math.radians(shoulder_angle)
    upper = (out * math.sin(a), math.cos(a))
    elbow = (sx + UPPER_ARM * upper[0], sy + UPPER_ARM * upper[1])
    if wrist is None:
        fore = _rotate(upper, -out * (180 - elbow_angle))
        wrist = (elbow[0] + FOREARM * fore[0], elbow[1] + FOREARM * fore[1])
    return (sx, sy), elbow, wrist


def pose(left=HANG, right=None, left_wrist=None, right_wrist=None, visibility=0.99):
    """33 landmarks with both arms posed (right copies left unless given)"""
    right = left if right is None else right
    points = [(0.5, 0.25)] * 33  # face and body points nobody measures
    points[9] = (MOUTH[0] + 0.02, MOUTH[1])
    points[10] = (MOUTH[0] - 0.02, MOUTH[1])
    for side, (shoulder, elbow), wrist in (("left", left, left_wrist),
                                           ("right", right, right_wrist)):
        s, e, w = arm(side, shoulder, elbow, wrist)
        i = 11 if side == "left" else 12
        points[i], points[i + 2], points[i + 4] = s, e, w
    return [Landmark(x, y, visibility) for x, y in points]


def move(*poses, frames_each=8):
    """Smoothly pass through poses (each a (shoulder, elbow) pair, or a full
    pose() list to hold). Returns a list of landmark lists"""
    out = []
    for a, b in zip(poses, poses[1:]):
        if isinstance(a, list) or isinstance(b, list):
            out += [a if isinstance(a, list) else pose(a)] * frames_each
            continue
        for k in range(frames_each):
            f = k / frames_each
            out.append(pose((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)))
    last = poses[-1]
    out += [last if isinstance(last, list) else pose(last)] * frames_each
    return out


def reps(top, n, bottom=HANG):
    """n reps from bottom to top (with a short hold) and back"""
    out = move(bottom, bottom)
    for _ in range(n):
        out += move(bottom, top, top, bottom)
    return out


def still(seconds, landmarks=None):
    """Stand still (arms hanging) or, with landmarks=False, leave the frame"""
    if landmarks is False:
        return [None] * int(seconds * FPS)
    return [landmarks or pose(HANG)] * int(seconds * FPS)


def run(engine, *segments, start=0.0):
    """Feed segments of frames into the engine at 30 fps. Returns the time after
    the last frame"""
    t = start
    for segment in segments:
        for landmarks in segment:
            engine.step(landmarks, SIZE, SIZE, t)
            t += 1 / FPS
    return t
