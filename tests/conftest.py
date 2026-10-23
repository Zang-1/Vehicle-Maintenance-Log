import os

# app.db reads DATABASE_URL at import and crashes without it. The tests never
# open the pool (TestClient without "with" skips the lifespan), so a harmless
# dummy value is enough. CI has no .env and needs no secret.
os.environ.setdefault("DATABASE_URL", "postgresql://app:unused@localhost:5432/appdb")
