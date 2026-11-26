"""Turns what the Workout does into events for the backend.

It watches the Workout after every frame and compares it with the last frame,
so the counting logic doesn't need to know the backend exists:

    workout_started   the first set after a reset
    set_started       a new set, or the same set_id again when a 1 rep set
                      turns out to be another exercise
    rep               one arm (side left or right) or the whole body (side
                      both, for squats and push-ups) finished a rep
    set_ended         rest started, or the workout reset in the middle of a set
    workout_ended     the workout reset (person left, or rested too long)

Pure Python: the events are plain dicts, ready to be sent as JSON.
"""
import time
import uuid
from datetime import datetime, timezone


def wall_clock():
    """A function turning time.perf_counter() readings (what the app passes as
    `now`) into real dates. perf_counter is steady but has no date"""
    offset = time.time() - time.perf_counter()
    return lambda now: datetime.fromtimestamp(offset + now, timezone.utc)


class Reporter:
    def __init__(self, clock=None):
        # clock(now) -> datetime with a time zone. By default `now` is taken to
        # be seconds since 1970 (what the tests and replays use)
        self.clock = clock or (lambda now: datetime.fromtimestamp(now, timezone.utc))
        self.workout_id = None
        self.set_id = None
        self._entry = None          # the history entry of the current set
        self._history_len = 0
        self._side_reps = {}        # reps already reported, per side
        self._set_open = False      # set_ended not sent yet
        self._last_reps = 0

    def observe(self, workout, now):
        """Call after every Engine.step. Returns the new events (often none)"""
        events = []
        at = self.clock(now).isoformat()

        def emit(type_, **data):
            events.append({"id": str(uuid.uuid4()), "type": type_, "at": at, "data": data})

        history = workout.history
        if workout.exercise is None:  # reset, or nothing has happened yet
            if self.workout_id is not None:
                if self._set_open:
                    emit("set_ended", set_id=self.set_id, reps=self._last_reps)
                emit("workout_ended", workout_id=self.workout_id)
                self.workout_id = self.set_id = None
                self._set_open = False
            self._history_len = len(history)
            return events

        new_set = len(history) > self._history_len
        if new_set or history[-1] is not self._entry:
            if self.workout_id is None:
                self.workout_id = str(uuid.uuid4())
                emit("workout_started", workout_id=self.workout_id)
            if new_set or self.set_id is None:
                self.set_id = str(uuid.uuid4())
            entry = history[-1]
            emit("set_started", workout_id=self.workout_id, set_id=self.set_id,
                 exercise=entry["exercise"], set_number=entry["set"])
            self._entry = entry
            self._history_len = len(history)
            self._side_reps = dict.fromkeys(workout.counters[entry["exercise"]], 0)
            self._set_open = True

        for side, counter in workout.counters[workout.exercise].items():
            while self._side_reps[side] < counter.reps:
                self._side_reps[side] += 1
                top = None if counter.angle is None else round(counter.angle, 3)
                emit("rep", set_id=self.set_id, side=side, count=self._side_reps[side], top=top)
        self._last_reps = workout.set_reps()

        if self._set_open and workout.resting(now):
            emit("set_ended", set_id=self.set_id, reps=self._last_reps)
            self._set_open = False
        return events
