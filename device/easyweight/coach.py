"""Feedback on how the reps are done. During a set, a cue under the count when
a rep stopped halfway or the reps are too fast to control the weight. During
the rest after it, how the set went and one thing to do on the next one.

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

# What to do on the next set, after partial or too fast reps
FULL_RANGE_TEXT = {
    "curl": "Next set: all the way up, all the way down",
    "raise": "Next set: lift to shoulder height every rep",
    "press": "Next set: arms straight at the top, every rep",
}
SLOW_TEXT = "Next set: 2 seconds up, 2 seconds down"

# After a clean set, a pointer on form for the next one, a different one each set
TIPS = {
    "curl": (
        "Tip: keep your elbows pinned to your sides",
        "Tip: no swinging, keep your back still",
        "Tip: squeeze at the top, lower slowly",
    ),
    "raise": (
        "Tip: lead with your elbows, not your hands",
        "Tip: stop at shoulder height",
        "Tip: keep a slight bend in your elbows",
    ),
    "press": (
        "Tip: brace your core, don't arch your back",
        "Tip: press straight up, biceps by your ears",
        "Tip: lower to chin height, no lower",
    ),
}


def cue_text(cue, exercise):
    return PARTIAL_TEXT[exercise] if cue == "partial" else FAST_TEXT


def tip(exercise, set_number):
    """The form tip for after a clean set"""
    tips = TIPS[exercise]
    return tips[(set_number - 1) % len(tips)]


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

    def summary(self, workout):
        """During the rest after a set: (how it went, what to do next), or None"""
        if not self.exercise or self.set != workout.set:
            return None
        reps = workout.set_reps()
        parts = [f"{reps} rep" if reps == 1 else f"{reps} reps"]
        if self.partial:
            parts.append(f"{self.partial} partial")
        if self.fast:
            parts.append(f"{self.fast} too fast")
        if self.partial >= self.fast and self.partial:
            advice = FULL_RANGE_TEXT[self.exercise]
        elif self.fast:
            advice = SLOW_TEXT
        else:
            parts[0] = f"Clean set: {parts[0]}"
            advice = tip(self.exercise, self.set)
        return " · ".join(parts), advice

    def _say(self, cue, now):
        self.cue, self.cue_at = cue, now
        if cue == "partial":
            self.partial += 1
        else:
            self.fast += 1
