import pytest

from easyweight.counter import RepCounter, Workout, smoothing_factor


def feed(counter, angles, **kw):
    return sum(counter.update(a, **kw) for a in angles)


def curl_counter():
    return RepCounter("test curl", down_angle=150, up_angle=50)


def test_curl_counts_one_rep_per_cycle():
    c = curl_counter()
    cycle = [170] * 5 + [30] * 5
    assert feed(c, cycle * 3) == 3
    assert c.reps == 3


def test_must_start_from_down():
    c = curl_counter()
    assert feed(c, [30] * 10) == 0  # already curled when first seen
    assert feed(c, [170] * 10 + [30] * 10) == 1


def test_half_rep_does_not_count():
    c = curl_counter()
    assert feed(c, ([170] * 5 + [80] * 5) * 3) == 0


def test_bad_form_does_not_count():
    c = curl_counter()
    assert feed(c, [170] * 5 + [30] * 5, form_ok=False) == 0


def test_raising_counter_goes_the_other_way():
    c = RepCounter("test raise", down_angle=30, up_angle=75)
    assert feed(c, ([10] * 5 + [90] * 5) * 2) == 2


def test_lost_arm_keeps_state():
    c = curl_counter()
    feed(c, [170] * 5)
    assert c.update(None) is False
    assert c.visible is False
    assert feed(c, [30] * 5) == 1


def test_smoothing_ignores_a_one_frame_glitch():
    c = curl_counter()
    assert feed(c, [170] * 10 + [30] + [170] * 10) == 0


def test_progress():
    c = curl_counter()
    assert c.progress() == 0.0
    feed(c, [170] * 20)
    assert c.progress() == 0.0
    feed(c, [30] * 20)
    assert c.progress() == 1.0


def test_smoothing_reacts_as_fast_at_any_frame_rate():
    assert smoothing_factor(1 / 30) == pytest.approx(0.4)
    # One reading after two frames' time moves as far as two readings would
    two_steps = 1 - (1 - smoothing_factor(1 / 30)) ** 2
    assert smoothing_factor(2 / 30) == pytest.approx(two_steps)


def test_median_drops_a_one_frame_spike_completely():
    c = curl_counter()
    feed(c, [170] * 10)
    c.update(30)
    assert c.angle == pytest.approx(170)


def test_long_gap_starts_the_smoothing_over():
    c = curl_counter()
    for i in range(10):
        c.update(170, now=i / 30)
    c.update(None, now=10 / 30)
    c.update(100, now=10 / 30 + 1.0)  # out of sight for a second
    assert c.angle == pytest.approx(100)
    assert c.stage == "down"  # the rep under way isn't lost


def test_short_gap_keeps_smoothing():
    c = curl_counter()
    for i in range(10):
        c.update(170, now=i / 30)
    c.update(100, now=10 / 30 + 0.2)
    c.update(100, now=11 / 30 + 0.2)  # the median needs two to move
    assert 100 < c.angle < 170


def test_form_check_slip_is_remembered_with_the_rep():
    c = curl_counter()
    feed(c, [170] * 5)
    feed(c, [100] * 5, check_ok=False)
    assert feed(c, [30] * 5) == 1
    assert c.rep_clean is False
    feed(c, [170] * 5 + [30] * 5)
    assert c.rep_clean is True


def test_workout_switches_after_one_rep_only():
    w = Workout()
    curl, press = w.counters["curl"]["left"], w.counters["press"]["left"]
    curl.reps = 1
    assert w.add_rep(0.0, "curl", curl)
    press.reps = 1
    assert w.add_rep(1.0, "press", press)  # 1 curl was lifting the weights: now a press set
    assert w.exercise == "press"
    assert w.history == [{"exercise": "press", "set": 1, "reps": 1}]


def test_workout_never_switches_from_press_to_curl():
    w = Workout()
    curl, press = w.counters["curl"]["left"], w.counters["press"]["left"]
    press.reps = 1
    w.add_rep(0.0, "press", press)
    curl.reps = 1
    assert not w.add_rep(1.0, "curl", curl)  # lowering a press looks like a curl
    assert w.exercise == "press"
    assert curl.reps == 0


def test_whole_body_exercises_have_one_counter():
    w = Workout()
    assert set(w.counters["squat"]) == {"both"}
    assert set(w.counters["pushup"]) == {"both"}
    squat = w.counters["squat"]["both"]
    w.exercise = "squat"
    assert w.arms() == (squat, squat)


def test_a_squat_set_starts_on_the_second_squat():
    w = Workout()
    squat = w.counters["squat"]["both"]
    squat.reps = 1
    assert not w.add_rep(0.0, "squat", squat)  # maybe just sitting down
    assert squat.reps == 0
    assert w.history == []
    squat.reps = 1
    assert w.add_rep(3.0, "squat", squat)
    assert w.history == [{"exercise": "squat", "set": 1, "reps": 2}]
    squat.reps = 3
    assert w.add_rep(6.0, "squat", squat)  # then each squat counts
    assert w.history[-1]["reps"] == 3


def test_squats_too_far_apart_dont_start_a_set():
    w = Workout()
    squat = w.counters["squat"]["both"]
    squat.reps = 1
    w.add_rep(0.0, "squat", squat)
    squat.reps = 1
    assert not w.add_rep(20.0, "squat", squat)
    assert w.history == []
