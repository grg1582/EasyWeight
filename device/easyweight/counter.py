"""Rep and set logic. Pure Python: it takes numbers and returns numbers, so it
can be tested without a camera or the pose model."""
import logging
import math

from . import config as cfg
from .exercises import EXERCISES, sides_of

log = logging.getLogger(__name__)


def smoothing_factor(dt):
    """How much of a new reading goes into the smoothed one, for a reading dt
    seconds after the last. SMOOTHING at SMOOTHING_FPS, and just as quick to
    react (in seconds) at other frame rates"""
    if dt is None:
        return cfg.SMOOTHING
    return 1 - (1 - cfg.SMOOTHING) ** (dt * cfg.SMOOTHING_FPS)


def median3(values):
    a, b, c = values
    return max(min(a, b), min(max(a, b), c))


class RepCounter:
    """One arm (or the whole body) doing one exercise: the reading goes past
    down_angle, then past up_angle = 1 rep. For a curl the elbow angle gets
    smaller on the way up, for a lateral raise the shoulder angle gets bigger.
    For an overhead press or a squat the "angle" is a height

    Each reading goes through a median of the last 3 (a single wrong frame is
    dropped completely), then smoothing that reacts as fast at any frame rate"""

    def __init__(self, name, down_angle, up_angle, measure="angle"):
        self.name = name
        self.measure = measure  # what the angle is, for the printout
        self.down_angle, self.up_angle = down_angle, up_angle
        self.sign = 1 if down_angle > up_angle else -1  # 1 = the angle shrinks on the way up
        self.reps = 0
        self.angle = None      # smoothed angle
        self.stage = None      # "down" or "up"
        self.visible = False
        self.form_ok = False   # whether the latest reading's form fit this exercise
        self.mouth = None      # wrist to mouth distance right now
        self.closest = math.inf  # closest the wrist came to the mouth since the arm was down
        self.top = None        # furthest up the angle got since the arm was down
        self.clean = True      # the form check held since the arm was down
        self.rep_clean = True  # and it held through the latest rep
        self.rep_at = None     # when the latest rep was reached
        self._recent = []      # the last raw readings, for the median
        self._last_seen = None  # time of the latest reading
        # Highest the wrist and elbow got since the arm was down (joint_height).
        # Only printed for now, to find what tells a curl from touching the face
        self.wrist_top = self.elbow_top = -math.inf

    def update(self, raw_angle, mouth=None, form_ok=True, wrist=None, elbow=None,
               now=None, check_ok=True):
        """Feed one reading (or None), the mouth_distance, whether the form fits
        this exercise, the wrist and elbow joint_height, the time in seconds,
        and whether the form check (exercises.py) holds. Returns True when this
        reading completes a rep"""
        self.visible = raw_angle is not None
        self.mouth = mouth
        if raw_angle is None:
            return False
        self.form_ok = form_ok
        dt = None
        if now is not None and self._last_seen is not None:
            dt = now - self._last_seen
            if dt > cfg.MAX_GAP_SECONDS:  # out of sight for a while: start over from here
                self.angle, self._recent, dt = None, [], None
        self._last_seen = now
        self._recent = (self._recent + [raw_angle])[-3:]
        reading = median3(self._recent) if len(self._recent) == 3 else raw_angle
        if mouth is not None:
            self.closest = min(self.closest, mouth)
        if wrist is not None:
            self.wrist_top = max(self.wrist_top, wrist)
        if elbow is not None:
            self.elbow_top = max(self.elbow_top, elbow)
        if self.angle is None:
            self.angle = reading
        else:
            self.angle += smoothing_factor(dt) * (reading - self.angle)
        if self.top is None or self.sign * (self.angle - self.top) < 0:
            self.top = self.angle
        if self.sign * (self.angle - self.down_angle) > 0:
            if self.stage == "up":  # a lift just ended. Printed to help with tuning
                top = f"{self.top:.0f}" if self.measure == "angle" else f"{self.top:.2f}"
                log.info("%s: top %s %s, wrist came %.2f from the mouth, "
                         "above shoulder: wrist up to %+.2f, elbow up to %+.2f",
                         self.name, self.measure, top, self.closest,
                         self.wrist_top, self.elbow_top)
            self.stage = "down"
            self.closest = math.inf
            self.top = None
            self.clean = True
            self.wrist_top = self.elbow_top = -math.inf
            return False
        if self.stage == "down" and not check_ok:
            self.clean = False
        if self.sign * (self.angle - self.up_angle) < 0 and self.stage == "down" and form_ok:
            self.stage = "up"
            self.reps += 1
            self.rep_clean = self.clean
            self.rep_at = now
            return True
        return False

    def progress(self):
        """How far through the rep the arm is: 0 = down, 1 = all the way up"""
        if self.angle is None:
            return 0.0
        done = (self.down_angle - self.angle) / (self.down_angle - self.up_angle)
        return min(1.0, max(0.0, done))


class Workout:
    """Splits the reps into sets and knows which exercise each set is. The first
    rep of a set decides the exercise, and only that exercise counts until the
    set ends. No new rep for SET_IDLE_SECONDS means resting, and the first rep
    after a rest starts the next set (which can be another exercise). A curl
    during rest is held back until the arm straightens, so drinking water or
    touching the face doesn't count. An exercise with confirm_reps 2 (squats)
    starts a set only on its second rep

    counters[exercise] has a counter for each side the exercise counts:
    "left" and "right", or just "both" (see exercises.py).

    history lists every set since the program started, as dicts with
    exercise, set and reps. reset() doesn't clear it"""

    def __init__(self):
        self.counters = {
            exercise: {
                side: RepCounter(f"{side} {exercise}", spec["down"], spec["up"],
                                 measure=spec["measure"]["kind"])
                for side in sides_of(exercise)
            }
            for exercise, spec in EXERCISES.items()
        }
        self.history = []
        self.reset()

    def arms(self):
        """The (left, right) counters to show: the set's exercise, or before the
        first rep, whichever exercise (with the right form) is further along. An
        exercise of the whole body gives its one counter twice"""
        if self.exercise:
            pair = self.counters[self.exercise]
        else:
            pair = max(self.counters.values(),
                       key=lambda p: max(c.progress() if c.form_ok else 0 for c in p.values()))
        if "both" in pair:
            return pair["both"], pair["both"]
        return pair["left"], pair["right"]

    def clear_reps(self):
        for pair in self.counters.values():
            for counter in pair.values():
                counter.reps = 0

    def set_reps(self):
        return max(c.reps for c in self.counters[self.exercise].values())

    def resting(self, now):
        return self.last_rep is not None and now - self.last_rep > cfg.SET_IDLE_SECONDS

    def rest_time(self, now):
        """Seconds since the person stopped, counted from their last rep"""
        return now - self.last_rep

    def start_set(self, exercise, counter, now, replace=False, reps=1):
        """counter's rep is the first rep of a set of exercise (or its reps, for
        an exercise that needs more than one to start). Switching exercise
        starts its sets from 1. replace=True when this set takes the place of a
        1 rep set that turned out to be another exercise"""
        self.set = self.prev_set + 1 if exercise == self.prev_exercise else 1
        self.exercise = exercise
        self.clear_reps()
        counter.reps = reps
        self.last_rep = now
        self.pending = self.pending_exercise = self.candidate = None
        entry = {"exercise": exercise, "set": self.set, "reps": reps}
        if replace and self.history:
            self.history[-1] = entry
        else:
            self.history.append(entry)
        log.info("Set %d: %s", self.set, EXERCISES[exercise]["label"].lower())

    def next_set(self, exercise, counter, now, reps=1):
        """After a rest: counter's rep starts the next set"""
        self.prev_exercise, self.prev_set = self.exercise, self.set
        self.start_set(exercise, counter, now, reps=reps)

    def _can_switch(self, exercise):
        """Whether a set of 1 rep can turn into a set of exercise"""
        return self.set_reps() < 2 and self.exercise not in EXERCISES[exercise]["not_after"]

    def _begin(self, exercise, counter, now, reps=1):
        """Start a set of exercise however fits now. False if it can't"""
        if self.resting(now):
            self.next_set(exercise, counter, now, reps)
        elif self.exercise is None:
            self.start_set(exercise, counter, now, reps=reps)
        elif self._can_switch(exercise):
            # One rep isn't enough to be sure: the first "curl" is often picking
            # up the weights or lifting them to the shoulders for a press
            self.start_set(exercise, counter, now, replace=True, reps=reps)
        else:
            return False
        return True

    def _confirm(self, exercise, counter, now):
        """A rep of an exercise that needs more than one rep to start a set.
        Returns True when this rep confirms the set"""
        counter.reps -= 1
        needed = EXERCISES[exercise]["confirm_reps"]
        c = self.candidate
        if (c is not None and c["counter"] is counter
                and now - c["at"] <= cfg.SET_IDLE_SECONDS):
            c["reps"] += 1
            c["at"] = now
        else:
            c = self.candidate = {"exercise": exercise, "counter": counter, "reps": 1, "at": now}
        if c["reps"] < needed:
            return False
        self.candidate = None
        return self._begin(exercise, counter, now, reps=c["reps"])

    def add_rep(self, now, exercise, counter):
        """Call after counter completed a rep of exercise. Returns True if it counts
        right away. A curl during rest is held back until check_pending knows it
        isn't drinking, and a squat outside a squat set until a second one"""
        spec = EXERCISES[exercise]
        starting = self.exercise != exercise or self.resting(now)
        if starting and spec["confirm_reps"] > 1:
            return self._confirm(exercise, counter, now)
        if self.resting(now):
            if spec["could_be_drinking"]:
                counter.reps -= 1
                if self.pending is None:
                    self.pending, self.pending_exercise = counter, exercise
                return False
            self.next_set(exercise, counter, now)
            return True
        if exercise == self.exercise:
            self.last_rep = now
            self.history[-1]["reps"] = self.set_reps()
            return True
        if self.exercise is None or self._can_switch(exercise):
            # Never from press to curl (not_after): lowering a press looks like
            # a curl, so the set would flip back and forth and stay at 1 rep
            self.start_set(exercise, counter, now, replace=self.exercise is not None)
            return True
        counter.reps -= 1  # not the exercise this set is doing
        return False

    def check_pending(self, now):
        """Call every frame. Returns True when a held back curl turned out to be a
        real rep and started the next set. There's no time limit: people often
        lift a bottle to the chest and pause before drinking"""
        counter = self.pending
        if counter is None:
            return False
        if counter.closest < cfg.DRINK_DISTANCE:
            log.info("Lift during rest: wrist came %.2f from the mouth "
                     "(drinking below %s) -> drinking, ignored",
                     counter.closest, cfg.DRINK_DISTANCE)
            self.pending = self.pending_exercise = None
            return False
        # Straight again without reaching the mouth. Checked after the line above
        # every frame, so a lift that came near the mouth never gets here
        if counter.stage == "down":
            log.info("Lift during rest: wrist stayed %s+ from the mouth -> not drinking",
                     cfg.DRINK_DISTANCE)
            self.next_set(self.pending_exercise, counter, now)
            return True
        return False

    def reset(self):
        self.clear_reps()
        self.exercise = None   # a key of EXERCISES, None before the first rep
        self.set = 1
        self.prev_exercise, self.prev_set = None, 0  # the set before this one
        self.last_rep = None   # time of the latest rep, None before the first one
        self.pending = None    # counter of a curl during rest that might be drinking
        self.pending_exercise = None
        self.candidate = None  # reps of an exercise that needs more than one to start a set
