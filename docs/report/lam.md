# Report — phần của Tăng Thoại Lâm (mục 1, 2, 4)

Bản nháp để dán vào `72ITDS30103_SDPs_Final_Report_Template.docx`. Viết bằng tiếng Anh như file mẫu. Mỗi mục khoảng 1,5 trang.

**Trước khi dán:**
- Thay mọi chỗ `(chèn ảnh …)` bằng ảnh chụp thật. Che mọi key, connection string, URL Deploy Hook trước khi chèn.
- Sơ đồ mục 2 viết bằng Mermaid: mở file này trên GitHub (GitHub vẽ sẵn sơ đồ) rồi chụp ảnh dán vào Word.
- Điền các chỗ `[…]`. Kiểm tra lại trên Render: Auto-Deploy đang **tắt**, và thời gian build lấy từ Render Events.
- Kiểm tra lại rule bảo vệ `main` trên GitHub (Settings → Branches) có đúng như 4.1 ghi không: cần PR, 1 review, check `check` xanh. Sai chỗ nào thì sửa câu cho khớp.
- Mục 4 cần bằng chứng một PR bị check đỏ chặn (xem 4.3). Đến 4/11 cả 18 lần chạy trên pull request đều xanh, nên cần làm PR minh họa rồi chụp ảnh.
- Phụ lục B: dán nguyên file `.github/workflows/ci-cd.yml`.

---

## 1. Platform selection rationale

The application is a FastAPI service with a PostgreSQL database and one AI feature. It runs on three managed services: Render for the container, Supabase for the database, and Google Gemini for the AI call. GitHub holds the code and runs CI. Every one of them has a free plan that needs no credit card, which was a hard constraint for a student team.

| Component | Chosen | Chosen over | Why | What it costs us |
|---|---|---|---|---|
| Cloud PaaS | Render Web Service, Free, Docker runtime | Railway, Fly.io, Heroku | Builds our own `Dockerfile`, gives HTTPS on `*.onrender.com`, has a health check path and a Deploy Hook. Railway and Fly.io now offer only a trial credit, and Heroku has no free plan | The instance sleeps after 15 minutes without traffic, so the first request takes up to a minute. 750 free instance hours per workspace per month. 512 MB of RAM |
| Database | Supabase PostgreSQL, Free | Render Postgres (Free), Neon, MongoDB Atlas | Plain PostgreSQL, so the same `schema.sql` runs locally and in the cloud. A free Render database expires 30 days after creation, which is shorter than the project. MongoDB would have meant giving up the joins, constraints and views our data model relies on | The project pauses after one week without activity, and has a 500 MB limit. We must use the transaction pooler on port 6543, which cannot keep prepared statements, so the pool sets `prepare_threshold=None` (Section 5) |
| AI API | Google Gemini (`gemini-3.5-flash-lite`) through its OpenAI-compatible endpoint | OpenAI, Groq, OpenRouter | Free tier with no card, and good Vietnamese. Because `app/ai.py` speaks the OpenAI chat-completions format, any of the alternatives is a change of three environment variables, not of code | Per-minute and per-day quotas. When they run out the user gets a 503 with a clear message (Section 6) |
| CI / registry | GitHub Actions; no registry | GitLab CI, Jenkins; GHCR, Docker Hub | The code is already on GitHub, so Actions needs no extra account or server. Render builds the image itself from the `Dockerfile` at the merged commit, so we do not need to push an image anywhere | The image is built twice, once in CI to prove it builds and once on Render. CI cannot guarantee that Render runs the exact bytes it tested, only the same commit |

**Cost.** The whole stack costs nothing for our team today. For an organisation adopting it, the first paid steps would be a Render instance that does not sleep and a Supabase plan that does not pause. Both are small fixed monthly fees and need no change to the code.

**Portability and lock-in.** We kept every provider behind a standard interface, so each one can be replaced:
- The application is a Docker image that listens on `$PORT`. It runs unchanged on any container host. The only Render-specific pieces are the Deploy Hook URL and the health check setting.
- The database is standard PostgreSQL 16 SQL with no Supabase extension. Moving it is a `pg_dump` and a new `DATABASE_URL`. Row Level Security is switched on only to close Supabase's own REST API, which we do not use.
- The AI provider is set by `AI_BASE_URL`, `AI_MODEL` and the key. The weakest point is the prompt: another model may answer in a different style, so a switch needs a manual check of the answers.

**Licensing.** Everything we ship is open source with permissive licences: Python (PSF), FastAPI (MIT), Uvicorn and Jinja2 (BSD-3-Clause), PostgreSQL (PostgreSQL Licence) and psycopg (LGPL-3.0, used as an unmodified library). Nothing obliges us to publish our own code, although the repository is public by the course rules. The managed services are under their providers' terms. The Gemini free tier may use prompts to improve Google's products, so an organisation handling real customer data should move to a paid tier.

**What the free tiers cost us in practice:**
- **Cold start.** A demo that opens the site after a quiet period waits for the instance to wake up. Before a demo we open `/health` first.
- **Database pause.** The app must survive Supabase being paused. `/health` does not touch the database, so Render never restarts the app in a loop, and every API call answers 503 `DB_UNAVAILABLE` until the database is back (Section 5).
- **Pooler.** Connections go through port 6543, so prepared statements are switched off. We found this limit in the documentation before it failed.
- **Workaround we wrote.** No scheduled job can run on a sleeping instance, so reminder status is computed by a database view when it is read, never by a background job (Section 5).

---

## 2. System architecture

### 2.1 Deployed components

```mermaid
flowchart LR
    User["Browser<br/>laptop or phone"]
    Dev["Developer laptop"]

    subgraph GH["GitHub"]
        Repo["Repository<br/>Zang-1/Vehicle-Maintenance-Log<br/>main is protected"]
        GA["GitHub Actions runner<br/>ci-cd.yml: check, deploy<br/>secret: RENDER_DEPLOY_HOOK"]
    end

    subgraph TB["Trust boundary: our server side"]
        subgraph RD["Render (Free, Docker runtime)"]
            Edge["Render edge<br/>HTTPS, TLS certificate"]
            Web["Web container<br/>python:3.12-slim<br/>uvicorn app.main:app on $PORT"]
            Env[("Environment<br/>DATABASE_URL<br/>GEMINI_API_KEY<br/>APP_ENV=production")]
        end
        subgraph SB["Supabase (Free)"]
            Pool["Transaction pooler<br/>port 6543"]
            PG[("PostgreSQL<br/>8 tables, 2 views<br/>RLS on")]
        end
    end

    Gemini["Google Gemini API<br/>OpenAI-compatible endpoint"]

    User -- "HTTPS 443<br/>cookie vml_session" --> Edge --> Web
    Env -. "environment variables" .-> Web
    Web -- "PostgreSQL over TLS :6543<br/>psycopg pool, max 5" --> Pool --> PG
    Web -- "HTTPS 443<br/>key in Authorization header" --> Gemini
    Dev -- "git push branch, open PR" --> Repo
    Repo -- "pull_request, push to main" --> GA
    GA -- "HTTPS POST deploy hook<br/>only after check is green" --> Web
    Repo -. "Render pulls the commit<br/>and runs docker build" .-> Web
```

(chèn ảnh 2.1: sơ đồ trên, chụp từ GitHub)

**The trust boundary.** Everything inside the dashed box is ours: the container, its environment and the database. The browser is outside it and never receives a secret. The Gemini key exists only in the Render environment and travels only in the `Authorization` header of a request from our server. The browser cannot call Gemini or Supabase directly: it only knows our own URL.

| Component | Where it runs | Reached by | Notes |
|---|---|---|---|
| Web / API application | Render Free Web Service, one Docker container built from our `Dockerfile` (`python:3.12-slim`, uvicorn) | Browser: HTTPS 443 to `https://vehicle-maintenance-log.onrender.com`; Render's edge forwards to the container on `$PORT` | Serves both the HTML pages (Jinja2) and the JSON API (`/api/*`). Holds no state, so a restart loses nothing. Render probes `/health`, which does not touch the database |
| Database | Supabase managed PostgreSQL, Free plan | The container only: PostgreSQL protocol over TLS to the transaction pooler on port 6543, credentials in `DATABASE_URL` | Eight tables and two views (Section 5). Sessions are stored here too, so users stay signed in across redeploys |
| AI API | Google Gemini, model `gemini-3.5-flash-lite` | The container only: HTTPS 443, OpenAI-compatible chat-completions endpoint, 15 s timeout | Called by `app/ai.py`, the only file that knows the provider (Section 6) |
| CI/CD | GitHub Actions, `ubuntu-latest` runner | Started by GitHub on every pull request and every push to `main` | Job `check` lints, tests and builds the image. Job `deploy` calls the Render Deploy Hook (Section 4) |
| Image build | Render's builder | Started by the Deploy Hook | No registry: Render builds the image from the `Dockerfile` at the latest commit of `main` |

The local stack (`compose.yml`) is different on purpose: the database is a `postgres:16-alpine` container reached at host `db` on port 5432, with no pooler, and the app is published only on `127.0.0.1:3000`. Section 3 explains it.

### 2.2 Inside the container

The code has three layers:
- **Presentation:** Jinja2 templates give each page its frame; `app/static/*.js` loads the data with `fetch` and builds the DOM with `textContent` only, never `innerHTML`, so data is never parsed as HTML.
- **Logic:** one FastAPI router per module (`vehicles`, `records`, `service_types`, `reminders`, `stats`, `diagnose`, `auth`, `pages`). Pydantic models in `app/schemas.py` validate every input before any query runs.
- **Data:** `app/db.py` owns the only connection pool. Every query is parameterised and filtered on the signed-in user's id. Rules that must never break are in the database: constraints, a generated line total, and the two views.

### 2.3 One request, end to end: saving a maintenance visit

The user fills in "Ghi lần bảo dưỡng" for their scooter and presses Lưu.

1. **Browser.** `record_form.js` sends `POST /api/vehicles/1/records` with a JSON body (date, odometer, garage, items). The browser adds the `vml_session` cookie (HttpOnly, Secure, SameSite=Lax).
2. **Render edge.** TLS ends at Render's edge, which forwards the request over HTTP to uvicorn on `$PORT` inside the container.
3. **Sign-in check.** The `CurrentUser` dependency hashes the cookie token with sha256 and looks it up in `sessions`. No match gives 401 `NOT_SIGNED_IN`, and the page opens the sign-in screen.
4. **Validation.** FastAPI parses the body into `RecordIn`: the date is not in the future (in Vietnam time), there is at least one item, and quantities and prices are in range. Any failure gives 422 with the field name, and no SQL runs.
5. **Database, one transaction.** The router borrows a connection from the pool (the pool first checks that it is alive), then:
   - checks that vehicle 1 belongs to this user, otherwise 404, exactly like a vehicle that does not exist;
   - checks that every service type is a default one or the user's own, and still active;
   - inserts the record and its items; the database computes each line total;
   - raises the vehicle's odometer if the new reading is higher, never lowers it.

   If any step fails, the whole transaction rolls back. A second visit with the same date and odometer breaks a `UNIQUE` constraint and answers 409 `DUPLICATE_RECORD`.
6. **Response.** The router reads the record back from the `v_record_totals` view and returns 201 with JSON. The connection returns to the pool and the transaction commits.
7. **Browser.** The page moves to `/bao-duong/{id}?saved=1`, which shows "Đã lưu". The reminders of that vehicle change on their own: `v_reminder_status` reads the latest record of each service type, so no other write is needed.

If Supabase is paused at step 5, the pool gives up after 5 seconds and the user sees "Không kết nối được cơ sở dữ liệu, vui lòng thử lại sau ít phút." The form keeps what they typed.

---

## 4. CI/CD pipeline walkthrough

### 4.1 The workflow

One file, `.github/workflows/ci-cd.yml`, with two jobs. The full file is in Appendix B.

```yaml
on:
  pull_request:          # every pull request, whatever its branch
  push:
    branches: [main]     # every merge into main

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5          # Python 3.12, the same as the Dockerfile
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements-dev.txt
      - run: python -m compileall -q app tests  # 1. syntax
      - run: ruff check .                        # 2. lint
      - run: pytest -q                           # 3. tests, no database, no AI key
      - run: docker build -t vehicle-maintenance-log:ci .   # 4. the image still builds

  deploy:
    needs: check                                  # never runs if check is red
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - env: { HOOK: "${{ secrets.RENDER_DEPLOY_HOOK }}" }
        run: |
          if [ -z "$HOOK" ]; then echo "Repository secret RENDER_DEPLOY_HOOK is not set ..."; exit 1; fi
          curl -fsS -X POST "$HOOK" > /dev/null
```

The template lists four jobs. We run lint, test and build as steps of one job, `check`, because they share one checkout and one install. The first failing step stops the job, so each step still blocks on its own.

| Job (step) | Runs on | What it checks | What it blocks |
|---|---|---|---|
| lint (`check`: compileall, `ruff check .`) | Every pull request and every push to `main`, `ubuntu-latest` | Python syntax in `app/` and `tests/`; ruff's default rules: unused imports and variables, undefined names, unsorted imports | A syntax error, or code that hides a bug such as an undefined name |
| test (`check`: `pytest -q`) | Same | 149 tests (4 November): every API route, input validation, isolation between users (another user's data answers 404), every AI failure path, the database-down path | A change that breaks a business rule or lets one user reach another user's data |
| build (`check`: `docker build`) | Same | The `Dockerfile` builds with the current `requirements.txt` | A broken image reaching Render, where it would fail the deploy |
| deploy | Only on a push to `main`, and only after `check` is green | That the `RENDER_DEPLOY_HOOK` secret exists, then calls it | Any red commit reaching production. Render's Auto-Deploy is off, so the hook is the only way in |

**Why the tests need no secret.** `tests/conftest.py` sets a dummy `DATABASE_URL`; `tests/fakedb.py` replaces the connection pool, and the AI call is mocked. The pipeline therefore never holds the database password or the Gemini key. A fork or a pull request from a stranger cannot read them either, because they do not exist in GitHub.

**Branch protection.** `main` requires a pull request with one approving review and a green `check` before the merge button is enabled. Nobody pushes to `main` directly.

(chèn ảnh 4.1: Settings → Branches → rule của `main`, có "Require status checks to pass: check")

### 4.2 What happens on a merge to main

Measured on the merge of PR #30 on 4 November (run `41841050464`):

| Step | Time (UTC) | Duration |
|---|---|---|
| Merge into `main`; GitHub starts the workflow | 13:45:42 | |
| `check` (install, compile, lint, 149 tests, image build) | 13:45:44 to 13:46:11 | 27 s |
| `deploy` calls the Render Deploy Hook | 13:46:13 to 13:46:17 | 4 s |
| Render builds the image and switches traffic once `/health` answers | [điền từ Render Events] | [… phút] |

A change is live about [… phút] after the merge. Render keeps the old container serving until the new one passes its health check, so users see no downtime. To confirm which commit is live, we compare the commit hash on Render's Events page with `main`, and `/api/info` returns the app version.

(chèn ảnh 4.2a: Actions, run của merge PR #30, hai job xanh)
(chèn ảnh 4.2b: Render Events, deploy "Triggered via Deploy Hook" cùng commit `d464a4a`)

### 4.3 Evidence that the pipeline blocks

**The deploy gate failed closed.** The first run on `main` after the workflow was merged (PR #20, 1 November, run `41320852255`) had a green `check` and a red `deploy`:

```
Repository secret RENDER_DEPLOY_HOOK is not set (Settings > Secrets and variables > Actions).
Error: Process completed with exit code 1.
```

The secret had not been created yet. The job stopped with a clear message instead of silently skipping, so a merge could not look deployed when it was not. The fix was to create the Deploy Hook on Render and store it as the repository secret `RENDER_DEPLOY_HOOK`. The re-run (attempt 2, 15:31 UTC) was green, and Render showed one deploy from the hook.

(chèn ảnh 4.3a: run `41320852255` attempt 1, job deploy đỏ với dòng lỗi trên)
(chèn ảnh 4.3b: attempt 2 của cùng run, hai job xanh)

**A red check on a pull request.** [Làm PR minh họa: một commit cố ý làm hỏng một test hoặc để một import thừa, push, chụp check đỏ và nút Merge bị khóa; rồi một commit sửa, chụp check xanh; đóng PR, không merge. Viết lại đoạn này theo đúng lỗi đã dùng, ví dụ:] On pull request #[…] the `check` job failed at the `[Lint / Test]` step: `[dòng lỗi]`. GitHub showed "Required statuses must pass before merging" and the merge button stayed disabled. The next commit `[…]` fixed it, `check` turned green, and only then could the pull request be merged.

(chèn ảnh 4.3c: PR với check đỏ và nút Merge bị khóa)
(chèn ảnh 4.3d: cùng PR sau khi sửa, check xanh)

### 4.4 Secrets the pipeline needs

| Secret | Used by | Stored in | Notes |
|---|---|---|---|
| `RENDER_DEPLOY_HOOK` | Job `deploy` only | GitHub → Settings → Secrets and variables → Actions | Anyone with this URL can trigger a deploy, so it is a secret. GitHub masks it in logs, and it is passed to `curl` through an environment variable, never printed. Section 7 describes the time it leaked and was rotated |
| `DATABASE_URL`, `GEMINI_API_KEY` | Not used by CI | Render → Environment only | The tests replace the database and mock the AI call, so CI never needs them |

The workflow uses only official GitHub actions (`actions/checkout@v4`, `actions/setup-python@v5`). Pull requests from forks get no secrets, and the `deploy` job never runs for a pull request.
