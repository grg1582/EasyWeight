"""Feedback on how the reps are done. During a set, a cue under the count when
a rep stopped halfway, its form slipped (exercises.py "check") or the reps are
too fast to control the weight. During the rest after it, how the set went and
one thing to do on the next one.

The coach only watches the Workout and never changes what is counted. The
browser has the same coach (web/src/train/coach.ts). Its texts for each
exercise are in exercises.py.
"""
import math

from .exercises import EXERCISES

# A lift that got this far (0 = down, 1 = a counted rep) and went back down
# without counting was a partial rep
PARTIAL_FROM = 0.5
DOWN = 0.05  # back down: the arm is this close to the start
FAST_REP_SECONDS = 0.9  # two reps of one arm closer together are too fast
CUE_SECONDS = 2.5  # how long a cue stays on screen

FAST_TEXT = "Slow down: control the weight"
SLOW_TEXT = "Next set: 2 seconds up, 2 seconds down"


def cue_text(cue, exercise):
    if cue == "fast":
        return FAST_TEXT
    return EXERCISES[exercise]["text"][cue]


def tip(exercise, set_number):
    """The form tip for after a clean set"""
    tips = EXERCISES[exercise]["text"]["tips"]
    return tips[(set_number - 1) % len(tips)]


def _fresh():
    return {"peak": 0.0, "reps": 0, "last_rep": None}


class Coach:
    def __init__(self):
        self.arms = {}
        self.exercise = None
        self.set = 0
        self.cue = None
        self.cue_at = -math.inf
        self.partial = 0  # this set's partial reps
        self.form = 0  # reps whose form slipped
        self.fast = 0  # and too fast ones

    def observe(self, workout, now):
        """Call every frame, after the engine"""
        if (workout.exercise, workout.set) != (self.exercise, self.set):
            self.exercise, self.set = workout.exercise, workout.set
            self.arms = {side: _fresh() for side in workout.counters.get(self.exercise, {})}
            self.partial = self.form = self.fast = 0
        if not self.exercise or workout.resting(now):
            return
        for side, arm in self.arms.items():
            counter = workout.counters[self.exercise][side]
            if not counter.visible:
                continue
            if counter.reps > arm["reps"]:
                if arm["last_rep"] is not None and now - arm["last_rep"] < FAST_REP_SECONDS:
                    self._say("fast", now)
                if not counter.rep_clean:
                    self._say("form", now)
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

    def summary(self, workout):
        """During the rest after a set: (how it went, what to do next), or None.
        The advice is about whatever happened most: partial reps, then form,
        then pace on a tie (the range matters most)"""
        if not self.exercise or self.set != workout.set:
            return None
        reps = workout.set_reps()
        parts = [f"{reps} rep" if reps == 1 else f"{reps} reps"]
        if self.partial:
            parts.append(f"{self.partial} partial")
        if self.form:
            parts.append(f"{self.form} off form")
        if self.fast:
            parts.append(f"{self.fast} too fast")
        text = EXERCISES[self.exercise]["text"]
        most = max(self.partial, self.form, self.fast)
        if not most:
            parts[0] = f"Clean set: {parts[0]}"
            advice = tip(self.exercise, self.set)
        elif self.partial == most:
            advice = text["full_range"]
        elif self.form == most:
            advice = text["form_advice"]
        else:
            advice = SLOW_TEXT
        return " · ".join(parts), advice

    def _say(self, cue, now):
        self.cue, self.cue_at = cue, now
        if cue == "partial":
            self.partial += 1
        elif cue == "form":
            self.form += 1
        else:
            self.fast += 1
