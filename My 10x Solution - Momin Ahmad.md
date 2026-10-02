# My 10x Solution — Momin Ahmad

**Project:** PixelFit — Your Generative AI Fitness Buddy

**Repo:** https://github.com/mominxahmad/PixelFit

---

## 1. The problem

Eating well for a fitness goal starts with numbers most people don't know: their BMI, their BMR (calories burned at rest), and their TDEE (calories burned per day including activity). Working these out by hand means finding the right formulas and applying an activity multiplier. Turning the result into actual meals with a calorie target is a second job that usually means guesswork, a long web search, or a paid coach.

**Who has this problem:** People starting a fitness journey, especially beginners who want to lose fat or build muscle but don't know how many calories they need or what to eat to reach it. They either skip the maths and eat blindly, or lose hours piecing together calculators and generic meal plans that don't fit their body or food culture.

**10x claim:** PixelFit turns a few profile details into BMR, BMI, TDEE and a personalized, downloadable meal plan in seconds, instead of manual calculation and guesswork.

**Non-goals (deliberately not built):** no manual food diary or logging, no long-term progress tracking, no social features.

## 2. How I implemented it

A user registers and logs in, then saves a profile (height, weight, age, sex, activity level, and a goal: cut, maintain, or bulk). PixelFit calculates BMI, BMR, and TDEE and stores them with the profile. The user then requests a meal plan, optionally adding a food preference such as "pakistani food".

The calorie target is calculated in plain Python as TDEE ± 500 kcal/day for cut or bulk, and TDEE for maintain, so the LLM never decides the number. Gemini then generates meals and macros around that target in two variants, **muscle-building** and **normal/general**, each combined with the user's goal. Each variant is generated independently and validated, which means one failing doesn't lose the other. Successful variants are saved to the database under a shared `generation_id`, and the plan can be downloaded as a PDF. Temporary Gemini errors are retried with backoff and then fall back to a second model. If every variant fails, the API returns `503` rather than pretending it worked.

**Stack:** FastAPI (Python), PostgreSQL, Gemini API (free tier), ReportLab, Docker Compose. All free, no credit card.

### Concepts implemented (5, no swaps)

| # | Concept | Where it lives |
|---|---|---|
| 1 | API endpoints | The auth, profile, meal-plan and report routers under `app/routers/`. Pydantic validation and standard status codes |
| 2 | Database | PostgreSQL in Docker with a persistent volume. Users, profiles (with stored BMI/BMR/TDEE) and meal plans |
| 3 | Authentication | JWT bearer tokens from `/auth/login`. Profile, meal-plan and report routes are protected, and each user can only access their own data |
| 4 | LLM integration | Gemini meal plan generation in `app/routers/meal_plan.py`, with output validation, retries and model fallback |
| 5 | Reporting (PDF) | `GET /report/pdf/{generation_id}` builds the meal plan PDF with ReportLab |

**Swaps:** none.

## 3. How to run it

Prerequisites: Docker with Docker Compose, and a free Gemini API key from Google AI Studio.

1. `git clone https://github.com/mominxahmad/PixelFit.git` and `cd PixelFit`
2. `cp .env.example .env`, then fill in the values, including your Gemini API key
3. `docker compose up -d --build`
4. Open `http://localhost:8000/docs`

**5-minute demo path:** register → log in (Authorize in `/docs`) → create a profile → generate a meal plan → download the PDF using the returned `generation_id`.

The full setup, environment variables, everyday commands and troubleshooting are in the repository README.

## 4. Known limitations and future ideas

- Meal plans come from an LLM and BMR/TDEE from standard formulas. They are estimates, not medical or dietitian advice.
- If Gemini is down or overloaded for every model, generation fails and must be retried. Failed variants are not saved.
- The calorie target has no minimum floor yet, so it can be too low for very small or sedentary users.
- Tables are created on startup with no migrations, so a model change means recreating the table.
- **Future ideas:** a minimum calorie floor, Alembic migrations, photo-based calorie estimation (cut for time), and workout tracking.