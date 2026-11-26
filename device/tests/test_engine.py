"""Whole sessions of synthetic frames through the engine, checking the sets
and reps it finds, like a person would at the mirror."""
import pytest

from easyweight.engine import Engine
from easyweight.recording import Landmark
from poses import (
    CURLED,
    HALF_SQUAT,
    HANG,
    MOUTH,
    PRESS_BOTTOM,
    PRESS_TOP,
    RAISED,
    SQUAT_BOTTOM,
    body_reps,
    move,
    pose,
    pushups,
    reps,
    run,
    sideways,
    squat,
    squats,
    still,
    tween,
)


@pytest.fixture
def engine():
    return Engine()


def sets(engine):
    return [(s["exercise"], s["set"], s["reps"]) for s in engine.workout.history]


def drink():
    sip = pose(CURLED, left_wrist=MOUTH, right_wrist=MOUTH)
    return move(HANG, sip, HANG)


def test_curls(engine):
    run(engine, reps(CURLED, 10))
    assert sets(engine) == [("curl", 1, 10)]
    assert engine.workout.exercise == "curl"


def test_lateral_raises(engine):
    run(engine, reps(RAISED, 8))
    assert sets(engine) == [("raise", 1, 8)]


def test_overhead_press(engine):
    run(engine, reps(PRESS_TOP, 6, bottom=PRESS_BOTTOM))
    assert sets(engine) == [("press", 1, 6)]


def test_standing_still_counts_nothing(engine):
    run(engine, still(5))
    assert sets(engine) == []
    assert engine.workout.exercise is None


def test_rest_then_next_set(engine):
    t = run(engine, reps(CURLED, 5), still(9))
    assert engine.workout.resting(t)
    run(engine, reps(CURLED, 4), start=t)
    assert sets(engine) == [("curl", 1, 5), ("curl", 2, 4)]


def test_switching_exercise_after_rest_starts_from_set_1(engine):
    run(engine, reps(CURLED, 5), still(9), reps(RAISED, 3))
    assert sets(engine) == [("curl", 1, 5), ("raise", 1, 3)]


def test_drinking_during_rest_is_not_a_rep(engine):
    t = run(engine, reps(CURLED, 5), still(9), drink(), still(2))
    assert engine.workout.resting(t)
    assert sets(engine) == [("curl", 1, 5)]
    # a real curl after the drink still starts the next set
    run(engine, reps(CURLED, 3), start=t)
    assert sets(engine) == [("curl", 1, 5), ("curl", 2, 3)]


def test_lifting_weights_before_a_press_is_not_a_curl_set(engine):
    lift = move(HANG, CURLED, PRESS_BOTTOM)  # pick up the weights and bring them up
    run(engine, lift, reps(PRESS_TOP, 5, bottom=PRESS_BOTTOM))
    assert sets(engine) == [("press", 1, 5)]


def test_both_arms_count_separately(engine):
    one_arm = []
    for _ in range(4):
        one_arm += [pose(HANG)] * 8 + [pose(HANG, right=CURLED)] * 8
    run(engine, one_arm)
    left, right = engine.workout.arms()
    assert (left.reps, right.reps) == (0, 4)
    assert sets(engine) == [("curl", 1, 4)]


def test_nobody_seen_resets(engine):
    t = run(engine, reps(CURLED, 5), still(11, landmarks=False))
    assert engine.workout.exercise is None
    run(engine, reps(CURLED, 2), start=t)
    assert sets(engine)[-1] == ("curl", 1, 2)  # a new person starts at set 1


def test_short_absence_does_not_reset(engine):
    run(engine, reps(CURLED, 5), still(3, landmarks=False))
    assert engine.workout.exercise == "curl"


def test_long_rest_resets(engine):
    t = run(engine, reps(CURLED, 5), still(181))
    assert engine.workout.exercise is None
    assert not engine.workout.resting(t)


def test_curls_at_a_low_frame_rate(engine):
    run(engine, reps(CURLED, 10), fps=15)
    assert sets(engine) == [("curl", 1, 10)]


def test_visibility_hovering_around_the_line(engine):
    """Found again only above REGAIN_VISIBILITY, so it doesn't flicker"""
    engine.step(pose(HANG, visibility=0.65), 1000, 1000, 0.0)
    assert engine.visible[13]
    engine.step(pose(HANG, visibility=0.55), 1000, 1000, 0.1)
    assert engine.visible[13]  # still seen
    engine.step(pose(HANG, visibility=0.45), 1000, 1000, 0.2)
    assert not engine.visible[13]
    engine.step(pose(HANG, visibility=0.55), 1000, 1000, 0.3)
    assert not engine.visible[13]  # not back yet
    engine.step(pose(HANG, visibility=0.65), 1000, 1000, 0.4)
    assert engine.visible[13]


def test_press_standing_sideways(engine):
    """Turned side on, the shoulders are close together in the picture: heights
    are measured against the torso instead"""
    run(engine, [sideways(f) for f in reps(PRESS_TOP, 5, bottom=PRESS_BOTTOM)])
    assert sets(engine) == [("press", 1, 5)]


@pytest.mark.parametrize("view", ["front", "side"])
def test_squats(engine, view):
    run(engine, squats(8, view))
    assert sets(engine) == [("squat", 1, 8)]
    left, right = engine.workout.arms()
    assert left is right  # one count for the whole body


def test_half_squats_dont_count(engine):
    run(engine, squats(5, depth=HALF_SQUAT))
    assert sets(engine) == []


def test_squats_count_with_the_feet_out_of_view(engine):
    """A camera close by often cuts off the feet: the depth doesn't need them"""
    run(engine, squats(5, ankles=0.2))
    assert sets(engine) == [("squat", 1, 5)]


def test_pushups_count_with_the_feet_out_of_view(engine):
    def no_feet(frame):
        for i in (27, 28):
            frame[i] = Landmark(frame[i].x, frame[i].y, 0.2)
        return frame

    run(engine, [no_feet(f) for f in pushups(5)])
    assert sets(engine) == [("pushup", 1, 5)]


def test_pushups_that_stop_short_of_90_degrees_count(engine):
    """Seen from the side, a real push-up's bottom often reads 95-100°"""
    run(engine, pushups(5, depth=98))
    assert sets(engine) == [("pushup", 1, 5)]


def test_arms_out_during_squats_are_not_lateral_raises(engine):
    frames = body_reps(lambda b: squat(b, arms=(90 * b / SQUAT_BOTTOM, 170)), 0, SQUAT_BOTTOM, 6)
    run(engine, frames)
    assert sets(engine) == [("squat", 1, 6)]


def test_switching_from_curls_to_squats(engine):
    run(engine, reps(CURLED, 5), still(9), squats(4))
    assert sets(engine) == [("curl", 1, 5), ("squat", 1, 4)]


def test_sitting_down_during_rest_is_not_a_squat_set(engine):
    sit = tween(lambda b: squat(b), 0, SQUAT_BOTTOM) + [squat(SQUAT_BOTTOM)] * 90
    run(engine, reps(CURLED, 5), still(9), sit)
    assert sets(engine) == [("curl", 1, 5)]


def test_seated_curls(engine):
    sit = tween(lambda b: squat(b), 0, SQUAT_BOTTOM) + [squat(SQUAT_BOTTOM)] * 90
    curls = body_reps(lambda e: squat(SQUAT_BOTTOM, arms=(0, e)), 175, 30, 5, frames_each=8)
    run(engine, sit, curls)
    assert sets(engine) == [("curl", 1, 5)]


def test_pushups(engine):
    run(engine, pushups(10))
    assert sets(engine) == [("pushup", 1, 10)]


def test_pushups_with_sagging_hips_still_count(engine):
    run(engine, pushups(6, sag=0.1))
    assert sets(engine) == [("pushup", 1, 6)]
    assert engine.workout.counters["pushup"]["both"].rep_clean is False


def test_standing_curls_are_never_pushups(engine):
    run(engine, reps(CURLED, 6))
    assert sets(engine) == [("curl", 1, 6)]
    assert engine.workout.counters["pushup"]["both"].reps == 0


def test_far_side_is_ignored_when_it_disagrees(engine):
    """From the side, MediaPipe guesses where the far arm is, a little less
    surely: when the two arms disagree, the better seen one is used"""
    def guessed(f):
        return [Landmark(p.x + (0.12 if i == 14 else 0), p.y,
                         0.7 if i in (12, 14, 16) else p.visibility)
                for i, p in enumerate(f)]
    run(engine, [guessed(f) for f in pushups(3)])
    assert sets(engine) == [("pushup", 1, 3)]
