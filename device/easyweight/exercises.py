"""The exercises, as data. Adding one is a new entry here (and the same entry in
web/src/train/exercises.ts), not new counting code.

Each exercise says:

    label            the name on the mirror
    sides            "each": both arms counted separately (curls), "both": one
                     count for the whole body (squats)
    measure          what is measured each frame, one of:
                       {"kind": "angle", "points": [a, b, c]}  angle at b
                       {"kind": "from_vertical", "points": [a, b]}  how far the
                           line a->b is from hanging straight down
                       {"kind": "height", "points": [joint, ref]}  how far joint
                           is above ref, in body widths
                       {"kind": "torso"}  the torso's angle from upright
                     Points are names from config.LANDMARKS, on the counted side
    down, up         the measure passes down, then up = 1 rep (either can be the
                     bigger number)
    form             conditions for a rep to count: [{"measure", "min"/"max"}],
                     with "unseen": True when a measure that can't be seen passes
    check            a form check that doesn't stop the rep from counting, only
                     makes the coach say text["form"]: {"measure", "min"/"max"}
    agree            for "both": the two sides' readings are averaged when they're
                     this close, otherwise the better seen side is used
    could_be_drinking  a rep during rest is held back until it's clear the hand
                     didn't go to the mouth
    confirm_reps     a new set of this exercise starts only after this many reps,
                     so getting up from a bench isn't a set of squats
    not_after        a set of these exercises with 1 rep never turns into this one
                     (lowering a press looks like a curl)
    blocks           while a rep of this is under way (and just after it), these
                     exercises don't count
    text             what the coach says: partial rep, advice after partial reps,
                     form slip and advice after them, and tips after a clean set
"""
from . import config as cfg

ARM_EXERCISES = ["curl", "raise", "press"]
TORSO = {"kind": "torso"}
# The arm exercises count only standing (or when the hips aren't seen, as when
# the camera sees only the upper body)
UPRIGHT = {"measure": TORSO, "max": cfg.UPRIGHT_MAX_TORSO, "unseen": True}

EXERCISES = {
    "curl": {
        "label": "BICEP CURLS",
        "sides": "each",
        "measure": {"kind": "angle", "points": ["shoulder", "elbow", "wrist"]},
        "down": cfg.CURL_DOWN_ANGLE,
        "up": cfg.CURL_UP_ANGLE,
        "form": [UPRIGHT],
        "check": None,
        "agree": None,
        "could_be_drinking": True,
        "confirm_reps": 1,
        "not_after": ["press"],
        "blocks": [],
        "text": {
            "partial": "Curl all the way up",
            "full_range": "Next set: all the way up, all the way down",
            "form": None,
            "form_advice": None,
            "tips": [
                "Tip: keep your elbows pinned to your sides",
                "Tip: no swinging, keep your back still",
                "Tip: squeeze at the top, lower slowly",
            ],
        },
    },
    "raise": {
        "label": "LATERAL RAISES",
        "sides": "each",
        "measure": {"kind": "from_vertical", "points": ["shoulder", "elbow"]},
        "down": cfg.RAISE_DOWN_ANGLE,
        "up": cfg.RAISE_UP_ANGLE,
        # Upright, the elbow fairly straight, so a curl or a drink can't count as
        # a raise, and below RAISE_MAX_ANGLE, so a press can't either
        "form": [
            UPRIGHT,
            {"measure": {"kind": "angle", "points": ["shoulder", "elbow", "wrist"]},
             "min": cfg.RAISE_MIN_ELBOW},
            {"measure": {"kind": "from_vertical", "points": ["shoulder", "elbow"]},
             "max": cfg.RAISE_MAX_ANGLE},
        ],
        "check": None,
        "agree": None,
        "could_be_drinking": False,
        "confirm_reps": 1,
        "not_after": [],
        "blocks": [],
        "text": {
            "partial": "Raise to shoulder height",
            "full_range": "Next set: lift to shoulder height every rep",
            "form": None,
            "form_advice": None,
            "tips": [
                "Tip: lead with your elbows, not your hands",
                "Tip: stop at shoulder height",
                "Tip: keep a slight bend in your elbows",
            ],
        },
    },
    "press": {
        "label": "OVERHEAD PRESS",
        "sides": "each",
        # The wrist height rather than an angle: with the weights held in front,
        # the wrist is above the shoulder at the bottom too
        "measure": {"kind": "height", "points": ["wrist", "shoulder"]},
        "down": cfg.PRESS_DOWN_HEIGHT,
        "up": cfg.PRESS_UP_HEIGHT,
        "form": [UPRIGHT],
        "check": None,
        "agree": None,
        "could_be_drinking": False,
        "confirm_reps": 1,
        "not_after": [],
        "blocks": [],
        "text": {
            "partial": "Press all the way up",
            "full_range": "Next set: arms straight at the top, every rep",
            "form": None,
            "form_advice": None,
            "tips": [
                "Tip: brace your core, don't arch your back",
                "Tip: press straight up, biceps by your ears",
                "Tip: lower to chin height, no lower",
            ],
        },
    },
    "squat": {
        "label": "SQUATS",
        "sides": "both",
        # The hips' height above the knees, in body widths. From the front the
        # thighs point at the camera, so the knee angle hardly changes in the
        # picture, but this does, and it works from the side too. Body widths
        # rather than the shins: they need no ankles (often out of the frame),
        # and the shins get shorter in the picture as the knees come forward
        "measure": {"kind": "height", "points": ["hip", "knee"]},
        "down": cfg.SQUAT_DOWN_HEIGHT,
        "up": cfg.SQUAT_UP_HEIGHT,
        "form": [{"measure": TORSO, "max": cfg.SQUAT_MAX_TORSO, "unseen": True}],
        # Leaning far forward at the bottom (only visible from the side)
        "check": {"measure": TORSO, "max": 55},
        "agree": 0.3,
        "could_be_drinking": False,
        "confirm_reps": 2,
        "not_after": [],
        "blocks": ARM_EXERCISES,
        "text": {
            "partial": "Squat deeper: thighs to parallel",
            "full_range": "Next set: thighs to parallel, every rep",
            "form": "Chest up",
            "form_advice": "Next set: chest up, back straight",
            "tips": [
                "Tip: push your knees out over your toes",
                "Tip: keep your heels on the floor",
                "Tip: brace your core before you go down",
            ],
        },
    },
    "pushup": {
        "label": "PUSH-UPS",
        "sides": "both",
        "measure": {"kind": "angle", "points": ["shoulder", "elbow", "wrist"]},
        "down": cfg.PUSHUP_DOWN_ANGLE,
        "up": cfg.PUSHUP_UP_ANGLE,
        # Lying down: the torso far from upright. It needs only the shoulders
        # and hips, not the ankles, which are often out of the frame
        "form": [{"measure": TORSO, "min": cfg.PUSHUP_MIN_TORSO}],
        # Shoulders, hips and ankles in a line: sagging hips bend it
        "check": {"measure": {"kind": "angle", "points": ["shoulder", "hip", "ankle"]},
                  "min": 160},
        "agree": 25,
        "could_be_drinking": False,
        "confirm_reps": 1,
        "not_after": [],
        "blocks": [],
        "text": {
            "partial": "Go lower: elbows to 90°",
            "full_range": "Next set: chest to the floor, every rep",
            "form": "Keep your body in a straight line",
            "form_advice": "Next set: squeeze your glutes, body straight",
            "tips": [
                "Tip: elbows at 45°, not flared out",
                "Tip: squeeze your glutes the whole set",
                "Tip: chest to the floor, then lock out",
            ],
        },
    },
}


def sides_of(exercise):
    """The counters an exercise has: ("left", "right"), or ("both",)"""
    return cfg.SIDES if EXERCISES[exercise]["sides"] == "each" else ("both",)
