"""The coach: feedback on partial and too fast reps, and on each set in the rest
after it. The same cases as the
browser's coach.test.ts"""
import pytest

from easyweight.coach import CUE_SECONDS, SLOW_TEXT, Coach
from easyweight.counter import Workout
from easyweight.engine import Engine
from easyweight.exercises import EXERCISES
from poses import FPS, HALF_SQUAT, SIZE, pushups, squats

REP = [160, 120, 80, 40, 80, 120, 160]
QUICK_REP = [170, 30, 30, 170, 170]  # held 3 frames each: half a second


def play(workout, coach, angles, start, hold=6):
    """Moves the left arm's elbow through these angles (160 = straight, 40 =
    curled), holding each for a few frames, as the engine would"""
    t = start
    counter = workout.counters["curl"]["left"]
    for angle in angles:
        for _ in range(hold):
            if counter.update(angle):
                workout.add_rep(t, "curl", counter)
            workout.check_pending(t)
            coach.observe(workout, t)
            t += 1 / FPS
    return t


def test_full_reps_at_a_steady_pace_get_no_feedback():
    workout, coach = Workout(), Coach()
    play(workout, coach, REP * 3, 0, hold=8)
    assert workout.set_reps() == 3
    assert coach.cue is None


def test_a_rep_that_stopped_halfway():
    workout, coach = Workout(), Coach()
    t = play(workout, coach, REP, 0, hold=8)
    t = play(workout, coach, [160, 120, 90, 90, 120, 160], t, hold=8)
    assert workout.set_reps() == 1  # not counted
    assert coach.text(t) == "Curl all the way up"
    assert coach.partial == 1
    assert coach.text(t + CUE_SECONDS + 0.1) is None


def test_a_small_wobble_is_not_a_partial_rep():
    workout, coach = Workout(), Coach()
    t = play(workout, coach, REP + [160, 140, 130, 140, 160], 0, hold=8)
    assert coach.text(t) is None


def test_reps_that_are_too_fast():
    workout, coach = Workout(), Coach()
    t = play(workout, coach, QUICK_REP * 2, 0, hold=3)
    assert workout.set_reps() == 2
    assert coach.text(t) == "Slow down: control the weight"
    assert coach.fast == 1


def test_each_set_starts_over_and_the_rest_is_quiet():
    workout, coach = Workout(), Coach()
    t = play(workout, coach, QUICK_REP * 2, 0, hold=3)
    assert coach.fast == 1
    t += 10  # a rest
    coach.observe(workout, t)
    assert workout.resting(t)
    t = play(workout, coach, [160, 120, 90, 120, 160], t, hold=8)  # not a rep yet
    assert coach.partial == 0
    play(workout, coach, REP, t, hold=8)
    assert workout.set == 2
    assert coach.fast == 0


def rest(workout, coach, t):
    t += 10
    coach.observe(workout, t)
    assert workout.resting(t)
    return t


def test_nothing_to_sum_up_before_the_first_rep():
    assert Coach().summary(Workout()) is None


def test_after_a_clean_set_the_rest_shows_a_tip():
    workout, coach = Workout(), Coach()
    rest(workout, coach, play(workout, coach, REP * 3, 0, hold=8))
    assert coach.summary(workout) == (
        "Clean set: 3 reps", "Tip: keep your elbows pinned to your sides")


def test_each_set_gets_a_different_tip():
    workout, coach = Workout(), Coach()
    t = rest(workout, coach, play(workout, coach, REP * 2, 0, hold=8))
    t = rest(workout, coach, play(workout, coach, REP * 2, t, hold=8))
    assert workout.set == 2
    assert coach.summary(workout) == (
        "Clean set: 2 reps", "Tip: no swinging, keep your back still")


def test_after_partial_reps_the_rest_asks_for_the_full_range():
    workout, coach = Workout(), Coach()
    t = play(workout, coach, REP, 0, hold=8)
    t = rest(workout, coach, play(workout, coach, [160, 120, 90, 90, 120, 160], t, hold=8))
    assert coach.summary(workout) == (
        "1 rep · 1 partial", "Next set: all the way up, all the way down")


def test_after_fast_reps_the_rest_asks_to_slow_down():
    workout, coach = Workout(), Coach()
    rest(workout, coach, play(workout, coach, QUICK_REP * 2, 0, hold=3))
    assert coach.summary(workout) == ("2 reps · 1 too fast", SLOW_TEXT)


def session(*segments):
    """Whole frames through the engine, with the coach watching. Returns the
    engine, the coach and the time after the last frame"""
    engine, coach = Engine(), Coach()
    t = 0.0
    for segment in segments:
        for landmarks in segment:
            engine.step(landmarks, SIZE, SIZE, t)
            coach.observe(engine.workout, t)
            t += 1 / FPS
    return engine, coach, t


def test_sagging_hips_in_pushups():
    engine, coach, t = session(pushups(4, sag=0.1))
    assert engine.workout.set_reps() == 4
    assert coach.form == 4
    assert coach.text(t - 1) == "Keep your body in a straight line"
    t = rest(engine.workout, coach, t)
    assert coach.summary(engine.workout) == (
        "4 reps · 4 off form", "Next set: squeeze your glutes, body straight")


def test_clean_pushups_get_a_tip():
    engine, coach, t = session(pushups(4))
    rest(engine.workout, coach, t)
    assert coach.summary(engine.workout) == (
        "Clean set: 4 reps", "Tip: elbows at 45°, not flared out")


def test_a_half_squat_during_a_set():
    engine, coach, t = session(squats(3), squats(1, depth=HALF_SQUAT)[12:])
    assert engine.workout.set_reps() == 3
    assert coach.partial == 1
    assert coach.text(t) == "Squat deeper: thighs to parallel"


def test_leaning_far_forward_in_squats():
    engine, coach, t = session(squats(3, "side", lean=58))
    assert engine.workout.set_reps() == 3
    assert coach.form == 2  # the first two squats start the set together: one cue
    assert coach.text(t - 1) == "Chest up"


@pytest.mark.parametrize("exercise", list(EXERCISES))
def test_every_exercise_has_its_texts(exercise):
    text = EXERCISES[exercise]["text"]
    assert text["partial"] and text["full_range"]
    assert len(text["tips"]) == 3
    # An exercise with a form check says something about it
    assert bool(EXERCISES[exercise]["check"]) == bool(text["form"]) == bool(text["form_advice"])
