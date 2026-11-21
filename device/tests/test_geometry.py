import pytest

from easyweight.geometry import (
    angle_at,
    elbow_angle,
    joint_height,
    mouth_distance,
    shoulder_angle,
)
from poses import CURLED, HANG, MOUTH, PRESS_TOP, RAISED, SIZE, pose


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


def test_angles_use_pixels_not_fractions():
    """In a wide frame the same normalized points make a different angle"""
    lm = pose((45, 170))
    assert shoulder_angle(lm, "left", 2000, 1000) != pytest.approx(
        shoulder_angle(lm, "left", 1000, 1000))
