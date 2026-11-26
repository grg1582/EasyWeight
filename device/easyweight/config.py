"""Tuning constants. Adjust these if reps are missed or counted when they
shouldn't be. The terminal prints the top angle of every rep while running.

The exercises themselves (what is measured, and where a rep starts and ends)
are in exercises.py. The browser has the same numbers (web/src/train/config.ts),
and the parity test fails if the two differ."""

CURL_DOWN_ANGLE = 150  # elbow angle that counts as "arm straight"
CURL_UP_ANGLE = 50     # elbow angle that counts as "fully curled"
RAISE_DOWN_ANGLE = 30  # shoulder angle (0 = arm hanging down, 90 = out level with
                       # the shoulder) that counts as "arm down" in a lateral raise
RAISE_UP_ANGLE = 75    # shoulder angle that counts as "arm raised"
RAISE_MIN_ELBOW = 120  # a lateral raise keeps the elbow at least this straight,
                       # so curls and drinking can't count as raises
RAISE_MAX_ANGLE = 140  # and stays below this shoulder angle, so an overhead press can't
PRESS_DOWN_HEIGHT = 0.5  # wrist height above the shoulder (in body widths) that
                         # counts as "weights at the shoulders" in an overhead press
PRESS_UP_HEIGHT = 1.0    # wrist height above the shoulder that counts as "pressed overhead"
SQUAT_DOWN_HEIGHT = 0.8   # hip height above the knee (in body widths) that counts as
                          # "standing" in a squat (about 1.1 standing straight, so knees
                          # that don't quite lock at the top still count)
SQUAT_UP_HEIGHT = 0.4     # and as "at the bottom" (0 = thighs level with the knees)
PUSHUP_DOWN_ANGLE = 145   # elbow angle that counts as "arms straight" in a push-up
PUSHUP_UP_ANGLE = 105     # elbow angle that counts as "at the bottom". Not 90: the
                          # smoothing takes a few degrees off a quick bottom, and seen
                          # from the side most people's elbows read 95-105 there

MIN_VISIBILITY = 0.5   # a landmark seen less surely than this is lost...
REGAIN_VISIBILITY = 0.6  # ...and only found again once seen this surely
SMOOTHING = 0.4        # 0-1 at 30 frames a second: lower = steadier but slower to react.
                       # At other frame rates it is adjusted to react just as fast
SMOOTHING_FPS = 30     # the frame rate SMOOTHING is for
MAX_GAP_SECONDS = 0.5  # a limb out of sight longer than this starts its smoothing over
SET_IDLE_SECONDS = 8   # no new rep for this long = the set is over and rest starts
MAX_REST_SECONDS = 180  # resting longer than this resets the count
AWAY_RESET_SECONDS = 10  # reset the count after nobody has been seen this long
DRINK_DISTANCE = 0.52  # a lift during rest where the wrist comes closer to the mouth
                       # than this (in body widths) is drinking, not a curl
UPRIGHT_MAX_TORSO = 45  # the arm exercises count only with the torso this close to
                        # upright (degrees from vertical), or when the hips aren't seen
SQUAT_MAX_TORSO = 60    # a squat may lean forward this much at the bottom
PUSHUP_MIN_TORSO = 50   # a push-up needs the torso at least this far from upright
                        # (lying down). Above UPRIGHT_MAX_TORSO, so a curl never is one
TORSO_WIDTH_RATIO = 0.75  # shoulder width is about this times the shoulder to hip
                          # length: the body width used when the person stands sideways
BLOCK_AFTER_REP_SECONDS = 2  # after a squat reaches the bottom, the arms don't count for
                             # this long (people hold their arms out while squatting)

# MediaPipe landmark numbers (the person's own left/right)
LANDMARKS = {
    "left": {"shoulder": 11, "elbow": 13, "wrist": 15, "hip": 23, "knee": 25, "ankle": 27},
    "right": {"shoulder": 12, "elbow": 14, "wrist": 16, "hip": 24, "knee": 26, "ankle": 28},
}
SIDES = ("left", "right")
ARMS = {side: tuple(LANDMARKS[side][j] for j in ("shoulder", "elbow", "wrist")) for side in SIDES}
SHOULDERS = (11, 12)
HIPS = (23, 24)
MOUTH = (9, 10)
