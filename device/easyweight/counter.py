"""Rep and set logic. Pure Python: it takes numbers and returns numbers, so it
can be tested without a camera or the pose model."""
import logging
import math

from . import config as cfg

log = logging.getLogger(__name__)


class ArmCounter:
    """One arm doing one exercise: the angle goes past down_angle, then past
    up_angle = 1 rep. For a curl the elbow angle gets smaller on the way up, for
    a lateral raise the shoulder angle gets bigger. For an overhead press the
    "angle" is the wrist height, which also gets bigger"""

    def __init__(self, name, down_angle, up_angle, measure="angle"):
        self.name = name
        self.measure = measure  # what the angle is, for the printout
        self.down_angle, self.up_angle = down_angle, up_angle
        self.sign = 1 if down_angle > up_angle else -1  # 1 = the angle shrinks on the way up
        self.reps = 0
        self.angle = None      # smoothed angle
        self.stage = None      # "down" or "up"
        self.visible = False
        self.mouth = None      # wrist to mouth distance right now
        self.closest = math.inf  # closest the wrist came to the mouth since the arm was down
        self.top = None        # furthest up the angle got since the arm was down
        # Highest the wrist and elbow got since the arm was down (joint_height).
        # Only printed for now, to find what tells a curl from touching the face
        self.wrist_top = self.elbow_top = -math.inf

    def update(self, raw_angle, mouth=None, form_ok=True, wrist=None, elbow=None):
        """Feed one reading (or None), the mouth_distance, whether the arm's form
        fits this exercise, and the wrist and elbow joint_height. Returns True
        when this reading completes a rep"""
        self.visible = raw_angle is not None
        self.mouth = mouth
        if raw_angle is None:
            return False
        if mouth is not None:
            self.closest = min(self.closest, mouth)
        if wrist is not None:
            self.wrist_top = max(self.wrist_top, wrist)
        if elbow is not None:
            self.elbow_top = max(self.elbow_top, elbow)
        if self.angle is None:
            self.angle = raw_angle
        else:
            self.angle += cfg.SMOOTHING * (raw_angle - self.angle)
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
            self.wrist_top = self.elbow_top = -math.inf
        elif self.sign * (self.angle - self.up_angle) < 0 and self.stage == "down" and form_ok:
            self.stage = "up"
            self.reps += 1
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
    touching the face doesn't count

    history lists every set since the program started, as dicts with
    exercise, set and reps. reset() doesn't clear it"""

    def __init__(self):
        self.counters = {
            "curl": {side: ArmCounter(f"{side} arm curl", cfg.CURL_DOWN_ANGLE, cfg.CURL_UP_ANGLE)
                     for side in cfg.ARMS},
            "raise": {side: ArmCounter(f"{side} arm raise", cfg.RAISE_DOWN_ANGLE,
                                       cfg.RAISE_UP_ANGLE)
                      for side in cfg.ARMS},
            "press": {side: ArmCounter(f"{side} arm press", cfg.PRESS_DOWN_HEIGHT,
                                       cfg.PRESS_UP_HEIGHT, measure="height")
                      for side in cfg.ARMS},
        }
        self.history = []
        self.reset()

    def arms(self):
        """The (left, right) counters to show: the set's exercise, or before the
        first rep, whichever exercise the arms are further into"""
        if self.exercise:
            pair = self.counters[self.exercise]
        else:
            pair = max(self.counters.values(),
                       key=lambda p: max(c.progress() for c in p.values()))
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

    def start_set(self, exercise, counter, now, replace=False):
        """counter's rep is the first rep of a set of exercise. Switching exercise
        starts its sets from 1. replace=True when this set takes the place of a
        1 rep set that turned out to be another exercise"""
        self.set = self.prev_set + 1 if exercise == self.prev_exercise else 1
        self.exercise = exercise
        self.clear_reps()
        counter.reps = 1
        self.last_rep = now
        self.pending = None
        entry = {"exercise": exercise, "set": self.set, "reps": 1}
        if replace and self.history:
            self.history[-1] = entry
        else:
            self.history.append(entry)
        log.info("Set %d: %s", self.set, cfg.EXERCISES[exercise].lower())

    def next_set(self, exercise, counter, now):
        """After a rest: counter's rep starts the next set"""
        self.prev_exercise, self.prev_set = self.exercise, self.set
        self.start_set(exercise, counter, now)

    def add_rep(self, now, exercise, counter):
        """Call after counter completed a rep of exercise. Returns True if it counts
        right away. A curl during rest is held back until check_pending knows it
        isn't drinking (a raise or a press can't be drinking)"""
        if self.resting(now):
            if exercise == "curl":
                counter.reps -= 1
                if self.pending is None:
                    self.pending = counter
                return False
            self.next_set(exercise, counter, now)
            return True
        if self.exercise is None:
            self.start_set(exercise, counter, now)
            return True
        if exercise == self.exercise:
            self.last_rep = now
            self.history[-1]["reps"] = self.set_reps()
            return True
        if self.set_reps() < 2 and not (self.exercise == "press" and exercise == "curl"):
            # One rep isn't enough to be sure: the first "curl" is often picking
            # up the weights or lifting them to the shoulders for a press. But
            # never from press to curl: lowering a press looks like a curl, so
            # the set would flip back and forth and stay at 1 rep
            self.start_set(exercise, counter, now, replace=True)
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
            self.pending = None
            return False
        # Straight again without reaching the mouth. Checked after the line above
        # every frame, so a lift that came near the mouth never gets here
        if counter.stage == "down":
            log.info("Lift during rest: wrist stayed %s+ from the mouth -> not drinking",
                     cfg.DRINK_DISTANCE)
            self.next_set("curl", counter, now)
            return True
        return False

    def reset(self):
        self.clear_reps()
        self.exercise = None   # "curl", "raise" or "press", None before the first rep
        self.set = 1
        self.prev_exercise, self.prev_set = None, 0  # the set before this one
        self.last_rep = None   # time of the latest rep, None before the first one
        self.pending = None    # counter of a curl during rest that might be drinking
