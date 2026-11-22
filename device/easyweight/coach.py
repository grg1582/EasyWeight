"""Feedback on how the reps are done, shown under the count: a rep that
stopped halfway, or reps done too fast to control the weight.

The coach only watches the Workout and never changes what is counted. The
browser has the same coach (web/src/train/coach.ts).
"""
import math

SIDES = ("left", "right")

# A lift that got this far (0 = down, 1 = a counted rep) and went back down
# without counting was a partial rep
PARTIAL_FROM = 0.5
DOWN = 0.05  # back down: the arm is this close to the start
FAST_REP_SECONDS = 0.9  # two reps of one arm closer together are too fast
CUE_SECONDS = 2.5  # how long a cue stays on screen

PARTIAL_TEXT = {
    "curl": "Curl all the way up",
    "raise": "Raise to shoulder height",
    "press": "Press all the way up",
}
FAST_TEXT = "Slow down: control the weight"


def cue_text(cue, exercise):
    return PARTIAL_TEXT[exercise] if cue == "partial" else FAST_TEXT


def _fresh():
    return {"peak": 0.0, "reps": 0, "last_rep": None}


class Coach:
    def __init__(self):
        self.arms = {side: _fresh() for side in SIDES}
        self.exercise = None
        self.set = 0
        self.cue = None
        self.cue_at = -math.inf
        self.partial = 0  # this set's partial reps
        self.fast = 0  # and too fast ones

    def observe(self, workout, now):
        """Call every frame, after the engine"""
        if (workout.exercise, workout.set) != (self.exercise, self.set):
            self.exercise, self.set = workout.exercise, workout.set
            self.arms = {side: _fresh() for side in SIDES}
            self.partial = self.fast = 0
        if not self.exercise or workout.resting(now):
            return
        for side in SIDES:
            counter = workout.counters[self.exercise][side]
            arm = self.arms[side]
            if not counter.visible:
                continue
            if counter.reps > arm["reps"]:
                if arm["last_rep"] is not None and now - arm["last_rep"] < FAST_REP_SECONDS:
                    self._say("fast", now)
                arm.update(reps=counter.reps, last_rep=now, peak=0.0)  # this lift counted
                continue
            progress = counter.progress()
            if progress <= DOWN:
                if PARTIAL_FROM <= arm["peak"] < 1:
                    self._say("partial", now)
                arm["peak"] = 0.0
            elif counter.stage == "down":
                arm["peak"] = max(arm["peak"], progress)

    def text(self, now):
        """The text to show now, or None"""
        if not self.cue or not self.exercise or now - self.cue_at > CUE_SECONDS:
            return None
        return cue_text(self.cue, self.exercise)

    def _say(self, cue, now):
        self.cue, self.cue_at = cue, now
        if cue == "partial":
            self.partial += 1
        else:
            self.fast += 1
