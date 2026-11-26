# How the counting works

[MediaPipe Pose](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)
finds your shoulders, elbows, wrists, hips, knees and ankles in each frame, and
five exercises are measured from them:

| Exercise       | What's measured                                   | Start         | 1 rep when it reaches |
|----------------|---------------------------------------------------|---------------|-----------------------|
| Bicep curl     | At the elbow, each arm                            | above 150°    | below 50° (fully curled) |
| Lateral raise  | Upper arm vs straight down (shoulder), each arm   | below 30°     | above 75° (but below 140°), with the elbow fairly straight |
| Overhead press | Wrist height above the shoulder, in body widths, each arm | below 0.5 | above 1.0 (pressed overhead) |
| Squat          | Hip height above the knee, in body widths, the whole body | above 0.8 | below 0.4 (thighs about level) |
| Push-up        | At the elbow, the whole body                      | above 145°    | below 105°            |

Curls, raises and presses count each arm separately, and the big number shows
whichever arm has more reps. Squats and push-ups count once for the whole body
(each rep is sent with side `both`), and the browser shows one "Depth" meter
for them instead of one per arm.

The arm exercises count only standing upright (the torso within 45° of
vertical), or when the camera doesn't see the hips, as when it only sees the
upper body. A push-up counts only lying down: the torso at least 50° from
vertical. So the elbows bending in a push-up are never a curl, and a curl is
never a push-up.

The push-up's bottom is 105°, not 90°: the smoothing takes a few degrees off a
quick bottom, and seen from the side most people's elbows read 95–105° there.
Neither squats nor push-ups need the ankles, which a camera close by often
cuts off: squat depth is measured in body widths (the shoulder width, or the
torso seen from the side), not shin lengths, and the push-up's "lying down"
looks at the torso, not the line to the ankles. Shin lengths were also wrong
from the front: as the knees come forward the shins get shorter in the
picture, so the depth seemed shallower than it was.

All the exercises are watched all the time. The first rep of a set decides
which exercise it is, its name appears at the top of the screen, and only that
exercise is counted until the set ends. One exception: one rep isn't enough to
be sure (picking up the weights, or lifting them to your shoulders before
pressing, looks like a curl), so while a set has only 1 rep it switches to
another exercise when that exercise's rep comes next. The one switch that
doesn't happen is from overhead press to curls, because lowering the weights
after a press looks like a curl. The camera has to see your hands at the top of
the press.

A squat set starts only on the second squat (both within 8 seconds), so sitting
down on a bench, which looks like the bottom of a squat, never starts one.
While a squat is under way, and for 2 seconds after its bottom, the arm
exercises don't count: people often hold their arms out while squatting, which
looks like a lateral raise.

Only the time and date (top left), the exercise and the count (top middle) and
the EasyWeight name (top right) are shown, so the rest of the glass stays clear
for your reflection.

When you stop for 8 seconds, the set is over and the big number turns into a
rest timer, counting from your last rep. Your next rep ends the rest and starts
a new set from 1, and that rep decides the new set's exercise, so you can
switch exercise after a rest. Switching exercise starts the
set number over at 1. If you rest for more than 3
minutes, or nobody is seen for 10 seconds, everything resets for the next
person.

Drinking water or touching your face during the rest doesn't count as a rep. A
curl during the rest is watched until the arm straightens again: if your hand
comes up to your mouth at any point, it's drinking and the rest continues. A
real curl stops near the shoulder, so when the arm straightens it starts the
next set. Raises and presses can't be drinking, so they start the next set
right away.

## Where the camera should be

| Exercise | Camera | Why |
|----------|--------|-----|
| Curls, raises, presses | In front, seeing at least your upper body | The angles are measured in the picture's plane, which faces the camera |
| Squats | In front or from the side, seeing at least your **shoulders, hips and knees** (about 2–3 m back) | The hips' drop is measured in body widths, which stay the same from the front and the side. The knee angle wouldn't work from the front: the thighs point at the camera |
| Push-ups | **From the side**, your body parallel to the mirror | From the front (head toward the camera) the arms and the body point at the camera, and their angles in the picture mean little. Push-ups facing the camera aren't counted |

## Steady readings

MediaPipe's landmarks jitter, and now and then one is far off for a frame or is
lost behind the body. Before a reading reaches the rep counter:

- **A landmark is lost below 0.5 visibility, and found again only at 0.6**, so
  one hovering around the line doesn't come and go every frame.
- **A median of the last 3 readings** drops a single wrong frame completely
  (this makes each rep count one frame, 33 ms, later).
- **Smoothing that reacts in seconds, not frames**: 0.4 of each new reading at
  30 frames a second, and just as quick at 15 fps on a phone or 60 fps on a
  fast camera.
- **Out of sight for more than half a second**, a limb's smoothing starts over
  from where it comes back, instead of from where it was lost. The rep under
  way isn't forgotten.
- **Heights and distances are in body widths**: the shoulder width, so it
  doesn't matter how far you stand from the camera, but at least 0.75 times
  the shoulder-to-hip length when the hips are seen. Turned sideways, the
  shoulders come close together in the picture while the torso keeps its
  length.
- **Squats and push-ups combine both sides**: the average when they agree, the
  better seen side when they don't. From the side, MediaPipe only guesses where
  the far arm and leg are.

## Feedback on the reps

A coach watches the counting (without changing it) and shows a short cue under
the count for a few seconds:

| Cue | When |
|-----|------|
| *Curl all the way up* (or *Raise to shoulder height*, *Press all the way up*, *Squat deeper: thighs to parallel*, *Go lower: elbows to 90°*) | You got at least halfway through a rep, then went back without finishing it |
| *Keep your body in a straight line* (push-ups) | Shoulders, hips and ankles bent by more than 20° on the way down: sagging hips. The rep still counts |
| *Chest up* (squats) | The torso leaned more than 55° forward on the way down (only visible from the side). The rep still counts |
| *Slow down: control the weight* | Two reps of the same arm less than 0.9 seconds apart |

Each set starts with a clean slate. During the rest after a set, the coach
sums it up under the rest timer, with one thing to do on the next set:

| After the set | Next to it |
|---------------|-----------|
| *10 reps · 2 partial* | *Next set: all the way up, all the way down* (for each exercise its own) |
| *10 reps · 3 off form* | *Next set: squeeze your glutes, body straight* (push-ups) or *Next set: chest up, back straight* (squats) |
| *10 reps · 3 too fast* | *Next set: 2 seconds up, 2 seconds down* |
| *Clean set: 10 reps* | A form tip for the exercise, a different one each set, like *Tip: keep your elbows pinned to your sides* |

When a set had more than one of these, whichever happened most decides the
advice. On a tie partial reps win, then form, then pace: the range matters
most.

The mirror (`device/easyweight/coach.py`) and the browser
(`web/src/train/coach.ts`) have the same coach, tested with the same cases.

## Adding an exercise

An exercise is data, not code: an entry in `device/easyweight/exercises.py`
and the same entry in `web/src/train/exercises.ts`. Each says which
landmarks are measured and how (an angle, an angle from vertical, a height, or
the torso's lean), where a rep starts and ends, whether each arm counts
separately or the body once, which posture it needs, an optional form check
for the coach, and the coach's texts. The top of `exercises.py` explains each
field. The parity test compares the two files, so they can't drift apart.

Beyond the two entries, an exercise needs:

1. A value in the backend's `Exercise` enum (`backend/easyweight_api/models.py`),
   an Alembic migration that adds it to the PostgreSQL type (see
   `0005_squat_pushup.py`), and the exercise in `simulator.py` for the demo.
   If it counts for the whole body, add it to `WHOLE_BODY` there too.
2. Its name and color in the web app (`web/src/lib/format.ts`, and a
   `--ex-...` color in `web/src/index.css`), and the type in `web/src/api/types.ts`.
3. Synthetic poses in `device/tests/poses.py`, scenarios in
   `device/tests/web_parity.py` (then `python tests/web_parity.py`) and
   engine tests.

## Tuning

If reps are missed or counted when they shouldn't be, adjust the constants in
`device/easyweight/config.py` and the same ones in `web/src/train/config.ts`
(the web tests fail if they differ). While running, the terminal prints the
top angle (or height) of every rep and how close the wrist came to the mouth.
The squat and push-up thresholds were set from geometry, not from recordings
yet: record a few sets (see `device/tests/recordings/README.md`) and tune from
the printout.

| Constant             | Default | Meaning                                          |
|----------------------|---------|--------------------------------------------------|
| `CURL_DOWN_ANGLE`    | 150     | Elbow angle that counts as "arm straight"        |
| `CURL_UP_ANGLE`      | 50      | Elbow angle that counts as "fully curled"        |
| `RAISE_DOWN_ANGLE`   | 30      | Shoulder angle that counts as "arm down" in a lateral raise (0 = hanging) |
| `RAISE_UP_ANGLE`     | 75      | Shoulder angle that counts as "arm raised" (90 = level with the shoulder) |
| `RAISE_MIN_ELBOW`    | 120     | A lateral raise keeps the elbow at least this straight |
| `RAISE_MAX_ANGLE`    | 140     | A lateral raise stays below this shoulder angle (so a press isn't one) |
| `PRESS_DOWN_HEIGHT`  | 0.5     | Wrist height above the shoulder (in body widths) that counts as "weights at the shoulders" |
| `PRESS_UP_HEIGHT`    | 1.0     | Wrist height above the shoulder that counts as "pressed overhead" |
| `SQUAT_DOWN_HEIGHT`  | 0.8     | Hip height above the knee (in body widths) that counts as "standing" (about 1.1 standing straight) |
| `SQUAT_UP_HEIGHT`    | 0.4     | Hip height above the knee that counts as "at the bottom" (0 = thighs level) |
| `PUSHUP_DOWN_ANGLE`  | 145     | Elbow angle that counts as "arms straight" in a push-up |
| `PUSHUP_UP_ANGLE`    | 105     | Elbow angle that counts as "at the bottom" |
| `UPRIGHT_MAX_TORSO`  | 45      | The arm exercises count only with the torso this close to vertical (or the hips unseen) |
| `SQUAT_MAX_TORSO`    | 60      | A squat may lean forward this much |
| `PUSHUP_MIN_TORSO`   | 50      | A push-up needs the torso at least this far from vertical (lying down) |
| `MIN_VISIBILITY`     | 0.5     | A landmark seen less surely than this is lost    |
| `REGAIN_VISIBILITY`  | 0.6     | ...and found again only once seen this surely    |
| `SMOOTHING`          | 0.4     | 0–1 at 30 fps: lower is steadier but slower to react |
| `MAX_GAP_SECONDS`    | 0.5     | Out of sight longer than this, a limb's smoothing starts over |
| `TORSO_WIDTH_RATIO`  | 0.75    | Body width is at least this times the shoulder-to-hip length |
| `BLOCK_AFTER_REP_SECONDS` | 2  | After a squat's bottom, the arm exercises don't count for this long |
| `SET_IDLE_SECONDS`   | 8       | No new rep for this long ends the set (rest starts) |
| `MAX_REST_SECONDS`   | 180     | Resting longer than this resets the count        |
| `AWAY_RESET_SECONDS` | 10      | Reset the count after nobody is seen this long   |
| `DRINK_DISTANCE`     | 0.52    | During rest, a lift where the wrist comes closer to the mouth than this (in body widths) is drinking |
