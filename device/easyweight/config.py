"""Tuning constants. Adjust these if reps are missed or counted when they
shouldn't be. The terminal prints the top angle of every rep while running."""

CURL_DOWN_ANGLE = 150  # elbow angle that counts as "arm straight"
CURL_UP_ANGLE = 50     # elbow angle that counts as "fully curled"
RAISE_DOWN_ANGLE = 30  # shoulder angle (0 = arm hanging down, 90 = out level with
                       # the shoulder) that counts as "arm down" in a lateral raise
RAISE_UP_ANGLE = 75    # shoulder angle that counts as "arm raised"
RAISE_MIN_ELBOW = 120  # a lateral raise keeps the elbow at least this straight,
                       # so curls and drinking can't count as raises
RAISE_MAX_ANGLE = 140  # and stays below this shoulder angle, so an overhead press can't
PRESS_DOWN_HEIGHT = 0.5  # wrist height above the shoulder (in shoulder widths) that
                         # counts as "weights at the shoulders" in an overhead press
PRESS_UP_HEIGHT = 1.0    # wrist height above the shoulder that counts as "pressed overhead"
MIN_VISIBILITY = 0.5   # ignore an arm when MediaPipe isn't confident it can see it
SMOOTHING = 0.4        # 0-1: lower = steadier but slower to react
SET_IDLE_SECONDS = 8   # no new rep for this long = the set is over and rest starts
MAX_REST_SECONDS = 180  # resting longer than this resets the count
AWAY_RESET_SECONDS = 10  # reset the count after nobody has been seen this long
DRINK_DISTANCE = 0.52  # a lift during rest where the wrist comes closer to the mouth
                       # than this (in shoulder widths) is drinking, not a curl

# MediaPipe landmark numbers: shoulder, elbow, wrist (the person's own left/right)
ARMS = {"left": (11, 13, 15), "right": (12, 14, 16)}
SHOULDERS = (11, 12)
MOUTH = (9, 10)

EXERCISES = {"curl": "BICEP CURLS", "raise": "LATERAL RAISES", "press": "OVERHEAD PRESS"}
