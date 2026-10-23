"""One connection pool for the whole app (doc 07, section 6.3)."""

import os

from psycopg_pool import ConnectionPool

# Connection string comes from the environment, never from the code.
# Local: compose.yml builds it (host "db"). Render: Supabase transaction pooler, port 6543.
DATABASE_URL = os.environ["DATABASE_URL"]  # crash at start if it is missing

# One pool per running copy of the app. Created closed: tests can import this
# module without a database; the server opens it at start-up (see main.lifespan).
pool = ConnectionPool(
    DATABASE_URL,
    min_size=1,
    max_size=5,  # small pool: Supabase free tier, several copies may run
    max_lifetime=300,  # recycle: replace a connection after 5 minutes
    check=ConnectionPool.check_connection,  # pre-ping: test before lending
    kwargs={
        "prepare_threshold": None,  # port 6543: no prepared statements
        "connect_timeout": 5,  # fail fast instead of hanging
    },
    open=False,
)


def open_pool() -> None:
    pool.open()  # does not wait: the app starts even if the database is paused


def close_pool() -> None:
    pool.close()  # Render stops the container: return the connections cleanly
