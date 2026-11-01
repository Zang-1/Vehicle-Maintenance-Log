"""A small stand-in for the database pool, so router tests need no PostgreSQL (NFR-11).

    cursor = use_fake_db(monkeypatch, [
        ("FROM vehicles", [row]),                 # any query containing this text returns these rows
        ("INSERT INTO vehicles", {"id": 7}),      # a dict is one row
        ("UPDATE vehicles", UniqueViolation()),   # an exception instance is raised
        ("SELECT count(*)", Seq({"n": 0}, {"n": 1})),  # successive answers; the last one repeats
    ])
    ...
    cursor.calls    # [(sql with single spaces, params), ...] in the order the router ran them

The first entry whose text appears in the query wins; a query nothing matches returns no rows.
"""

from contextlib import contextmanager

from app import db


class Seq:
    """Successive answers to the same query."""

    def __init__(self, *results):
        self.results = list(results)

    def next(self):
        return self.results.pop(0) if len(self.results) > 1 else self.results[0]


class FakeCursor:
    def __init__(self, script):
        self.script = script
        self.calls = []
        self.rows = []

    def execute(self, query, params=None):
        sql = " ".join(query.split())
        self.calls.append((sql, params))
        self.rows = []
        for key, result in self.script:
            if key not in sql:
                continue
            if isinstance(result, Seq):
                result = result.next()
            if isinstance(result, Exception):
                raise result
            if result is not None:
                self.rows = result if isinstance(result, list) else [result]
            break
        return self

    def executemany(self, query, params_seq):
        self.calls.append((" ".join(query.split()), list(params_seq)))

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)

    def calls_matching(self, text):
        return [params for sql, params in self.calls if text in sql]


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, *args, **kwargs):
        return self._cursor

    def execute(self, query, params=None):
        return self._cursor.execute(query, params)


def use_fake_db(monkeypatch, script):
    cursor = FakeCursor(script)
    connection = FakeConnection(cursor)

    @contextmanager
    def fake_connection(timeout=None):
        yield connection

    monkeypatch.setattr(db.pool, "connection", fake_connection)
    return cursor
