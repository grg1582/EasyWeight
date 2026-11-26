"""Angles and distances measured from pose landmarks.

A landmark is anything with x and y (0-1, as a fraction of the frame) and
visibility (0-1 or None), such as a MediaPipe landmark or a recording.Landmark.
Positions are turned into pixels first, so angles aren't squashed by the
frame's shape.

Functions that check visibility take `visible`: a list saying for each
landmark whether it is seen well enough (the engine keeps it, so a landmark
flickering around the threshold doesn't come and go every frame). Without it,
a landmark is seen when its visibility is at least MIN_VISIBILITY.
"""
import math

from . import config as cfg


def angle_at(a, b, c):
    """Angle ABC in degrees, measured at point b"""
    v1 = (a[0] - b[0], a[1] - b[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return None
    cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def seen(landmarks, i, visible=None):
    if visible is not None:
        return visible[i]
    v = landmarks[i].visibility
    return v is None or v >= cfg.MIN_VISIBILITY


def visibility(landmarks, ids):
    """How surely MediaPipe sees the least visible of these (1 when unknown)"""
    return min(1.0 if landmarks[i].visibility is None else landmarks[i].visibility for i in ids)


def arm_points(landmarks, ids, width, height, visible=None):
    """Pixel positions of these landmarks, or None if MediaPipe can't see one of
    them well"""
    points = []
    for i in ids:
        if not seen(landmarks, i, visible):
            return None
        points.append(_pixel(landmarks, i, width, height))
    return points


def _pixel(landmarks, i, width, height):
    return landmarks[i].x * width, landmarks[i].y * height


def _middle(points):
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def shoulder_width(landmarks, width, height):
    return math.dist(*(_pixel(landmarks, i, width, height) for i in cfg.SHOULDERS))


def _torso_ends(landmarks, width, height, visible=None):
    """(middle of the shoulders, middle of the hips) in pixels, from the ones
    that are seen, or None"""
    shoulders = [_pixel(landmarks, i, width, height) for i in cfg.SHOULDERS
                 if seen(landmarks, i, visible)]
    hips = [_pixel(landmarks, i, width, height) for i in cfg.HIPS if seen(landmarks, i, visible)]
    if not shoulders or not hips:
        return None
    return _middle(shoulders), _middle(hips)


def body_width(landmarks, width, height, visible=None):
    """The length heights and distances are measured in. Usually the shoulder
    width, so it doesn't matter how far from the camera the person stands. But
    turned sideways the shoulders get close together in the picture, while the
    torso's length doesn't change, so when the hips are seen it's at least
    TORSO_WIDTH_RATIO times the torso"""
    shoulders = shoulder_width(landmarks, width, height)
    torso = _torso_ends(landmarks, width, height, visible)
    if torso:
        shoulders = max(shoulders, cfg.TORSO_WIDTH_RATIO * math.dist(*torso))
    return shoulders


def torso_angle(landmarks, width, height, visible=None):
    """How far the torso leans from upright: 0 = standing straight, 90 = lying
    down, None when the hips or shoulders can't be seen"""
    ends = _torso_ends(landmarks, width, height, visible)
    if not ends:
        return None
    (sx, sy), (hx, hy) = ends
    return angle_at((hx, hy - 100), (hx, hy), (sx, sy))


def measure_ids(measure, side):
    """The landmarks a measure looks at"""
    if measure["kind"] == "torso":
        return list(cfg.SHOULDERS + cfg.HIPS)
    return [cfg.LANDMARKS[side][n] for n in measure["points"]]


def measure(landmarks, spec, side, width, height, visible=None):
    """One measure (see exercises.py) of one side, or None if it can't be seen"""
    kind = spec["kind"]
    if kind == "torso":
        return torso_angle(landmarks, width, height, visible)
    points = arm_points(landmarks, measure_ids(spec, side), width, height, visible)
    if not points:
        return None
    if kind == "angle":
        return angle_at(*points[:3])
    if kind == "from_vertical":
        (ax, ay), b = points[:2]
        return angle_at((ax, ay + 100), (ax, ay), b)
    if kind == "height":
        (_, joint_y), (_, ref_y) = points[:2]
        unit = body_width(landmarks, width, height, visible)
        return (ref_y - joint_y) / unit if unit else None
    raise ValueError(f"unknown measure {kind}")


ELBOW = {"kind": "angle", "points": ["shoulder", "elbow", "wrist"]}
SHOULDER = {"kind": "from_vertical", "points": ["shoulder", "elbow"]}


def elbow_angle(landmarks, side, width, height, visible=None):
    """Elbow angle for one arm (about 180 = straight), or None if it can't be seen"""
    return measure(landmarks, ELBOW, side, width, height, visible)


def shoulder_angle(landmarks, side, width, height, visible=None):
    """How far the upper arm is raised out to the side: 0 = hanging straight down,
    90 = level with the shoulder. Measured from straight down rather than from the
    hip, so it works when the camera doesn't see the hips"""
    return measure(landmarks, SHOULDER, side, width, height, visible)


def joint_height(landmarks, side, joint, width, height, visible=None):
    """How far a joint of the arm (1 = elbow, 2 = wrist, as in ARMS) is above the
    shoulder, in body widths (negative = below it)"""
    name = ("shoulder", "elbow", "wrist")[joint]
    spec = {"kind": "height", "points": [name, "shoulder"]}
    return measure(landmarks, spec, side, width, height, visible)


def mouth_distance(landmarks, side, width, height, visible=None):
    """How far the wrist is from the mouth, in body widths (so it doesn't
    matter how far the person stands from the camera). Drinking brings the hand
    to the mouth, a curl stops near the shoulder. The face points aren't checked
    for visibility because a bottle often covers the mouth, and MediaPipe still
    places them well"""
    mouth_l, mouth_r = (_pixel(landmarks, i, width, height) for i in cfg.MOUTH)
    mouth = ((mouth_l[0] + mouth_r[0]) / 2, (mouth_l[1] + mouth_r[1]) / 2)
    scale = body_width(landmarks, width, height, visible)
    if scale == 0:
        return None
    return math.dist(_pixel(landmarks, cfg.ARMS[side][2], width, height), mouth) / scale
