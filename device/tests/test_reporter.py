"""The events the mirror sends, from whole synthetic sessions"""
from easyweight.engine import Engine
from easyweight.reporter import Reporter
from poses import CURLED, FPS, HANG, PRESS_BOTTOM, PRESS_TOP, RAISED, SIZE, move, reps, still


def session(*segments, reset_at_end=True):
    """Run segments through an Engine and a Reporter. Returns the events"""
    engine, reporter = Engine(), Reporter()
    events, t = [], 1_700_000_000.0  # a date in 2023, so the times are real dates
    for segment in segments:
        for landmarks in segment:
            engine.step(landmarks, SIZE, SIZE, t)
            events += reporter.observe(engine.workout, t)
            t += 1 / FPS
    if reset_at_end:
        engine.reset()
        events += reporter.observe(engine.workout, t)
    return events


def kinds(events):
    out = []
    for e in events:
        d = e["data"]
        if e["type"] == "set_started":
            out.append(("set_started", d["exercise"], d["set_number"]))
        elif e["type"] == "set_ended":
            out.append(("set_ended", d["reps"]))
        elif e["type"] != "rep":
            out.append((e["type"],))
    return out


def test_one_set():
    events = session(reps(CURLED, 5), still(9))
    assert kinds(events) == [("workout_started",), ("set_started", "curl", 1),
                             ("set_ended", 5), ("workout_ended",)]
    reps_ = [e["data"] for e in events if e["type"] == "rep"]
    # both arms curl, so each arm reports its own reps 1..5
    assert sorted((r["side"], r["count"]) for r in reps_) == sorted(
        [(side, n) for side in ("left", "right") for n in range(1, 6)])


def test_events_refer_to_each_other():
    events = session(reps(CURLED, 3), still(9))
    workout_id = events[0]["data"]["workout_id"]
    set_id = events[1]["data"]["set_id"]
    assert events[1]["data"]["workout_id"] == workout_id
    assert all(e["data"]["set_id"] == set_id for e in events if e["type"] in ("rep", "set_ended"))
    assert events[-1]["data"]["workout_id"] == workout_id
    assert len({e["id"] for e in events}) == len(events)  # every event has its own id


def test_times_are_real_dates_in_order():
    events = session(reps(CURLED, 2), still(9))
    times = [e["at"] for e in events]
    assert times == sorted(times)
    assert times[0].startswith("2023-11-14T") and times[0].endswith("+00:00")


def test_two_sets_and_a_switch_after_rest():
    events = session(reps(CURLED, 4), still(9), reps(CURLED, 3), still(9), reps(RAISED, 2))
    assert kinds(events) == [
        ("workout_started",),
        ("set_started", "curl", 1), ("set_ended", 4),
        ("set_started", "curl", 2), ("set_ended", 3),
        ("set_started", "raise", 1), ("set_ended", 2),
        ("workout_ended",),
    ]


def test_one_rep_set_that_turns_out_to_be_a_press():
    # Picking up the weights and bringing them up counts as 1 rep of something
    # else first (a curl, or here a raise) before the presses
    lift = move(HANG, CURLED, PRESS_BOTTOM)
    events = session(lift, reps(PRESS_TOP, 3, bottom=PRESS_BOTTOM))
    started = [e for e in events if e["type"] == "set_started"]
    assert len(started) >= 2
    assert started[0]["data"]["exercise"] != "press"
    assert started[-1]["data"]["exercise"] == "press"
    # the same set, so the backend changes its exercise instead of adding a set
    assert len({s["data"]["set_id"] for s in started}) == 1
    assert kinds(events)[-2:] == [("set_ended", 3), ("workout_ended",)]


def test_walking_away_mid_set_ends_set_and_workout():
    events = session(reps(CURLED, 3), still(11, landmarks=False), reset_at_end=False)
    assert kinds(events) == [("workout_started",), ("set_started", "curl", 1),
                             ("set_ended", 3), ("workout_ended",)]


def test_a_new_person_gets_a_new_workout():
    events = session(reps(CURLED, 2), still(11, landmarks=False), reps(CURLED, 2))
    started = [e["data"]["workout_id"] for e in events if e["type"] == "workout_started"]
    assert len(started) == 2 and started[0] != started[1]


def test_nothing_happens_nothing_is_sent():
    assert session(still(5)) == []
