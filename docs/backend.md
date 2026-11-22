# Backend and API

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
| `POST /api/v1/events/browser` | user | The same events, from the Train page |
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
