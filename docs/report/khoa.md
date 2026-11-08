# Report — Nguyễn Nam Khoa (Sections 3 and 7)

Sections 3 and 7 (first part) of the final report for course 72ITDS30103 – Software Development Platforms.

---

## 3. Dockerfile and Compose explained

### 3.1 Goal

The application has to run the same way in three places: on a developer laptop, in the GitHub Actions `check` job, and in the container on Render. We therefore package it as one Docker image built from a single `Dockerfile`, and use `compose.yml` to start the web application and a local database with one command:

```bash
git clone https://github.com/Zang-1/Vehicle-Maintenance-Log.git
cd Vehicle-Maintenance-Log
cp .env.example .env          # set DB_PASSWORD
docker compose up --build     # or: podman compose up --build
                              # then open http://localhost:3000
```

The team plan uses Podman because it is free and needs no background daemon. The `Dockerfile` and `compose.yml` use the standard formats, so they run unchanged with either Podman or Docker. The screenshots in this section were taken with Docker Desktop on Windows.

### 3.2 The Dockerfile

The file has 19 lines. Each instruction is there for a reason:

| Instruction | What it does | Why we chose it |
|---|---|---|
| `FROM python:3.12-slim` | Starts from the official Python 3.12 image, slim variant | Same Python version as the CI job, so "green in CI, broken in the image" cannot happen because of a version mismatch. Slim is Debian with only what Python needs, so builds and deploys are faster |
| `WORKDIR /app` | Sets the working directory inside the container | All later commands run in `/app` |
| `ENV PYTHONUNBUFFERED=1` | Turns off Python's output buffering | Logs reach Render immediately instead of sitting in a buffer, which matters when we read logs during a failed deploy |
| `COPY requirements.txt .` then `RUN pip install --no-cache-dir -r requirements.txt` | Installs the libraries before any application code is copied | The manifest changes rarely, so Docker reuses this cached layer on most rebuilds. `--no-cache-dir` keeps pip's download cache out of the image |
| `COPY . .` | Copies the source code last | The source changes constantly, so it comes after the install layer. `.dockerignore` keeps secret files out of this step |
| `ENV PORT=8000` and `EXPOSE 8000` | Sets the default port and documents it | Render sets `PORT` at run time and overrides this value. 8000 is the local default |
| `CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]` | Starts the FastAPI application with Uvicorn | `0.0.0.0` makes the server reachable from outside the container. The `sh -c` wrapper lets the shell expand `${PORT:-8000}`. `exec` makes Uvicorn the main process, so it receives Render's stop signal and shuts down cleanly |

**`.dockerignore`** excludes `.env` and `.env.*`, together with files the application does not need at run time. It has two purposes: a smaller image, and, more important, making sure that a file holding secrets can never be copied into an image.

![Figure 3.2: The Dockerfile](img/fig-3-2-dockerfile.png)

*Figure 3.2: The `Dockerfile` in the repository (19 lines).*

### 3.3 Compose

`compose.yml` defines two services and one named volume, `pgdata`.

| Service | Image | Role | Key settings |
|---|---|---|---|
| `db` | `postgres:16-alpine` | Local PostgreSQL, standing in for Supabase during development | User `app`, database `appdb`, password from `DB_PASSWORD`. The data directory is the volume `pgdata`, so data survives a restart. `db/schema.sql` and `db/seed.sql` are mounted read-only into `/docker-entrypoint-initdb.d/`, so PostgreSQL runs them automatically on the first start. A `healthcheck` runs `pg_isready` every 5 seconds, up to 10 retries |
| `web` | Built from our `Dockerfile` (`build: .`) | The FastAPI application | Published as `127.0.0.1:3000:8000`, so only the laptop itself can reach it. `DATABASE_URL` is assembled as `postgresql://app:<DB_PASSWORD>@db:5432/appdb`. `depends_on` with `condition: service_healthy` makes it wait for the database |

Four details matter in practice:
- **Host name `db`.** Inside a container, `localhost` means the container itself. The web service reaches the database through the service name `db` on the Compose network.
- **Health check before start.** If the web container started before PostgreSQL was ready, its first connection would fail. Waiting for a healthy database makes the first `up` work reliably.
- **Fail fast on a missing password.** `${DB_PASSWORD:?Set DB_PASSWORD in .env}` stops Compose with a clear message when `.env` is missing, instead of starting a database with an empty password.
- **Initial data loads once.** PostgreSQL runs the scripts in `docker-entrypoint-initdb.d` only when the volume is empty, which is the first start or after `podman compose down -v`. The data stays between normal restarts.

The Gemini key is optional: `GEMINI_API_KEY` defaults to empty, so the application still starts and `/diagnose` answers `NO_KEY`.

![Figure 3.3: compose.yml](img/fig-3-3-compose.png)

*Figure 3.3: `compose.yml` with the `web` and `db` services (35 lines).*

### 3.4 Local versus cloud

| | Local (Compose) | Cloud (Render) |
|---|---|---|
| Database | Container `db` (PostgreSQL 16), host `db`, port 5432, no pooler | Supabase through the transaction pooler on port 6543 |
| Network | App on `127.0.0.1:3000` (container port 8000) | Render assigns `$PORT` and puts HTTPS in front |
| Configuration | Read from `.env` | Set in the Render Environment |
| Image | Built from our `Dockerfile` | Built from the same `Dockerfile` at the merged commit |

Render does not read `compose.yml`. Only the configuration changes: the image and the code are identical, which is why a problem reproduced locally is usually the same problem on Render.

### 3.5 Proof: a clean clone

The Brief asks for the stack to start with one command on a machine that has never seen the project. We tested this by cloning the repository into a new folder and following only the steps in the README, then checked:

- `http://localhost:3000/health` returns 200;
- `http://localhost:3000/health/db` returns `{"db":"ok","vehicles":3}`, which shows the sample data was loaded;
- the Dashboard page shows the sample vehicles and maintenance data.

![Figure 3.5a: docker compose ps](img/fig-3-5a-compose-ps.png)

*Figure 3.5a: `docker compose ps` after a clean clone: `db` is healthy and `web` is published on `127.0.0.1:3000`.*
![Figure 3.5b: /health/db](img/fig-3-5b-health-db.png)

*Figure 3.5b: `/health/db` returns `{"db":"ok","vehicles":3}`, so the sample data was loaded.*

**A rule we adopted.** `DB_PASSWORD` may contain only letters and digits. Compose places it inside the `DATABASE_URL` connection string, and characters such as `@`, `:` or `/` would be read as part of the URL and break the connection. `.env.example` states this rule next to the variable, because a strict rule is cheaper than debugging an unreadable error on someone else's machine.

---

## 7. Secret and configuration management (first part)

*Giang continues with the secrets on Render and GitHub Actions, the Git history audit, and the steps taken after a leak.*

### 7.1 Principle

Configuration and secrets never live in the code. The code reads values from environment variables, and the real values are kept outside the repository, different for each environment. The same image therefore runs locally and in production without any change to the code.

### 7.2 Configuration variables

| Variable | Secret? | Local | Render | GitHub Actions |
|---|---|---|---|---|
| `APP_ENV` | No | `.env`, default `development` | Environment (`APP_ENV=production`) | Not needed |
| `PORT` | No | Default 8000 | Set by Render, never overridden | Not needed |
| `DB_PASSWORD` | Yes | `.env` (letters and digits only) | Not used | Not needed |
| `DATABASE_URL` | **Yes** | Assembled by Compose (host `db`) | Environment: Supabase transaction pooler, port 6543 | Dummy value in `tests/conftest.py` |
| `GEMINI_API_KEY` | **Yes** | `.env` (optional) | Environment | Not needed (tests mock the AI call) |
| `AI_BASE_URL`, `AI_MODEL` | No | Optional, defaults in `app/ai.py` | Optional | Not needed |
| `RENDER_DEPLOY_HOOK` | **Yes** | Not present | Not present | Repository secret |

### 7.3 How it works locally

1. **`.env.example`** is committed. It lists the name of every variable but no secret value, and its first line reads "Never commit .env". A new team member knows exactly what to fill in.
2. The developer runs `cp .env.example .env` and enters the real values in `.env`.
3. **`.env` and `.env.*` are listed in `.gitignore`**, so `git add` cannot stage them.
4. **They are also listed in `.dockerignore`**, so they are never copied into the image. Without this line, the secrets would sit inside the image and leak with it.
5. `compose.yml` reads `.env` and passes the values to the containers at **run time**, through `${...}` substitution. Nothing is written into the image at **build time**.

![Figure 7.3a: .env.example](img/fig-7-3a-env-example.png)

*Figure 7.3a: `.env.example` lists variable names only, with no secret values.*
![Figure 7.3b: git check-ignore](img/fig-7-3b-check-ignore.png)

*Figure 7.3b: `git check-ignore -v .env` shows that line 13 of `.gitignore` blocks `.env`.*

### 7.4 Why we did it this way

- **Configuration is separate from code.** Changing the database or rotating a key does not need a code change or a new build.
- **Two barriers for two leak routes.** `.gitignore` stops secrets entering the repository, and `.dockerignore` stops them entering the image. Each file protects a different route, so we need both.
- **Tests need no secrets.** CI uses a dummy `DATABASE_URL` and mocks the Gemini call, so the pipeline passes without holding any real secret.

### 7.5 Team rules

- Never commit `.env`, a key or a connection string anywhere, **including screenshots and group chat messages**.
- Before attaching an image to an Issue or pull request, check it for connection strings and keys.
- Every new variable must have its name added to `.env.example` in the same pull request.
