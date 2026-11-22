# Web app

React, TypeScript and Tailwind, with TanStack Query for loading data and
Recharts for the charts. Sign up, add a mirror, and see your training: reps
per day, reps and sets per exercise, every workout and its sets. It follows
the system's dark mode and works on a phone.

## Live updates

While you're signed in, the app keeps a WebSocket open to the API (the dot
next to your email says **Live**). When a mirror, or the Train page in another
tab or on your phone, sends a rep, the dashboard shows it under **Training
now** (which device, the exercise, the set and the reps so far) and loads its
stats and workouts again, without a reload. See
[Backend and API](backend.md) for how it works on the server.

In development Vite passes the WebSocket on to the API like any other `/api`
request, and in Docker nginx does. On Render the site's rewrite doesn't carry
WebSockets, so the site is built with `VITE_LIVE_URL` set to the API's own
address (`render.yaml`).

## Connecting a mirror by QR code

A mirror running `python -m easyweight.pair` shows a QR code of
`/pair/<code>`. Opening it signs you in first if needed, comes back to the page,
and connects the mirror with one press. A laptop without a camera can type the
code on the Mirrors page instead.

## Training in the browser

The *Train* page counts reps with the webcam, no mirror needed. MediaPipe's
pose model runs in the browser (WebAssembly), so the video never leaves the
device: only the events are sent, the same ones a mirror sends, and the workout
is saved under a "Web browser" device.

The camera view looks like the mirror's display: the time and date, the
exercise, a big rep count that flashes green on every rep, and after 8 seconds
without a rep, a rest timer. Under the count, the same coach as the mirror's
says when a rep stopped halfway or the reps are too fast, and during the rest
sums up the set with a tip for the next one. It can go full
screen (on an iPhone, where a page can't, it fills the window instead).

The model runs on the GPU when there is a real one. Where WebGL is drawn by the
processor (SwiftShader or llvmpipe, as on computers without a usable graphics
card), the GPU path is about 5 times slower than MediaPipe's CPU path and keeps
the page too busy to respond, so the CPU path is used instead.

The counting logic is a TypeScript copy of the mirror's (`web/src/train`). To
keep the two from drifting apart, `device/tests/web_parity.py` runs sessions of
synthetic poses through the Python counter and saves the poses with every rep,
set and event it produced to `web/src/train/parity.json`. The web tests replay
the same poses and must get exactly the same results, and a Python test fails
if the file is out of date. After changing the counting logic:

```bash
cd device
python tests/web_parity.py
```

The access token is kept only in memory. When it expires, the app swaps the
refresh token for a new pair once and repeats the request, so you stay signed
in, also after a reload.
