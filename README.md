# PixelFit API

**A Generative AI Fitness Buddy.** A REST API that turns a few profile details into BMI, BMR, TDEE and a personalized, downloadable meal plan in seconds, instead of manual calculation and guesswork.

Built with **FastAPI, PostgreSQL, the Google Gemini API and ReportLab**, and run with Docker Compose. Everything uses free tiers, with no credit card needed.

Built as my FlyRank AI Backend Engineer Internship program capstone, "Your 10x Solution". The overview document is [`My 10x Solution - Momin Ahmad.md`](./My%2010x%20Solution%20-%20Momin%20Ahmad.md).

---

## What it does

PixelFit replaces two manual jobs: working out your daily calorie needs, and building meals around them. A user registers, saves a profile, and PixelFit calculates BMI, BMR and TDEE. It then calculates a daily calorie target and asks Gemini to generate meals around it in two variants, which can be downloaded as a PDF.

The calorie target is calculated deterministically in Python, so the LLM never decides that number. The meals and macros are LLM-generated estimates (see [Known limitations](#known-limitations)).

---

## Capstone concepts implemented (5, no swaps)

| # | Concept | Where it lives in the code |
|---|---|---|
| 1 | **API endpoints** | The `auth`, `profile`, `meal_plan` and `report` routers under `app/routers/`. Pydantic validation and standard status codes |
| 2 | **Database** | PostgreSQL in Docker with a persistent volume, accessed through SQLAlchemy in `app/database.py` and `app/models.py` |
| 3 | **Authentication** | JWT bearer tokens for registration and login in `app/routers/auth.py` |
| 4 | **LLM integration** | Gemini meal plan generation with prompt design, JSON validation, retries and model fallback in `app/routers/meal_plan.py` |
| 5 | **Reporting (PDF)** | On-the-fly PDF via ReportLab at `GET /report/pdf/{generation_id}` in `app/routers/report.py` |

---

## Tech stack

| Technology | Purpose |
|---|---|
| **Python** | Main language |
| **FastAPI** | API framework |
| **PostgreSQL** | Relational database |
| **SQLAlchemy** | ORM |
| **Pydantic** | Request validation and schemas |
| **Google Gemini** | Meal plan generation |
| **ReportLab** | PDF generation |
| **JWT** | Token-based authentication |
| **pwdlib** | Password hashing |
| **Uvicorn** | ASGI server |
| **Docker Compose** | Containerization and orchestration |

---

## Features

### 1. Authentication
- User registration and login with JWT bearer tokens.
- Passwords are hashed with `pwdlib` before storage.
- Profile, meal plan and report routes require a valid token.

### 2. Automated fitness metrics
A user creates a profile with height, weight, age, sex, activity level and goal (cut, maintain or bulk). The API calculates and stores **BMI**, **BMR** and **TDEE**.

### 3. AI meal plan generation
- Calculates a daily calorie target in Python: TDEE ± 500 kcal for cut or bulk, and TDEE for maintain.
- Prompts Gemini to build meals and macros around that target.
- Generates two variants, `muscle_building` and `normal`, each combined with the user's goal. Both come back in one response.
- Accepts an optional free-text food preference, for example "pakistani food". It is treated as data, not instructions, and limited to 100 characters.

### 4. PDF reporting
Converts the saved meal plan into a formatted PDF containing every variant that was generated successfully.

---

## API reference

Interactive docs are at `/docs` once the server is running. Protected routes return `401 Unauthorized` without a valid token.

### Authentication

| Method | Endpoint | Description | Status codes |
|---|---|---|---|
| POST | `/auth/register` | Creates a new user account | `201`, `422` |
| POST | `/auth/login` | Returns a JWT access token | `200`, `401` |

### Profile (requires authentication)

| Method | Endpoint | Description | Status codes |
|---|---|---|---|
| GET | `/profile/me` | Returns the current user's profile and metrics | `200`, `404` |
| POST | `/profile/` | Creates a profile and calculates BMI/BMR/TDEE | `201`, `409` |
| PUT | `/profile/` | Updates stats and recalculates metrics | `200`, `404` |
| DELETE | `/profile/` | Deletes the profile | `204`, `404` |

### Meal plan and report (requires authentication)

| Method | Endpoint | Description | Status codes |
|---|---|---|---|
| POST | `/meal-plan/generate` | Generates both meal plan variants via Gemini | `201`, `404`, `503` |
| GET | `/report/pdf/{generation_id}` | Downloads the saved plan as a PDF | `200`, `404` |

`/meal-plan/generate` returns `201` when at least one variant succeeds, with a per-variant `status` in the response. It returns `503` if every variant fails.

---

## How meal plan generation works

The target calorie number is computed in Python. Only the meals and macros come from the LLM.

```text
User creates a profile (stats + goal)
   ↓
API calculates BMI, BMR and TDEE in Python
   ↓
POST /meal-plan/generate
   ↓
API calculates target calories (TDEE ± 500, by goal)
   ↓
Gemini is prompted to build meals around the target (one call per variant)
   ↓
Each response is validated: JSON with a 'meals' list and a 'macros' object
   ↓
Successful variants are saved to PostgreSQL under a shared generation_id
   ↓
GET /report/pdf/{generation_id} downloads the PDF
```

### Error handling for the LLM call

- **Retries with backoff.** Temporary errors (HTTP 429, 500, 503) are retried up to 3 times per model, waiting about 1 s then 2 s, plus a small random jitter.
- **Model fallback.** If the primary model still fails with a temporary error, the request goes to a fallback model. Both are set as constants at the top of `app/routers/meal_plan.py`.
- **No pointless retries.** Permanent errors, such as an invalid model name or API key, fail immediately.
- **Per-variant isolation.** The variants are generated independently. If one fails, the other is still returned and saved, and the failed one is marked `"status": "failed"` with a reason.
- **Output validation.** Anything that isn't valid JSON with the expected structure marks that variant as failed, and nothing is saved for it.
- **Logging.** API and JSON errors are logged with the variant name, so failures can be diagnosed from the container logs.

---

## Database

PostgreSQL runs in a Docker container and is accessed through SQLAlchemy. Tables are created on app startup.

```text
User (1) ---- (1) Profile   (user_id, unique)
User (1) ---- (M) MealPlan  (user_id)
```

- A user has **one** profile at a time, with BMI, BMR and TDEE stored on it.
- A user can generate **many** meal plans over time. Each `/generate` call creates one row per successful variant, all sharing the same `generation_id`.

---

## Project structure

```text
PixelFit/
├── app/
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── meal_plan.py
│   │   ├── profile.py
│   │   └── report.py
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   └── models.py
├── .dockerignore
├── .env.example
├── .gitignore
├── docker-compose.yaml
├── Dockerfile
├── My 10x Solution - Momin Ahmad.md
├── README.md
└── requirements.txt
```

---

## Quick start (Docker)

**Prerequisites:** Docker with Docker Compose (the Docker daemon must be running) and a free Gemini API key from [Google AI Studio](https://aistudio.google.com/).

### 1. Clone the repository

```bash
git clone https://github.com/mominxahmad/PixelFit.git
cd PixelFit
```

### 2. Create your environment file

```bash
cp .env.example .env
```

Open `.env` and fill in every value:

```text
DATABASE_URL="postgresql+psycopg://postgres:<password>@localhost:5433/<db_name>"
DB_POSTGRES="<db_name>"
USER_POSTGRES="postgres"
PASSWORD_POSTGRES="<password>"
SECRET_KEY="<generate with: openssl rand -hex 32>"
ALGORITHM="HS256"
LLM_API_KEY="<your Gemini API key>"
```

Inside Docker Compose the app reaches the database through the service name `postgres:5432`, which `docker-compose.yaml` sets automatically. `DATABASE_URL` above is only used when running the app outside Docker.

### 3. Start everything

```bash
docker compose up -d --build
```

The first build downloads images and installs dependencies, so it can take several minutes. Later builds are fast because Docker caches the dependency layer.

### 4. Check that it's running

```bash
docker compose ps
docker compose logs -f backend
```

Look for `Application startup complete` (press `Ctrl+C` to stop following; the containers keep running).

The API is now available at `http://localhost:8000`.

---

## 5-minute demo path

Open the interactive docs at **http://localhost:8000/docs** (ReDoc is at `/redoc`), then:

1. **Register:** `POST /auth/register` with an email and password of your choice.
2. **Log in:** click **Authorize** at the top of the page and enter your credentials. This sends the token with every request.
3. **Create a profile:** `POST /profile/` with height, weight, age, sex, activity level and goal. The response shows your BMI, BMR and TDEE.
4. **Generate a meal plan:** `POST /meal-plan/generate`, optionally adding a food preference such as "pakistani food". Copy the `generation_id` from the response.
5. **Download the PDF:** `GET /report/pdf/{generation_id}` with that ID, then download the file from the response.

---

## Everyday commands

| Task | Command |
|---|---|
| Stop, keep the data | `docker compose down` |
| Start again | `docker compose up -d` |
| Rebuild after code changes | `docker compose up -d --build` |
| Stop and delete all database data | `docker compose down -v` |
| View API logs | `docker compose logs -f backend` |
| List database tables | `docker compose exec postgres psql -U postgres -d <db_name> -c "\dt"` |

The app image has no live-reload mount, so code changes only appear after a rebuild.

### Run the API locally without Docker (optional)

Start only the database in Docker, then run the app from the project root inside a virtual environment:

```bash
docker compose up -d postgres
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run `uvicorn` from the project root, not from inside `app/`, because the code uses relative imports.

---

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `failed to connect to the docker API ... docker.sock` | The Docker daemon isn't running. Start it (on Linux: `sudo systemctl enable --now docker`) |
| `port is already allocated` on 8000 | Another process, such as a local uvicorn, is using the port. Stop it first |
| Database container won't start on 5432 | A local PostgreSQL is using that port. This project maps the container to host port **5433** to avoid the clash |
| `503` from `/meal-plan/generate` | Every variant failed. Check `docker compose logs backend` for `Gemini API error` lines. `503 UNAVAILABLE` means Gemini is overloaded, so wait and retry. A `404` means a model name isn't available to your API key |
| `404 Report not found` from `/report/pdf/...` | Only successful variants are saved. Use a `generation_id` from a response where at least one variant had `"status": "success"`, with the same account's token |

---

## Known limitations

- Meal plans are LLM-generated estimates, and BMR/TDEE come from standard formulas. They are **not medical or dietitian advice**.
- The calorie target is computed exactly, but the generated meals and macros are only validated for structure. They are not checked against the target.
- If Gemini is down or overloaded for every model, generation fails and must be retried. Failed variants are not saved, so they don't appear in the PDF.
- The calorie target (TDEE ± 500) has no minimum floor yet, so it can be too low for very small or sedentary users.
- Tables are created on startup with no migrations, so a model change means recreating the table or database.

---

## Future ideas

- **Calorie safety floor:** a minimum daily target so aggressive cuts never drop below a healthy threshold.
- **Alembic migrations:** replace `Base.metadata.create_all()` on startup with versioned schema migrations.
- **Photo-based calorie estimation:** use Gemini Vision to estimate calories from food photos (cut for time).
- **Workout tracking:** log exercise and adjust the activity multiplier dynamically.