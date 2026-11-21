"""Makes up realistic workouts, as the events a mirror would send.

Used for the demo account, and handy for trying the dashboard without a
camera. The events go through the same checks and the same ingest as real
ones, so the demo shows exactly what a real mirror would produce.

A workout is 2 or 3 exercises of 2 to 4 sets. Both arms count each rep, the
reps drop a little as you tire, a rep takes 2 to 3 seconds, and the rest
between sets is 45 seconds to 2 minutes. Over the weeks the reps creep up.
"""
import random
import uuid
from datetime import UTC, datetime, timedelta

# exercise: (usual reps per set, top of a rep: (best, worst))
EXERCISES = {
    "curl": (11, (32.0, 48.0)),    # elbow angle at the top, smaller = higher curl
    "raise": (12, (95.0, 78.0)),   # shoulder angle at the top
    "press": (8, (1.35, 1.05)),    # wrist height above the shoulder, in shoulder widths
}
SET_IDLE_SECONDS = 8      # the mirror ends a set this long after the last rep
MAX_REST_SECONDS = 180    # and the workout after this long without a set


def _event(type_: str, at: datetime, **data) -> dict:
    return {"id": str(uuid.uuid4()), "type": type_, "at": at.isoformat(), "data": data}


def workout_events(start: datetime, rng: random.Random, progress: float = 0.0) -> list[dict]:
    """The events of one workout starting at `start`. `progress` (0 to 1)
    is how far along the training is: a little more reps later on"""
    t = start
    workout_id = str(uuid.uuid4())
    events = [_event("workout_started", t, workout_id=workout_id)]
    exercises = rng.sample(list(EXERCISES), rng.choice([2, 2, 3]))
    for e, exercise in enumerate(exercises):
        if e:
            t += timedelta(seconds=rng.uniform(60, 150))  # moving to the next exercise
        usual, (best_top, worst_top) = EXERCISES[exercise]
        for number in range(1, rng.choice([2, 3, 3, 4]) + 1):
            if number > 1:
                t += timedelta(seconds=rng.uniform(45, 120))
            set_id = str(uuid.uuid4())
            events.append(_event("set_started", t, workout_id=workout_id, set_id=set_id,
                                 exercise=exercise, set_number=number))
            reps = max(3, round(usual + 2 * progress - (number - 1) * rng.uniform(0.5, 1.5)
                                + rng.gauss(0, 1)))
            # The weaker arm sometimes stops one rep early
            sides = {"left": reps, "right": reps - (rng.random() < 0.2)}
            for count in range(1, reps + 1):
                t += timedelta(seconds=rng.uniform(2.0, 3.2) + count * 0.04)  # slower when tired
                tired = count / reps
                for side, side_reps in sides.items():
                    if count > side_reps:
                        continue
                    top = best_top + (worst_top - best_top) * min(1, tired * rng.uniform(0.3, 1.1))
                    at = t + timedelta(seconds=0.25 if side == "right" else 0)
                    events.append(_event("rep", at, set_id=set_id, side=side, count=count,
                                         top=round(top, 3)))
            t += timedelta(seconds=SET_IDLE_SECONDS)
            events.append(_event("set_ended", t, set_id=set_id, reps=reps))
    t += timedelta(seconds=MAX_REST_SECONDS)
    events.append(_event("workout_ended", t, workout_id=workout_id))
    return events


def training_days(first: datetime, last: datetime, rng: random.Random) -> list[datetime]:
    """Workout start times between two dates: about 4 days a week, mostly in
    the evening, sometimes in the morning"""
    starts = []
    day = first.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= last:
        if rng.random() < 0.58:
            hour = rng.choice([7, 7, 17, 18, 18, 19, 20])
            start = day.replace(hour=hour, minute=rng.randrange(60), second=rng.randrange(60))
            if first <= start <= last:
                starts.append(start)
        day += timedelta(days=1)
    return starts


def history(first: datetime, last: datetime, seed: int | None = None) -> list[dict]:
    """All the events of the workouts between two dates, oldest first"""
    rng = random.Random(seed)
    span = max((last - first).total_seconds(), 1)
    events = []
    for start in training_days(first, last, rng):
        events += workout_events(start, rng, progress=(start - first).total_seconds() / span)
    return events


if __name__ == "__main__":  # print one workout, to see what a mirror sends
    import json

    print(json.dumps(workout_events(datetime.now(UTC), random.Random()), indent=2))
