# FilmLog API — Movie Watchlist & Review Backend

Backend REST API for **FilmLog**, a movie watchlist and review platform in the vein of Letterboxd/IMDb,
built for the GDGoC Backend assignment. Key features: JWT authentication, a personal watchlist, watch history
with ratings and reviews, and **movie recommendations from Google Gemini, grounded in the local database**.

- **Stack:** Python 3.11+ (developed on 3.13) · FastAPI · SQLAlchemy 2.0 · PostgreSQL on Supabase (SQLite for local dev and tests) · bcrypt · PyJWT · Google Gemini (`google-genai`) · pytest
- **Companion frontend:** the [`frontend/`](frontend/) folder from the starter pack (unmodified)
- **Live API:** <https://movie-watchlist-dusky-six.vercel.app> — health check at `/api/health`, interactive Swagger docs at [`/docs`](https://movie-watchlist-dusky-six.vercel.app/docs)

## Project structure

```text
.
├── data/movies.json          # 20 initial movies (from the starter pack)
├── frontend/                 # companion frontend (from the starter pack)
└── backend/
    ├── app/
    │   ├── main.py           # entry point: CORS, error handlers, routers
    │   ├── config.py         # settings loaded from environment variables
    │   ├── database.py       # engine and session factory
    │   ├── models.py         # database schema (ERD)
    │   ├── schemas.py        # request/response validation (Pydantic)
    │   ├── security.py       # bcrypt password hashing + JWT helpers
    │   ├── deps.py           # authentication dependency
    │   ├── errors.py         # uniform error format
    │   ├── seed.py           # table creation + idempotent seeder
    │   ├── routers/          # auth, movies (+ AI recommendation), watchlist, watched
    │   └── services/         # gemini.py (API client), recommender.py (prompt + validation)
    ├── tests/                # pytest suite
    ├── .env.example          # template for local configuration
    ├── pytest.ini
    └── requirements.txt
```

## Getting started

### Prerequisites

- Python 3.11 or newer
- A free Gemini API key from <https://aistudio.google.com>
- A database — either of these:
  - **SQLite** — nothing to install; this is the default.
  - **PostgreSQL** — for example a free [Supabase](https://supabase.com) project.

### Install and run

Run these commands from the `backend/` folder.

```bash
cd backend
python -m venv .venv

source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows (PowerShell)

pip install -r requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
# now open .env and fill in the values (see the table below)

python -m app.seed                 # creates the tables and inserts the 20 movies (safe to re-run)
uvicorn app.main:app --reload --port 8000
```

The API is now available at <http://localhost:8000> and the Swagger UI at <http://localhost:8000/docs>.

> `--reload` restarts the server when `.py` files change, but **not** when `.env` changes.
> After editing `.env`, stop the server (Ctrl+C) and start it again.

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Required in production | `postgresql://user:pass@host:port/db` or `sqlite:///./filmlog.db`. Defaults to a local SQLite file. `postgres://` and `postgresql://` URLs are converted automatically for the psycopg driver. |
| `JWT_SECRET` | **Yes** | Secret used to sign tokens, at least 16 characters. The app refuses to start without it. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `GEMINI_API_KEY` | For the AI feature | From Google AI Studio. When empty, `POST /api/movies/recommend` responds with 503. |
| `GEMINI_MODEL` | No | Default `gemini-3.8-flash`. Model names change often — if the AI endpoint returns 502, check which models your key can use and set this variable accordingly. |
| `JWT_EXPIRE_MINUTES` | No | Token lifetime. Default `1440` (24 hours). |
| `BCRYPT_ROUNDS` | No | bcrypt cost factor. Default `12`; the test suite lowers it to keep tests fast. |
| `CORS_ORIGINS` | No | Comma-separated list of allowed origins. Default `*`. |

Never commit your real `.env` file — it is listed in `.gitignore`.

### Running the frontend

```bash
cd frontend
python -m http.server 3000
```

Open <http://localhost:3000>. The frontend talks to `http://localhost:8000/api` by default.
To use another backend (for example the deployed one), click **⚙️ Settings** and set the API Base URL,
e.g. `https://<your-project>.vercel.app/api`. The value is stored in the browser's `localStorage`,
so it overrides the default until you change it again.

### Running the tests

```bash
cd backend
pytest -v
```

The suite uses an in-memory SQLite database and a fake Gemini client, so it needs no internet connection,
database, or API key. The test configuration overrides `DATABASE_URL`, so the tests can never touch your
real (e.g. Supabase) database.

## API reference

Protected endpoints expect the header `Authorization: Bearer <token>`, where the token comes from `POST /api/auth/login`.

| Method & path | Auth | Success | Error codes |
|---|---|---|---|
| `POST /api/auth/register` | – | 201 | 400, 409 |
| `POST /api/auth/login` | – | 200 `{token, token_type, user}` | 400, 401 |
| `GET /api/movies?genre=&search=&shuffle=` | – | 200 | 400 |
| `GET /api/movies/{id}` | – | 200 | 400, 404 |
| `POST /api/movies/recommend` | – | 200 `{movie_id, reasoning}` | 400, 502, 503 |
| `GET /api/watchlist` | Bearer | 200 | 401 |
| `POST /api/watchlist` | Bearer | 201 | 400, 401, 404, 409 |
| `DELETE /api/watchlist/{movieId}` | Bearer | 200 | 401, 404 |
| `GET /api/watched` | Bearer | 200 | 401 |
| `POST /api/watched` | Bearer | 201 | 400, 401, 404, 409 |
| `GET /api/health` | – | 200 | – |

### Error format

Every error — expected or not — uses the same JSON shape (the bundled frontend reads `message`):

```json
{ "error": "Conflict", "message": "Film sudah ada di watchlist kamu.", "status": 409 }
```

Validation errors use status **400** (not FastAPI's default 422) and add a `details` array:

```json
{
  "error": "Bad Request",
  "message": "Validasi gagal - rating: Input should be less than or equal to 5",
  "status": 400,
  "details": [{ "field": "rating", "message": "Input should be less than or equal to 5" }]
}
```

> The human-readable `message` texts are currently written in Indonesian.

### Example requests

```bash
# Register, then log in
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"andi","email":"andi@mail.com","password":"secret1234"}'

curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"andi@mail.com","password":"secret1234"}'

# Use the returned token
curl http://localhost:8000/api/watchlist -H "Authorization: Bearer <token>"

# Ask the AI for a recommendation
curl -X POST http://localhost:8000/api/movies/recommend \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a dark crime thriller with a plot twist"}'
```

On Windows PowerShell, `curl` is an alias of `Invoke-WebRequest`; use `curl.exe` or the Swagger UI at `/docs` instead.

## Design and technical decisions

### Database (ERD)

```mermaid
erDiagram
    USERS ||--o{ WATCHLISTS : "saves"
    USERS ||--o{ REVIEWS : "writes"
    MOVIES ||--o{ WATCHLISTS : "appears in"
    MOVIES ||--o{ REVIEWS : "is reviewed in"
    MOVIES }o--o{ GENRES : "movie_genres"

    USERS {
        int id PK
        string username
        string email UK
        string password_hash
        datetime created_at
    }
    MOVIES {
        int id PK
        string title
        int year
        string director
        float rating
        string duration
        text synopsis
        text poster_url
        json cast_members
    }
    GENRES {
        int id PK
        string name UK
    }
    WATCHLISTS {
        int id PK
        int user_id FK
        int movie_id FK
        datetime created_at
    }
    REVIEWS {
        int id PK
        int user_id FK
        int movie_id FK
        int rating
        text review
        datetime created_at
    }
```

- `watchlists` and `reviews` each have a **unique constraint on `(user_id, movie_id)`**. Duplicates are rejected by the
  database itself (so the rule holds even under concurrent requests) and translated into HTTP 409.
- `reviews.rating` is protected by `CHECK (rating BETWEEN 1 AND 5)` in addition to Pydantic validation.
- Genres are normalised into their own table (many-to-many) so genre filtering is a real query; the cast list is a
  JSON column because it is only displayed, never searched.
- All foreign keys use `ON DELETE CASCADE`.
- `username` is a display name and is intentionally **not** unique (the frontend derives it from the email);
  the unique identity for login is the email.
- Seeding inserts explicit movie ids; on PostgreSQL the seeder also re-syncs the id sequence so later inserts cannot collide.

### Security

- Passwords are hashed with **bcrypt** (a unique salt per password) and are never returned in any response.
- JWTs use HS256 with an `exp` claim. When decoding, the accepted algorithm is whitelisted, so tokens with
  `alg: none` or any other algorithm are rejected.
- `user_id` is always taken from the verified **token**, never from the request body or URL, so users cannot
  read or modify each other's data. Another user's entry answers 404 (not 403) so its existence is not revealed.
- Login returns the same error for "unknown email" and "wrong password", and runs a dummy bcrypt check for unknown
  emails so response times do not reveal which emails are registered.
- Input is validated with Pydantic (type, length, range). SQL goes through the ORM (parameterised queries), and
  `LIKE` wildcards in the search box are escaped.
- Unexpected errors are logged on the server only; clients receive a generic message.
- **Supabase:** Row Level Security is enabled on all tables. The backend connects as the database owner role, which
  bypasses RLS, while Supabase's auto-generated REST API is blocked from reading or writing the tables directly.

### AI recommendations (grounding)

`POST /api/movies/recommend` asks Gemini to pick **one movie from the local catalogue**. Four layers keep the model
from inventing movies:

1. **Context** — the whole catalogue (id, title, year, genres, synopsis) is read from the database and placed in the prompt.
2. **Rules** — the system instruction forbids choosing anything outside the list. The user's text is wrapped in
   `<permintaan>` ("request") tags and declared to be data, not instructions; angle brackets are stripped from user
   input so it cannot close the tag (prompt-injection mitigation).
3. **Format** — Gemini's JSON mode is enabled and the expected `{movie_id, reasoning}` shape is described in the prompt.
4. **Validation** — the answer is parsed and its `movie_id` is checked against the ids that really exist in the
   database. If it is invalid, the request is retried once with feedback about what was wrong; if it still fails,
   the API answers **502**.

Layer 4 is the actual guarantee; layers 1–3 only make a valid answer more likely.

Status codes: `400` invalid prompt · `502` Gemini failed or its answer was unusable · `503` `GEMINI_API_KEY` not configured.
Failure details are written to the server log, while the client only receives a generic message.
The prompt and the model's explanations are in Indonesian.

Code: `app/services/recommender.py` (prompt building, parsing, validation — framework-free) and
`app/services/gemini.py` (API client behind a small interface, which tests replace with a fake).

### Known limitations and future work

- **No migration tool.** Tables are created with `create_all`, which never alters existing tables. For schema
  changes in production, adopt Alembic.
- **The AI endpoint is public** (as the assignment specifies), so anyone can consume the Gemini quota.
  Rate limiting or requiring login would address this.
- **JWTs cannot be revoked** before they expire. Short-lived access tokens plus refresh tokens would fix that.
- **One review per user and movie.** A second submission answers 409; an update endpoint could be added.

## Deployment (Vercel + Supabase)

The API is deployed on **Vercel** (free Hobby plan, no credit card needed), which runs FastAPI natively as a
serverless function, and uses **Supabase** for PostgreSQL. This is a monorepo, so Vercel must be pointed at the
`backend/` folder.

### 1. Prepare the database

1. Create a Supabase project and copy a **pooler** connection string (**Connect → Connection pooling**).
   For Vercel use the **Transaction pooler** (port `6543`): serverless functions open many short-lived connections.
   The app detects `pooler.supabase.com` and disables prepared statements automatically, which that mode requires.
2. Create the tables and seed the movies **once, from your machine** (the seeder is not run on Vercel):

   ```bash
   cd backend
   # put the Supabase URL in .env as DATABASE_URL, then:
   python -m app.seed
   ```

3. Enable Row Level Security so the tables cannot be accessed through Supabase's REST API.
   Run this in the Supabase **SQL Editor**:

   ```sql
   ALTER TABLE public.users        ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.movies       ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.genres       ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.movie_genres ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.watchlists   ENABLE ROW LEVEL SECURITY;
   ALTER TABLE public.reviews      ENABLE ROW LEVEL SECURITY;
   ```

   The backend is unaffected because it connects as the `postgres` role, which bypasses RLS.
   (If you ever drop and recreate the tables, run this again.)

### 2. Create the Vercel project

1. In Vercel choose **Add New → Project** and import this GitHub repository.
2. Configure the project:

   | Setting | Value |
   |---|---|
   | Framework Preset | `FastAPI` (auto-detected; `Other` also works) |
   | **Root Directory** | **`backend`** |
   | Build and Output Settings | Leave everything at the defaults. Python projects need no build command or output directory, and Vercel installs `requirements.txt` automatically. |

3. Add the **Environment Variables** (values without quotes), then click **Deploy**:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | Supabase Transaction pooler URL (port 6543) |
   | `JWT_SECRET` | A newly generated secret (see the table above) |
   | `GEMINI_API_KEY` | Your Gemini API key |
   | `GEMINI_MODEL` | A model available to your key |
   | `CORS_ORIGINS` | `*` |

   Mark the secrets as **Sensitive** if Vercel offers the option. Environment variables only apply to **new**
   deployments, so after changing one, trigger **Redeploy** from the Deployments tab.

### 3. Verify the deployment

Use your **production domain** (`https://<project>.vercel.app`), not the long per-deployment URLs:

```bash
curl https://<project>.vercel.app/api/health         # {"status":"ok"}
curl https://<project>.vercel.app/api/movies         # the 20 seeded movies
```

Then open `/docs`, log in via `POST /api/auth/login`, click **Authorize**, and try the protected endpoints.
Finally, point the frontend at the deployed API through **⚙️ Settings**
(`https://<project>.vercel.app/api`) and run through register → login → watchlist → watched → AI recommendation.

### Notes and troubleshooting

- **Deployment Protection.** On the Hobby plan the production domain is public, while preview and per-deployment URLs
  can require a Vercel login. If a request returns a Vercel login page instead of JSON, you are on a protected URL.
- **Cold starts.** Serverless functions start on demand, so the first request after a quiet period is slower.
- **Entrypoint not found.** If Vercel cannot locate the app, add `backend/index.py` containing
  `from app.main import app  # noqa: F401`.
- **Dependency build errors.** Pin the Python version by adding `backend/.python-version` (for example `3.12`).
- **AI endpoint returns 502.** Open **Logs** in Vercel and look for the line starting with `Rekomendasi gagal`:
  it names the cause (unknown model, invalid API key, exhausted quota). Check `GEMINI_MODEL` and `GEMINI_API_KEY`
  and redeploy.
- **Database connection errors.** Make sure you use the pooler host (`...pooler.supabase.com`), that the password
  has no unescaped special characters (`@` becomes `%40`), and that the Supabase project is not paused.
