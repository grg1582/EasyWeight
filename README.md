# EasyWeight

A rep counter for a smart mirror. It watches you through a webcam, recognizes
whether you're doing bicep curls, lateral raises or overhead presses, counts
your reps, and
shows the count as bright text on a black screen.
Behind a two-way mirror the black is invisible, so only the numbers appear to
float on the glass.

![EasyWeight smart mirror concept](Images/easyweight_mirror_concept.png)


## How it works

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
exercise is counted until the set ends. One exception: picking up the weights,
or lifting them to your shoulders before pressing, looks like a curl, so a set
that has only 1 curl turns into a lateral raise or overhead press set when one
of those comes next. The camera has to see your hands at the top of the press. Each arm is counted separately, and the
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

## Setup

Requires Python 3.9+ (tested on 3.13) and a webcam

```
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

The pose model (6–31 MB depending on the version) downloads automatically the
first time you run the script.

## Usage

```
python curl_counter.py                  # default webcam, "full" model
python curl_counter.py --camera 1       # use a different webcam
python curl_counter.py --model lite     # faster on slower computers
python curl_counter.py --model heavy    # most accurate
python curl_counter.py --fullscreen     # start fullscreen (for the mirror)
```

### Keys

These also work on a Hebrew keyboard layout.

| Key      | Action                                             |
|----------|----------------------------------------------------|
| F        | Fullscreen on/off                                  |
| D        | Show/hide the camera picture                       |
| R        | Reset the count                                    |
| Q / Esc  | Quit                                               |

## Tuning

If reps are missed or counted when they shouldn't be, adjust the constants at
the top of `curl_counter.py`. While running, the terminal prints the top angle
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

## License

[MIT](LICENSE)

The screen text uses the [Inter Display](https://github.com/rsms/inter) font
(`fonts/InterDisplay-SemiBold.ttf`), included under the SIL Open Font License
1.1. See [fonts/Inter-LICENSE.txt](fonts/Inter-LICENSE.txt).
