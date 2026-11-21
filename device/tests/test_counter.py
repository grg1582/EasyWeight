from easyweight.counter import ArmCounter, Workout


def feed(counter, angles, **kw):
    return sum(counter.update(a, **kw) for a in angles)


def curl_counter():
    return ArmCounter("test curl", down_angle=150, up_angle=50)


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
    c = ArmCounter("test raise", down_angle=30, up_angle=75)
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
