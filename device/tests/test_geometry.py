import pytest

from easyweight import config as cfg
from easyweight.geometry import (
    angle_at,
    body_width,
    elbow_angle,
    joint_height,
    measure,
    mouth_distance,
    shoulder_angle,
    torso_angle,
)
from easyweight.recording import Landmark
from poses import (
    CURLED,
    HALF_SQUAT,
    HANG,
    MOUTH,
    PRESS_TOP,
    PUSHUP_BOTTOM,
    RAISED,
    SIZE,
    SQUAT_BOTTOM,
    pose,
    pushup,
    sideways,
    squat,
)


def test_angle_at():
    assert angle_at((0, 1), (0, 0), (1, 0)) == pytest.approx(90)
    assert angle_at((-1, 0), (0, 0), (1, 0)) == pytest.approx(180)
    assert angle_at((1, 0), (0, 0), (1, 0)) == pytest.approx(0)


def test_angle_at_zero_length_side():
    assert angle_at((0, 0), (0, 0), (1, 0)) is None


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("arm", [HANG, CURLED, RAISED, PRESS_TOP])
def test_arm_angles(side, arm):
    shoulder, elbow = arm
    lm = pose(arm)
    assert shoulder_angle(lm, side, SIZE, SIZE) == pytest.approx(shoulder, abs=0.5)
    assert elbow_angle(lm, side, SIZE, SIZE) == pytest.approx(elbow, abs=0.5)


def test_wrist_height_in_shoulder_widths():
    assert joint_height(pose(HANG), "left", 2, SIZE, SIZE) < 0  # below the shoulder
    assert joint_height(pose(PRESS_TOP), "left", 2, SIZE, SIZE) > 1  # well overhead


def test_mouth_distance():
    assert mouth_distance(pose(CURLED, left_wrist=MOUTH), "left", SIZE, SIZE) == pytest.approx(0)
    assert mouth_distance(pose(CURLED), "left", SIZE, SIZE) > 0.52  # a curl stops short


def test_hidden_arm_is_none():
    lm = pose(HANG, visibility=0.1)
    assert elbow_angle(lm, "left", SIZE, SIZE) is None
    assert shoulder_angle(lm, "left", SIZE, SIZE) is None
    assert joint_height(lm, "left", 2, SIZE, SIZE) is None


SQUAT_HEIGHT = {"kind": "height", "points": ["hip", "knee"]}


@pytest.mark.parametrize("view", ["front", "side"])
def test_squat_depth_in_body_widths(view):
    def depth(bend):
        return measure(squat(bend, view), SQUAT_HEIGHT, "left", SIZE, SIZE)

    assert depth(0) == pytest.approx(1, abs=0.1)
    assert depth(0) > cfg.SQUAT_DOWN_HEIGHT
    assert depth(SQUAT_BOTTOM) < cfg.SQUAT_UP_HEIGHT
    assert cfg.SQUAT_UP_HEIGHT < depth(HALF_SQUAT) < cfg.SQUAT_DOWN_HEIGHT


def test_squat_depth_without_the_ankles():
    """Feet out of the frame, as with a camera close by: the depth is still measured"""
    for bend in (0, SQUAT_BOTTOM):
        assert measure(squat(bend, ankles=0.2), SQUAT_HEIGHT, "left", SIZE, SIZE) == pytest.approx(
            measure(squat(bend), SQUAT_HEIGHT, "left", SIZE, SIZE))


def test_torso_angle():
    assert torso_angle(pose(HANG), SIZE, SIZE) == pytest.approx(0)
    assert torso_angle(pushup(PUSHUP_BOTTOM), SIZE, SIZE) > 65
    # Sagging hips tilt the torso toward upright, but it's still lying down
    assert torso_angle(pushup(175, sag=0.1), SIZE, SIZE) > cfg.PUSHUP_MIN_TORSO
    hips_hidden = pose(HANG)
    for i in (23, 24):
        hips_hidden[i] = Landmark(hips_hidden[i].x, hips_hidden[i].y, 0.1)
    assert torso_angle(hips_hidden, SIZE, SIZE) is None


def test_pushup_elbow_angle():
    elbow = {"kind": "angle", "points": ["shoulder", "elbow", "wrist"]}
    assert measure(pushup(90), elbow, "left", SIZE, SIZE) == pytest.approx(90)


def test_body_width_when_turned_sideways():
    """The shoulders look close together, but the torso keeps its length"""
    assert body_width(pose(HANG), SIZE, SIZE) == pytest.approx(200)
    assert body_width(sideways(pose(HANG)), SIZE, SIZE) == pytest.approx(0.75 * 250)


def test_angles_use_pixels_not_fractions():
    """In a wide frame the same normalized points make a different angle"""
    lm = pose((45, 170))
    assert shoulder_angle(lm, "left", 2000, 1000) != pytest.approx(
        shoulder_angle(lm, "left", 1000, 1000))
