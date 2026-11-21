# EasyWeight

A rep counter for a smart mirror. It watches you through a webcam, recognizes
whether you're doing bicep curls, lateral raises or overhead presses, counts
your reps, and
shows the count as bright text on a black screen.
Behind a two-way mirror the black is invisible, so only the numbers appear to
float on the glass.

https://github.com/user-attachments/assets/cbb6c348-219c-41a6-bf49-df96ef5d7411



![EasyWeight smart mirror concept](Images/easyweight_mirror_concept.png)

Every set and rep is also saved to your account, and a web dashboard shows
your training over time.

**Live demo: [easyweight.onrender.com](https://easyweight.onrender.com)**.
Press *Try the demo* to look around an account with two months of simulated
workouts, no sign-up needed. (It runs on a free plan that sleeps when nobody
uses it, so the first visit can take a minute to wake up.)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="Images/dashboard-dark.png">
  <img alt="The EasyWeight dashboard: reps per day, reps by exercise and recent workouts" src="Images/dashboard.png">
</picture>

### The whole system

```
mirror (Python)                                      cloud
webcam ─▶ MediaPipe Pose ─▶ rep counter
                               │
                               ▼            HTTPS
                  outbox (SQLite: works ──────────▶ FastAPI ─▶ PostgreSQL
                  offline, sends later)                ▲
                                                       │ /api
                                      browser ─▶ React dashboard
```

| Part | Built with |
|------|------------|
| Mirror app | Python, MediaPipe, OpenCV, SQLite outbox with retries |
| API | FastAPI, SQLAlchemy, Alembic, PostgreSQL, JWT sign-in with refresh tokens, Argon2 |
| Dashboard | React, TypeScript, Tailwind, TanStack Query, Recharts |
| Tests | pytest (against a real PostgreSQL), Vitest, Playwright in a real browser |
| Delivery | Docker, Docker Compose, GitHub Actions, Render, Neon, Sentry |


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

### Saving workouts to the backend

Create an account in the [dashboard](#web-dashboard), then register the
mirror to it once (the backend must be running). It asks for your password:

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

## Project structure

```
device/                 the mirror app (Python)
  easyweight/
    config.py           tuning constants
    geometry.py         angles and distances from the pose points
    counter.py          rep and set logic (ArmCounter, Workout)
    engine.py           feeds one frame into the workout
    recording.py        saving and loading pose recordings
    replay.py           counts the reps in a recording
    reporter.py         turns the workout into events for the backend
    sync.py             outbox on disk, and sending it in the background
    register.py         registers the mirror to your account
    pose.py             the MediaPipe pose model
    hud.py              drawing the mirror display
    app.py              camera, window, keys and the main loop
  tests/                pytest tests
  models/               pose models (downloaded, not in git)
  data/                 the mirror's token and outbox (not in git)
backend/                the API (FastAPI + PostgreSQL)
  easyweight_api/
    models.py           database tables (SQLAlchemy)
    schemas.py          request and response shapes (Pydantic)
    ingest.py           applies the events a mirror sends
    auth.py             user accounts: passwords and login tokens
    demo.py             the read-only demo account
    simulator.py        makes up realistic workouts, as a mirror would send them
    ratelimit.py        limits sign-in attempts
    security.py         device tokens
    routers/            the HTTP endpoints
  migrations/           database migrations (Alembic)
  tests/                pytest tests against a real PostgreSQL
web/                    the dashboard (React + TypeScript)
  src/
    api/                talking to the backend, staying signed in
    auth/               who is signed in
    pages/              dashboard, workouts, one workout, mirrors, sign-in
    components/         charts, tables and small pieces
  e2e/                  Playwright tests in a real browser
docker-compose.yml      runs the dashboard, the API and the database
render.yaml             deploys the API and the dashboard on Render
```

Everything except `pose.py`, `hud.py` and `app.py` is plain Python with no
camera, OpenCV or MediaPipe, so it runs anywhere and is fully tested.

## Backend

The mirror sends what happens (a set started, a rep, a set ended) to the API,
which stores it in PostgreSQL. Each user sees their own mirrors' workouts in
the web dashboard.

```
mirror ──▶ outbox ──events──▶ FastAPI ──▶ PostgreSQL
 (Python)  (SQLite)   (device     ▲
                       token)     │ history and stats (user login)
                                  │
                         dashboard (React)
```

Run everything with Docker:

```
docker compose up --build
```

Then open http://localhost:8080 for the dashboard, or
http://localhost:8000/docs for interactive API docs where you can try every
endpoint (the Authorize button signs in).

| Endpoint | Who | What it does |
|----------|-----|--------------|
| `POST /api/v1/auth/register` | anyone | Create an account. Signs in right away |
| `POST /api/v1/auth/login` | anyone | Sign in with email and password |
| `POST /api/v1/auth/refresh` | anyone | Swap a refresh token for a new pair |
| `POST /api/v1/auth/logout` | anyone | Sign out: the refresh token stops working |
| `POST /api/v1/auth/demo` | anyone | Sign in to the read-only demo account |
| `GET /api/v1/users/me` | user | The signed-in user |
| `GET /api/v1/devices` | user | Your mirrors |
| `POST /api/v1/devices` | user | Add a mirror. Returns its token, once |
| `DELETE /api/v1/devices/{id}` | user | Remove a mirror and its workouts |
| `GET /api/v1/devices/me` | mirror | The mirror a token belongs to |
| `POST /api/v1/events` | mirror | A mirror sends events |
| `GET /api/v1/workouts` | user | Your workouts, newest first, with paging |
| `GET /api/v1/workouts/{id}` | user | One workout and its sets |
| `GET /api/v1/stats` | user | Sets and reps per exercise, and reps per day |
| `GET /health` | anyone | Is the API up and can it reach the database |

How events work:

- **Every event has an id chosen by the mirror**, so sending it twice (say, the
  answer was lost and the mirror retried) is harmless: it comes back as
  `duplicate` and isn't counted again.
- **Each event gets its own result** (`applied`, `duplicate` or `rejected` with a
  reason). One bad event doesn't block the rest of the batch, so a mirror
  sending a backlog after being offline never gets stuck.
- **Events are stored as they arrived** (`events` table) as well as applied to
  `workouts`, `sets` and `reps`, so nothing a mirror sent is ever lost.
- A mirror sends a token, and only its SHA-256 hash is stored. A mirror can
  only change its own workouts.

How signing in works:

- **Passwords** are stored as Argon2 hashes. A wrong email and a wrong
  password get the same answer, in the same time, so the API doesn't reveal
  who has an account.
- **Two tokens.** Signing in gives a short-lived access token (a JWT, 15
  minutes) sent with every request, and a refresh token (30 days) used only to
  get a new pair.
- **Refresh tokens work once.** Each use replaces it. If an already-used one
  shows up again, someone copied it, so every sign-in of that user is
  cancelled.
- **Users only see their own data.** Someone else's workout is "not found",
  not "forbidden", so ids can't be probed.

## Web dashboard

React, TypeScript and Tailwind, with TanStack Query for loading data and
Recharts for the charts. Sign up, add a mirror, and see your training: reps
per day, reps and sets per exercise, every workout and its sets. It follows
the system's dark mode and works on a phone.

The access token is kept only in memory. When it expires, the app swaps the
refresh token for a new pair once and repeats the request, so you stay signed
in, also after a reload.

## Deploying

The live demo runs on free plans: the API and the dashboard on
[Render](https://render.com), the database on [Neon](https://neon.tech).
`render.yaml` describes both Render services, so setting it up is:

1. Create a free PostgreSQL database on Neon and copy its connection string.
2. On Render: New > Blueprint, pick this repository, and paste the connection
   string as `DATABASE_URL` when asked. Render makes a random `JWT_SECRET`.
3. Render builds both services and redeploys on every push to `main`.

The API brings the database up to date on start (`alembic upgrade head`) and
refuses to start in production without a proper `JWT_SECRET`. Sign-in attempts
and new accounts are rate limited. Set `SENTRY_DSN` to get error reports.

To fill the demo account by hand, or after turning it off and on:

```
python -m easyweight_api.demo
```

## Development

The mirror app:

```
cd device
pip install -e ".[dev]"
pytest                  # run the tests
ruff check .            # lint
```

The backend (Python 3.11+). Its tests need a PostgreSQL database, which Docker
provides:

```
docker compose up -d db
cd backend
pip install -e ".[dev]"
set TEST_DATABASE_URL=postgresql+psycopg://easyweight:easyweight@localhost:5432/easyweight_test
pytest
ruff check .
```

(`export` instead of `set` on macOS and Linux. In PowerShell:
`$env:TEST_DATABASE_URL="..."`.)

The dashboard needs [Node.js](https://nodejs.org) 24. With the backend
running (`docker compose up -d db api`):

```
cd web
npm install
npm run dev             # http://localhost:5173, reloads as you edit
npm test                # component tests (Vitest)
npm run typecheck
npx playwright install chromium   # once
npm run e2e             # end-to-end tests in a real browser
```

The tests build synthetic poses (`tests/poses.py`) and play whole sessions
through the counter: sets, rests, drinking during a rest, switching exercise,
walking away. Real recordings in `tests/recordings/` are replayed too, see
[its README](device/tests/recordings/README.md). GitHub Actions runs the lint
and the tests of all three parts on every push, the end-to-end tests against
a real backend, and checks that `docker compose` brings up a working system.

## License

[MIT](LICENSE)

The screen text uses the [Inter Display](https://github.com/rsms/inter) font
(`device/easyweight/fonts/InterDisplay-SemiBold.ttf`), included under the SIL Open Font License
1.1. See [Inter-LICENSE.txt](device/easyweight/fonts/Inter-LICENSE.txt).
