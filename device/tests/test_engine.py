"""Whole sessions of synthetic frames through the engine, checking the sets
and reps it finds, like a person would at the mirror."""
import pytest

from easyweight.engine import Engine
from poses import (
    CURLED,
    HANG,
    MOUTH,
    PRESS_BOTTOM,
    PRESS_TOP,
    RAISED,
    move,
    pose,
    reps,
    run,
    still,
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
