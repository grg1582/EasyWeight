# Development

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
[its README](../device/tests/recordings/README.md). GitHub Actions runs the lint
and the tests of all three parts on every push, the end-to-end tests against
a real backend, and checks that `docker compose` brings up a working system.

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
    pages/              dashboard, workouts, one workout, train, mirrors, sign-in
    train/              rep counting in the browser (a copy of the mirror's)
    components/         charts, tables and small pieces
  e2e/                  Playwright tests in a real browser
docker-compose.yml      runs the dashboard, the API and the database
render.yaml             deploys the API and the dashboard on Render
```

Everything except `pose.py`, `hud.py` and `app.py` is plain Python with no
camera, OpenCV or MediaPipe, so it runs anywhere and is fully tested.
