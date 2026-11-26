"""Feeds one video frame's pose landmarks into a Workout. Pure Python, so the
live app, the replay tool and the tests all count reps the same way.

Every exercise in exercises.py is watched all the time, on each side it
counts. What decides which one a set is happens in the Workout."""
from . import config as cfg
from .counter import Workout
from .exercises import EXERCISES, sides_of
from .geometry import joint_height, measure, measure_ids, mouth_distance, visibility

# The order counters are fed in a frame: arm by arm, then the whole body ones
ORDER = ([(e, side) for side in cfg.SIDES for e in EXERCISES if sides_of(e) == cfg.SIDES]
         + [(e, "both") for e in EXERCISES if sides_of(e) == ("both",)])


def _passes(value, condition, unseen):
    """Whether a reading meets {"min": n} / {"max": n}. unseen when it's None"""
    if value is None:
        return unseen
    return condition.get("min", -float("inf")) <= value <= condition.get("max", float("inf"))


class Engine:
    def __init__(self):
        self.workout = Workout()
        self.last_seen = None  # time someone was last in front of the mirror
        self.visible = []      # per landmark: seen well enough, with hysteresis

    def _see(self, landmarks):
        """A landmark is lost below MIN_VISIBILITY and found again only at
        REGAIN_VISIBILITY, so one hovering around the line doesn't come and go"""
        if not landmarks:
            self.visible = []
            return
        before = self.visible or [False] * len(landmarks)
        self.visible = [
            lm.visibility is None or lm.visibility >= cfg.REGAIN_VISIBILITY
            or (was and lm.visibility >= cfg.MIN_VISIBILITY)
            for lm, was in zip(landmarks, before, strict=True)
        ]

    def _read(self, landmarks, spec, sides, width, height, agree=None):
        """A measure on the given sides. With two: the average when they're within
        agree of each other, otherwise the better seen side"""
        values = []
        for side in sides:
            value = measure(landmarks, spec, side, width, height, self.visible)
            if value is not None:
                values.append((value, visibility(landmarks, measure_ids(spec, side))))
        if not values:
            return None
        if len(values) == 2 and agree is not None and abs(values[0][0] - values[1][0]) <= agree:
            return (values[0][0] + values[1][0]) / 2
        return max(values, key=lambda v: v[1])[0]

    def _blocked(self, now):
        """The exercises that don't count now, because a squat is under way"""
        blocked = set()
        for exercise, spec in EXERCISES.items():
            for counter in self.workout.counters[exercise].values():
                if not (spec["blocks"] and counter.visible and counter.progress() > 0):
                    continue
                just_done = counter.rep_at is not None and \
                    now - counter.rep_at < cfg.BLOCK_AFTER_REP_SECONDS
                if counter.stage == "down" or just_done:
                    blocked.update(spec["blocks"])
        return blocked

    def step(self, landmarks, width, height, now):
        """Process one frame. landmarks is the list of 33 pose landmarks, or None
        when nobody is seen. width and height are the frame's size in pixels, now
        is the time in seconds. Returns True when a rep was counted"""
        workout = self.workout
        if self.last_seen is None:
            self.last_seen = now
        self._see(landmarks)
        counted = False
        blocked = self._blocked(now)

        for exercise, side in ORDER:
            spec = EXERCISES[exercise]
            counter = workout.counters[exercise][side]
            if not landmarks:
                counter.update(None, now=now)
                continue
            sides = cfg.SIDES if side == "both" else (side,)
            reading = self._read(landmarks, spec["measure"], sides, width, height, spec["agree"])
            form_ok = exercise not in blocked and all(
                _passes(self._read(landmarks, f["measure"], sides, width, height), f,
                        unseen=f.get("unseen", False))
                for f in spec["form"])
            check = spec["check"]
            check_ok = check is None or _passes(
                self._read(landmarks, check["measure"], sides, width, height), check, unseen=True)
            mouth = wrist = elbow = None
            if side != "both" and reading is not None:
                mouth = mouth_distance(landmarks, side, width, height, self.visible)
                wrist = joint_height(landmarks, side, 2, width, height, self.visible)
                elbow = joint_height(landmarks, side, 1, width, height, self.visible)
            if (counter.update(reading, mouth, form_ok, wrist, elbow, now=now, check_ok=check_ok)
                    and workout.add_rep(now, exercise, counter)):
                counted = True
        if workout.check_pending(now):
            counted = True

        # Nobody in front of the mirror for a while, or a rest that went on too
        # long: start fresh
        if landmarks:
            self.last_seen = now
        elif now - self.last_seen > cfg.AWAY_RESET_SECONDS:
            workout.reset()
        if workout.resting(now) and workout.rest_time(now) > cfg.MAX_REST_SECONDS:
            workout.reset()
        return counted

    def reset(self):
        self.workout.reset()
