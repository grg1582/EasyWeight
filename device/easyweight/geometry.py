"""Angles and distances measured from pose landmarks.

A landmark is anything with x and y (0-1, as a fraction of the frame) and
visibility (0-1 or None), such as a MediaPipe landmark or a recording.Landmark.
Positions are turned into pixels first, so angles aren't squashed by the
frame's shape.
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


def arm_points(landmarks, ids, width, height):
    """Pixel positions of these landmarks, or None if MediaPipe can't see one of
    them well"""
    points = []
    for i in ids:
        lm = landmarks[i]
        if lm.visibility is not None and lm.visibility < cfg.MIN_VISIBILITY:
            return None
        points.append((lm.x * width, lm.y * height))
    return points


def _pixel(landmarks, i, width, height):
    return landmarks[i].x * width, landmarks[i].y * height


def shoulder_width(landmarks, width, height):
    return math.dist(*(_pixel(landmarks, i, width, height) for i in cfg.SHOULDERS))


def elbow_angle(landmarks, side, width, height):
    """Elbow angle for one arm (about 180 = straight), or None if it can't be seen"""
    points = arm_points(landmarks, cfg.ARMS[side], width, height)
    return angle_at(*points) if points else None


def shoulder_angle(landmarks, side, width, height):
    """How far the upper arm is raised out to the side: 0 = hanging straight down,
    90 = level with the shoulder. Measured from straight down rather than from the
    hip, so it works when the camera doesn't see the hips"""
    points = arm_points(landmarks, cfg.ARMS[side][:2], width, height)
    if not points:
        return None
    (sx, sy), elbow = points
    return angle_at((sx, sy + 100), (sx, sy), elbow)


def joint_height(landmarks, side, joint, width, height):
    """How far a joint of the arm (1 = elbow, 2 = wrist, as in ARMS) is above the
    shoulder, in shoulder widths (negative = below it). The press uses the wrist
    height rather than an angle, because with the weights held in front the
    wrist is above the shoulder at the bottom too"""
    points = arm_points(landmarks, (cfg.ARMS[side][0], cfg.ARMS[side][joint]), width, height)
    if not points:
        return None
    shoulders = shoulder_width(landmarks, width, height)
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
    mouth_l, mouth_r = (_pixel(landmarks, i, width, height) for i in cfg.MOUTH)
    mouth = ((mouth_l[0] + mouth_r[0]) / 2, (mouth_l[1] + mouth_r[1]) / 2)
    shoulders = shoulder_width(landmarks, width, height)
    if shoulders == 0:
        return None
    return math.dist(_pixel(landmarks, cfg.ARMS[side][2], width, height), mouth) / shoulders
