# How the counting works

[MediaPipe Pose](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)
finds your shoulders, elbows and wrists in each frame, and the script measures
each arm in three ways:

| Exercise       | What's measured                         | Arm down    | 1 rep when the arm reaches |
|----------------|-----------------------------------------|-------------|----------------------------|
| Bicep curl     | At the elbow                            | above 150°  | below 50° (fully curled)   |
| Lateral raise  | Upper arm vs straight down (shoulder)   | below 30°   | above 75° (but below 140°), with the elbow fairly straight |
| Overhead press | Wrist height above the shoulder, in shoulder widths | below 0.5 | above 1.0 (pressed overhead) |

All three exercises are watched all the time. The first rep of a set decides
which exercise it is, its name appears at the top of the screen, and only that
exercise is counted until the set ends. One exception: one rep isn't enough to
be sure (picking up the weights, or lifting them to your shoulders before
pressing, looks like a curl), so while a set has only 1 rep it switches to
another exercise when that exercise's rep comes next. The one switch that
doesn't happen is from overhead press to curls, because lowering the weights
after a press looks like a curl. The camera has to see your hands at the top of
the press. Each arm is counted separately, and the
big number shows whichever arm has more reps.

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

## Feedback on the reps

A coach watches the counting (without changing it) and shows a short cue under
the count for a few seconds:

| Cue | When |
|-----|------|
| *Curl all the way up* (or *Raise to shoulder height*, *Press all the way up*) | An arm got at least halfway through a rep, then went back down without finishing it |
| *Slow down: control the weight* | Two reps of the same arm less than 0.9 seconds apart |

Each set starts with a clean slate. During the rest after a set, the coach
sums it up under the rest timer, with one thing to do on the next set:

| After the set | Next to it |
|---------------|-----------|
| *10 reps · 2 partial* | *Next set: all the way up, all the way down* (for each exercise its own) |
| *10 reps · 3 too fast* | *Next set: 2 seconds up, 2 seconds down* |
| *Clean set: 10 reps* | A form tip for the exercise, a different one each set, like *Tip: keep your elbows pinned to your sides* |

When a set had both, whichever happened more decides the advice, and partial
reps win a tie: the range matters more than the pace.

The mirror (`device/easyweight/coach.py`) and the browser
(`web/src/train/coach.ts`) have the same coach, tested with the same cases.

## Tuning

If reps are missed or counted when they shouldn't be, adjust the constants in
`device/easyweight/config.py`. While running, the terminal prints the top angle
(or height) of every rep and how close the wrist came to the mouth.

| Constant             | Default | Meaning                                          |
|----------------------|---------|--------------------------------------------------|
| `CURL_DOWN_ANGLE`    | 150     | Elbow angle that counts as "arm straight"        |
| `CURL_UP_ANGLE`      | 50      | Elbow angle that counts as "fully curled"        |
| `RAISE_DOWN_ANGLE`   | 30      | Shoulder angle that counts as "arm down" in a lateral raise (0 = hanging) |
| `RAISE_UP_ANGLE`     | 75      | Shoulder angle that counts as "arm raised" (90 = level with the shoulder) |
| `RAISE_MIN_ELBOW`    | 120     | A lateral raise keeps the elbow at least this straight |
| `RAISE_MAX_ANGLE`    | 140     | A lateral raise stays below this shoulder angle (so a press isn't one) |
| `PRESS_DOWN_HEIGHT`  | 0.5     | Wrist height above the shoulder (in shoulder widths) that counts as "weights at the shoulders" |
| `PRESS_UP_HEIGHT`    | 1.0     | Wrist height above the shoulder that counts as "pressed overhead" |
| `MIN_VISIBILITY`     | 0.5     | Ignore an arm when MediaPipe isn't confident     |
| `SMOOTHING`          | 0.4     | 0–1: lower is steadier but slower to react       |
| `SET_IDLE_SECONDS`   | 8       | No new rep for this long ends the set (rest starts) |
| `MAX_REST_SECONDS`   | 180     | Resting longer than this resets the count        |
| `AWAY_RESET_SECONDS` | 10      | Reset the count after nobody is seen this long   |
| `DRINK_DISTANCE`     | 0.52    | During rest, a lift where the wrist comes closer to the mouth than this (in shoulder widths) is drinking |
