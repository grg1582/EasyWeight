# The mirror app

The Python app that runs on the smart mirror: camera, pose model, rep counter and the display behind the glass.

## Setup

Requires Python 3.10+ (tested on 3.13) and a webcam

```
cd device
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -e .
```

The pose model (6–31 MB depending on the version) downloads automatically into
`device/models/` the first time you run it.

## Usage

```
python -m easyweight                    # default webcam, "full" model
python -m easyweight --camera 1         # use a different webcam
python -m easyweight --model lite       # faster on slower computers
python -m easyweight --model heavy      # most accurate
python -m easyweight --fullscreen       # start fullscreen (for the mirror)
python -m easyweight --record set.jsonl.gz   # also save the pose of every frame
```

A recording holds only the pose points, no video, and can be replayed through
the rep counter without a camera:

```
python -m easyweight.replay set.jsonl.gz
```

### Saving workouts to your account

The easy way: connect the mirror by scanning a QR code with your phone, no
password typed on the mirror.

```
python -m easyweight.pair --name "Home mirror"
```

The mirror shows a big QR code. Scan it with your phone, sign in (or create an
account), and press **Connect mirror**. The mirror notices within a few seconds
and saves its token. `--terminal` prints the QR code in the terminal instead of
opening a window. For a backend on your own computer, pass `--api-url` and
`--site` with the computer's address on your network (not localhost), so the
phone can open the link.

Or sign in on the mirror itself, once (the backend must be running). It asks
for your password:

```
python -m easyweight.register --name "Home mirror" --email you@example.com
```

This saves the mirror's own token to `device/data/device.json` (your password
isn't saved). You can also add a mirror on the dashboard's Mirrors page and
save the settings it shows into that file. From then on the
app sends every set and rep to the backend as it happens. Without a network
nothing is lost: events wait in `device/data/outbox.db` and go out when the
server is reachable again, even after a restart. `--offline` turns this off.

A recording can be sent too, as if it happened just now, which is handy for
trying the backend without a camera:

```
python -m easyweight.replay set.jsonl.gz --send
```

### Keys

These also work on a Hebrew keyboard layout.

| Key      | Action                                             |
|----------|----------------------------------------------------|
| F        | Fullscreen on/off                                  |
| D        | Show/hide the camera picture                       |
| R        | Reset the count                                    |
| Q / Esc  | Quit                                               |

To tune the counting, see [How the counting works](how-counting-works.md#tuning).
