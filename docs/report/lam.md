# Report - Tăng Thoại Lâm's part (sections 1, 2, 4)

Draft to paste into `72ITDS30103_SDPs_Final_Report_Template.docx`.

**Before pasting:**
- Hide every key, connection string and Deploy Hook URL.
- Ask Giang to confirm that Auto-Deploy is **off** (Render Events shows only deploys through the hook, which is consistent with off).
- Appendix B: paste the whole `.github/workflows/ci-cd.yml` file.

---

## 1. Platform selection rationale

We picked platforms that are easy to deploy and easy for a three-person student team to use. Render is also covered in this course, so we could apply directly what we learned.

| Component | Chosen | Chosen over | Why | What it costs us |
|---|---|---|---|---|
| Cloud PaaS | Render Web Service, Free, Docker runtime | Railway, Fly.io | Easy to deploy and use, and taught in this course. We had not had the chance to try or study the alternatives, so Render was the safer decision | The service goes to sleep when unused (after 15 minutes), so the first request is slow and scheduled jobs cannot run |
| Database | Supabase PostgreSQL, Free | Neon | We had already had several chances to work with Supabase, so it was easier to get started | The project pauses after a week without use. 500 MB limit |
| AI API | Google Gemini API, free tier | ChatGPT (OpenAI API) and other providers | The API key is easy to get and the service is reliable. Our earlier projects used a Gemini API key, and we had not tried switching to ChatGPT or another provider | Rate limits, so a demo can hit a 429 |
| CI / deploy | GitHub Actions + Render Deploy Hook | Render Auto-Deploy | A change is deployed only after it passes the checks, instead of everything that is pushed going live | One more secret to manage (the hook URL). There is no registry: Render builds the image itself |

**Cost.** Free for our team. If a company used this stack, we would move to paid plans instead of the free tiers, so the services do not sleep or pause.

**Portability and lock-in.** If we left Render, we would need another host that can run our Dockerfile. If we left Supabase, we would move to Neon, because it uses the same SQL. Firebase uses NoSQL, which would be harder for the team and take much more time to rebuild.

**Licensing.** Our main dependencies are open source: Python (PSF), FastAPI (MIT), Uvicorn and Jinja2 (BSD-3-Clause), PostgreSQL (PostgreSQL Licence), psycopg (LGPL-3.0).

**What the free tiers cost us in practice.** Render and Supabase go to sleep when they are not used for too long. Our workaround is to start them early, before the demo.

---

## 2. System architecture

### 2.1 Deployed components

![Figure 2.1: Deployed components and the trust boundary](img/fig-2-1-architecture.png)

**Trust boundary.** A change goes from a laptop to a pull request on GitHub, GitHub Actions checks it, and after the merge it reaches the web container on Render. When the site is used, the container reads and writes Supabase and calls the Gemini API. The Gemini API key is stored in Render's environment variables. Locally it stays in `.env`, which `.gitignore` keeps out of Git. The browser never sees the key, because only our server calls Gemini: the browser only talks to our own URL.

| Component | Where it runs | Reached by | Notes |
|---|---|---|---|
| Web / API application | Render Free, one container from our `Dockerfile` (`python:3.12-slim`, uvicorn) | HTTPS 443 to `vehicle-maintenance-log.onrender.com`; Render's edge forwards to `$PORT` | Serves HTML pages and the JSON API. Holds no state |
| Database | Supabase PostgreSQL, Free | Container only: PostgreSQL over TLS, pooler port 6543, credentials in `DATABASE_URL` | Eight tables, two views. Sessions live here, so users stay signed in across redeploys |
| AI API | Google Gemini | Container only: HTTPS 443, 15 s timeout | Called only from `app/ai.py` |
| CI/CD | GitHub Actions, `ubuntu-latest` | Started by pull requests and pushes to `main` | `check`, then `deploy` calls the Deploy Hook |
| Image build | Render's builder | Started by the Deploy Hook | No registry: built from the `Dockerfile` at the latest commit of `main` |

Inside the container: Jinja2 templates and `fetch` scripts (presentation), one FastAPI router per module with Pydantic validation (logic), and `app/db.py`, the only connection pool (data). Section 3 explains how the local stack differs.

### 2.2 One request, end to end: saving a maintenance visit

1. The user fills in the form and presses Save ("Lưu"). `record_form.js` sends the data to our server with `POST /api/vehicles/1/records`, over HTTPS, with the sign-in cookie.
2. The server checks that the user is signed in (401 if not) and that the input is valid (422 if not).
3. The server checks that the vehicle exists and belongs to this user (404 if not), and that it is not archived (409 `VEHICLE_ARCHIVED` if it is).
4. It checks for other errors: every service type must exist and be active (422 if not).
5. If there is no error, it adds the record and its items to the database, raises the vehicle odometer if the new reading is higher, and saves everything in one transaction. If a step fails, nothing is saved. The same date and odometer twice is refused (409).
6. The server reads the saved record back and answers 201. The page opens the new record and shows that it was saved.

---

## 4. CI/CD pipeline walkthrough

### 4.1 The workflow

`.github/workflows/ci-cd.yml` has two jobs (full file in Appendix B).

```yaml
on:
  pull_request:
  push:
    branches: [main]
jobs:
  check:
    steps:                                      # after checkout, Python 3.12 and install
      - run: python -m compileall -q app tests  # 1. syntax
      - run: ruff check .                       # 2. lint
      - run: pytest -q                          # 3. tests, no database, no AI key
      - run: docker build -t vehicle-maintenance-log:ci .  # 4. image builds
  deploy:
    needs: check                                # never runs if check is red
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - run: curl -fsS -X POST "$HOOK" > /dev/null  # fails first if the secret is missing
```

The `check` job sets up Python, installs the dependencies, compiles the Python files, runs the `ruff` lint, runs the tests, and builds the image to make sure the Dockerfile still works. The `deploy` job runs only after `check` has passed: it checks that the hook secret is set on GitHub, then tells Render to build.

| Job (step) | Runs on | What it checks | What it blocks |
|---|---|---|---|
| lint (`compileall`, `ruff`) | Every pull request and push to `main` | Syntax, unused imports, undefined names | Code that does not compile or hides such a bug |
| test (`pytest`) | Same | 155 tests: API routes, validation, isolation between users, AI failures | A broken business rule, or one user reaching another's data |
| build (`docker build`) | Same | The `Dockerfile` still builds | A broken image reaching Render |
| deploy | Push to `main`, after a green `check` | The secret exists, then calls the hook | A red commit reaching production; Auto-Deploy is off, so the hook is the only way in |

The tests replace the database with `tests/fakedb.py` and mock the AI call, so CI never holds the database password or the Gemini key.

`main` accepts changes only through a pull request with one approval from someone other than the last pusher, and a green `check`, set as a required status check.

### 4.2 What happens on a merge to main

Measured on PR #40 (9 November, run `42572466362`), which changed `APP_VERSION` to 0.6.0, so `/api/info` shows when the new code is live:

| Step | Time (UTC) | Duration |
|---|---|---|
| Merge | 06:20:44 | |
| `check` | 06:20:49 to 06:21:20 | 31 s |
| `deploy` calls the hook | 06:21:22 to 06:21:26 | 4 s |
| Render builds and switches | `/api/info` said 0.5.0 at 06:21:42, 0.6.0 at 06:21:54 | under 30 s |

The image that goes live is built on Render. A change is live about one minute after the merge. This deploy changed only source code, so Docker reused the dependency layer; a change to `requirements.txt` takes longer. Figures 4.2a and 4.2b (Appendix B) show the run and the Render deploy.

### 4.3 Evidence that the pipeline blocks

**A staged red check.** No real pull request had failed by 4 November, so we staged one. PR #31 removes `AND current_odometer < %(odometer)s` from the odometer update, which breaks BR-02: saving an older visit would lower the odometer.

```
FAILED tests/test_records.py::test_create_record_saves_record_items_and_raises_the_odometer
1 failed, 148 passed
```

The `check` job (run `41853983479`) failed at the `Test` step after 21 s. Lint had passed: the code was valid, only the rule was wrong. Merging was blocked. Commit `c9fd586` restored the condition and `check` turned green (Figure 4.3d, Appendix B). The pull request was closed without merging.

![Figure 4.3c: Pull request #31 with the red check](img/fig-4-3c-pr-red.png)

**The deploy gate failed closed.** The first run on `main` (PR #20, 1 November, run `41320852255`) had a green `check` and a red `deploy`, with `Repository secret RENDER_DEPLOY_HOOK is not set`. The job stopped instead of skipping silently, so a merge could not look deployed when it was not. After the secret was added, attempt 2 was green (Figures 4.3a and 4.3b, Appendix B).

### 4.4 Secrets the pipeline needs

| Secret | Used by | Stored in |
|---|---|---|
| `RENDER_DEPLOY_HOOK` | Job `deploy` only | GitHub Actions repository secrets |
| `DATABASE_URL`, `GEMINI_API_KEY` | Not used by CI | Render Environment only |

The hook URL is a secret because anyone holding it can trigger a deploy. Section 7 describes the time it leaked. Forks get no secrets, and `deploy` never runs for a pull request.

---

<!-- appendices: not counted in the 12 pages -->

## Appendix B - CI/CD evidence (after the workflow file)

![Figure 4.1: Merge box of pull request #31, merging blocked](img/fig-4-1-merge-blocked.png)

![Figure 4.2a: Run 42572466362, the merge of PR #40](img/fig-4-2a-actions-run.png)

![Figure 4.2b: Render Events, the deploy of commit 48134b4 triggered via Deploy Hook](img/fig-4-2b-render-events.png)

![Figure 4.3a: Run 41320852255, attempt 1, deploy failed](img/fig-4-3a-deploy-failed.png)

![Figure 4.3b: The same run, attempt 2, both jobs green](img/fig-4-3b-deploy-rerun.png)

![Figure 4.3d: Pull request #31 after the fix, check green](img/fig-4-3d-pr-green.png)

---

## Appendix E - AI-use declaration (Lâm's part, draft)

**B. AI tools used**

| # | Tool and model / version | Plan | Used by | Period of use |
|---|---|---|---|---|
| 1 | Claude Code (Anthropic), model Claude Opus 5.5 | Paid | Tăng Thoại Lâm | October - November 2026 |

**C. Use log (Lâm)**

| # | Artefact | Member | Tool | What the AI produced or explained | Gen. / Assist. | How you checked and changed it | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Reminders API and tab: `app/routers/reminders.py`, `ReminderIn`, `ReminderDetailOut`, `app/static/vehicle_reminders.js`, `tests/test_reminders.py` (PR #29) | Lâm | Claude Code | Wrote the code and 19 tests from the team's task assignment | Generated | Ran 48 checks on a real PostgreSQL database (including isolation between two users) and 149 tests, and tried the tab in a browser; another member reviewed the PR. Lâm tried adding, editing, pausing and deleting reminders and the error for an already existing service type, and all passed | E-4; E-5 (PR #29) |
| 2 | Workflow `.github/workflows/ci-cd.yml` (PR #20) | Lâm | Claude Code | Wrote the `check` and `deploy` jobs | Generated | The first `deploy` run was red because the secret was missing; after adding it the re-run was green. Lâm looked at and tried CI on GitHub, in both the red and the green case | E-5 (PR #20) |
| 3 | Vehicles and maintenance modules: `app/routers/vehicles.py`, `app/routers/records.py`, the pages and tests (PR #21, #22) | Lâm | Claude Code | Wrote the code and tests | Generated | Lâm tried the features and the archived-vehicle error, and all passed | E-5 (PR #21, #22) |
| 4 | Documents 02, 03, 07 (PR #4) | Lâm | Claude Code | Wrote the document content | Generated | Lâm checked the content again | E-5 (PR #4) |
| 5 | Pull request demonstrating a red check (#31) | Lâm | Claude Code | Proposed the demonstration, wrote the commit that breaks BR-02 and the commit that fixes it | Generated | Looked at the red check and the blocked merge on GitHub, then closed the PR without merging | E-4; E-5 (PR #31) |
| 6a | Report §1, §2.2, the trust boundary paragraph of §2.1 and the paragraph describing the two jobs in §4.1 (`docs/report/lam.md`) | Lâm | Claude Code | Asked guiding questions; translated Lâm's answers into English, formatted them, pointed out and fixed technical errors, added the sign-in and input-validation steps; added the list of licences | Assisted | Lâm answered in their own words why each platform was chosen and how to move away from it, and described the steps of `create_record` and of the two CI jobs; checked against document 08 and the code | E-4; E-5 |
| 6b | Report §2.1 (diagram, component table) and the rest of §4 (`docs/report/lam.md`, PR #32, #41, #43, #44) | Lâm | Claude Code | Wrote the content from the code and the CI history; measured the deploy time | Generated | Claude checked it against `ci-cd.yml`, the GitHub API and `/api/info`; another member reviewed it and asked for it to be shortened. Lâm checked the content again | E-4; E-5 |
| 7 | Figures 2.1, 4.1, 4.2a, 4.2b, 4.3a-d | Lâm | Claude Code | Built the page that exports diagram 2.1 from Mermaid; cropped the screenshots | Assisted | The screenshots were taken by team members on GitHub and Render; checked that no key or hook URL is visible | E-6 |

**E. Evidence** (numbered after Giang's E-1 to E-3)

| Item | Link, file name or screenshot | What it shows |
|---|---|---|
| E-4 | Transcript of the project's Claude Code session [file name after export] | Prompts and responses for rows 1, 5, 6, 7 |
| E-5 | Pull requests on GitHub: https://github.com/Zang-1/Vehicle-Maintenance-Log/pulls?q=is%3Apr+author%3Anoway165 | Code, commit history and reviews |
| E-6 | Folder `docs/report/img/` (`fig-2-1-*`, `fig-4-*`) | The figures in row 7 |
