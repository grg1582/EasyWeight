"""Builds synthetic pose landmarks, so the counting logic can be tested without
a camera. The figure stands facing the camera in a 1000 x 1000 frame with its
shoulders 200 px apart, and each arm is posed by two angles:

    shoulder: 0 = hanging straight down, 90 = out level with the shoulder
    elbow:    180 = straight, smaller = more bent (the forearm bends upward)

A move is a list of (shoulder, elbow) poses the arms pass through, and frames()
turns moves into timed frames at 30 fps.

squat() and pushup() pose the whole body instead, by how far it is into the
rep, seen from the front or the side.
"""
import math

from easyweight.recording import Landmark

SIZE = 1000  # frame width and height in pixels
FPS = 30
SHOULDER = {"left": (0.6, 0.4), "right": (0.4, 0.4)}
HIP = {"left": (0.55, 0.65), "right": (0.45, 0.65)}
OUT = {"left": 1, "right": -1}  # which way "out to the side" is in the picture
MOUTH = (0.5, 0.3)
UPPER_ARM = FOREARM = 0.15
TORSO = 0.25  # shoulder to hip
THIGH = SHIN = 0.2  # about 0.8 of the torso, as in real people
FLOOR = 0.95  # where the ankles are
FAR_SIDE = 0.3  # visibility of the side turned away from the camera

HANG = (0, 175)          # arms hanging, almost straight
CURLED = (0, 30)         # top of a curl
RAISED = (90, 170)       # top of a lateral raise
PRESS_BOTTOM = (90, 150)  # weights at the shoulders
PRESS_TOP = (165, 175)    # pressed overhead

SQUAT_BOTTOM = 110  # knee bend (0 = standing) with the thighs about level
HALF_SQUAT = 85     # a bit over halfway down
PUSHUP_TOP = 175    # elbow angle with the arms straight
PUSHUP_BOTTOM = 70

INDEX = {"left": {"shoulder": 11, "elbow": 13, "wrist": 15, "hip": 23, "knee": 25, "ankle": 27},
         "right": {"shoulder": 12, "elbow": 14, "wrist": 16, "hip": 24, "knee": 26, "ankle": 28}}


def _rotate(v, degrees):
    a = math.radians(degrees)
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


def _add(p, v, k=1.0):
    return (p[0] + k * v[0], p[1] + k * v[1])


def arm(side, shoulder_angle, elbow_angle, wrist=None, shoulder=None):
    """(shoulder, elbow, wrist) positions for one arm. wrist overrides where the
    wrist goes, e.g. MOUTH for drinking. shoulder moves the shoulder"""
    sx, sy = shoulder or SHOULDER[side]
    out = OUT[side]
    a = math.radians(shoulder_angle)
    upper = (out * math.sin(a), math.cos(a))
    elbow = (sx + UPPER_ARM * upper[0], sy + UPPER_ARM * upper[1])
    if wrist is None:
        fore = _rotate(upper, -out * (180 - elbow_angle))
        wrist = (elbow[0] + FOREARM * fore[0], elbow[1] + FOREARM * fore[1])
    return (sx, sy), elbow, wrist


def standing_legs(side):
    """(hip, knee, ankle) standing straight"""
    hx, hy = HIP[side]
    return (hx, hy), (hx, hy + THIGH), (hx, hy + THIGH + SHIN)


def figure(points, visibility=0.99, far=None):
    """33 landmarks from {"left": {"shoulder": (x, y), ...}, "right": ...,
    "mouth": (x, y)}. far = "left" or "right" gives that side FAR_SIDE visibility"""
    out = [(0.5, 0.25)] * 33  # face and body points nobody measures
    vis = [visibility] * 33
    mx, my = points["mouth"]
    out[9], out[10] = (mx + 0.02, my), (mx - 0.02, my)
    for side in ("left", "right"):
        for name, p in points[side].items():
            out[INDEX[side][name]] = p
            if side == far:
                vis[INDEX[side][name]] = FAR_SIDE
    return [Landmark(x, y, v) for (x, y), v in zip(out, vis, strict=True)]


def pose(left=HANG, right=None, left_wrist=None, right_wrist=None, visibility=0.99):
    """33 landmarks standing, with both arms posed (right copies left unless given)"""
    right = left if right is None else right
    points = {"mouth": MOUTH}
    for side, (shoulder, elbow), wrist in (("left", left, left_wrist),
                                           ("right", right, right_wrist)):
        s, e, w = arm(side, shoulder, elbow, wrist)
        h, k, a = standing_legs(side)
        points[side] = {"shoulder": s, "elbow": e, "wrist": w, "hip": h, "knee": k, "ankle": a}
    return figure(points, visibility)


def squat(bend, view="front", arms=HANG, lean=None, visibility=0.99, ankles=None):
    """Squatting bend degrees at the knee (0 = standing, SQUAT_BOTTOM = thighs
    about level). The shins tilt forward a quarter of the bend, the thighs the
    rest, and the torso leans forward 0.4 of it unless lean says otherwise.
    From the front, things tilting toward the camera just get shorter in the
    picture. From the side the person faces left and their right side is
    turned away. ankles sets the ankles' visibility (feet out of the frame)"""
    shin_tilt, thigh_tilt = math.radians(0.25 * bend), math.radians(0.75 * bend)
    lean = math.radians(0.4 * bend if lean is None else lean)
    points = {}
    for side in ("left", "right"):
        if view == "front":
            ax = HIP[side][0]
            ankle = (ax, FLOOR)
            knee = (ax + OUT[side] * 0.03 * bend / SQUAT_BOTTOM, FLOOR - SHIN * math.cos(shin_tilt))
            hip = (ax, knee[1] - THIGH * math.cos(thigh_tilt))
            shoulder = (SHOULDER[side][0], hip[1] - TORSO * math.cos(lean))
        else:
            ankle = (0.5 + (0.005 if side == "right" else 0), FLOOR)
            knee = _add(ankle, (-math.sin(shin_tilt), -math.cos(shin_tilt)), SHIN)
            hip = _add(knee, (math.sin(thigh_tilt), -math.cos(thigh_tilt)), THIGH)
            shoulder = _add(hip, (-math.sin(lean), -math.cos(lean)), TORSO)
        s, e, w = arm(side, *arms, shoulder=shoulder)
        points[side] = {"shoulder": s, "elbow": e, "wrist": w, "hip": hip, "knee": knee,
                        "ankle": ankle}
    top = min(points["left"]["shoulder"][1], points["right"]["shoulder"][1])
    points["mouth"] = ((points["left"]["shoulder"][0] + points["right"]["shoulder"][0]) / 2,
                       top - 0.1)
    landmarks = figure(points, visibility, far="right" if view == "side" else None)
    if ankles is not None:
        for i in (27, 28):
            landmarks[i] = Landmark(landmarks[i].x, landmarks[i].y, ankles)
    return landmarks


def pushup(elbow, sag=0.0):
    """A push-up seen from the side, the head to the left and the right side
    turned away: hands under the shoulders, elbow degrees at the elbows
    (PUSHUP_TOP = arms straight). sag lowers the hips (bad form)"""
    wrist = (0.3, 0.85)
    ankle = (0.95, 0.85)
    d = math.sqrt(UPPER_ARM ** 2 + FOREARM ** 2
                  - 2 * UPPER_ARM * FOREARM * math.cos(math.radians(elbow)))
    shoulder = (wrist[0], wrist[1] - d)
    # The elbow points back toward the feet
    elbow_at = (wrist[0] + math.sqrt(max(0.0, UPPER_ARM ** 2 - (d / 2) ** 2)), wrist[1] - d / 2)
    hip = _add(shoulder, (ankle[0] - shoulder[0], ankle[1] - shoulder[1]), 0.45)
    hip = (hip[0], hip[1] + sag)
    knee = ((hip[0] + ankle[0]) / 2, (hip[1] + ankle[1]) / 2)
    points = {"mouth": (shoulder[0] - 0.07, shoulder[1] - 0.02)}
    for side, dx in (("left", 0.0), ("right", 0.005)):
        points[side] = {name: (p[0] + dx, p[1]) for name, p in (
            ("shoulder", shoulder), ("elbow", elbow_at), ("wrist", wrist), ("hip", hip),
            ("knee", knee), ("ankle", ankle))}
    return figure(points, far="right")


def sideways(landmarks, squeeze=0.1):
    """The same pose turned almost side on to the camera: everything squeezed
    toward the middle, left to right"""
    return [Landmark(0.5 + (p.x - 0.5) * squeeze, p.y, p.visibility) for p in landmarks]


def move(*poses, frames_each=8):
    """Smoothly pass through poses (each a (shoulder, elbow) pair, or a full
    pose() list to hold). Returns a list of landmark lists"""
    out = []
    for a, b in zip(poses, poses[1:], strict=False):
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


def tween(make, *values, frames_each=8):
    """Like move() for any pose maker: make(value) gives the landmarks, and the
    value passes smoothly through values"""
    out = []
    for a, b in zip(values, values[1:], strict=False):
        out += [make(a + (b - a) * k / frames_each) for k in range(frames_each)]
    return out + [make(values[-1])] * frames_each


def body_reps(make, start, end, n, frames_each=12):
    """n reps of a whole body exercise: make(value) poses it, from start to end
    (with a short hold) and back"""
    out = tween(make, start, start, frames_each=frames_each)
    for _ in range(n):
        out += tween(make, start, end, end, start, frames_each=frames_each)
    return out


def squats(n, view="front", depth=SQUAT_BOTTOM, **kw):
    return body_reps(lambda b: squat(b, view, **kw), 0, depth, n)


def pushups(n, depth=PUSHUP_BOTTOM, sag=0.0):
    return body_reps(lambda e: pushup(e, sag), PUSHUP_TOP, depth, n)


def still(seconds, landmarks=None):
    """Stand still (arms hanging) or, with landmarks=False, leave the frame"""
    if landmarks is False:
        return [None] * int(seconds * FPS)
    return [landmarks or pose(HANG)] * int(seconds * FPS)


def run(engine, *segments, start=0.0, fps=FPS):
    """Feed segments of frames into the engine at 30 fps (or fps). Returns the
    time after the last frame"""
    t = start
    for segment in segments:
        for landmarks in segment:
            engine.step(landmarks, SIZE, SIZE, t)
            t += 1 / fps
    return t
