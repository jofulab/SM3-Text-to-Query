"""
Run queries against the four SM3 databases started with docker compose.

Each executor has ``execute(query) -> Result``. Connection settings default to the values in docker-compose.yml and
can be overridden with the same SM3_*_PORT env vars used there (plus SM3_*_HOST / credentials, see below).
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Any, List, Optional

QUERY_TIMEOUT = int(os.getenv("SM3_QUERY_TIMEOUT", "120"))  # seconds per query


@dataclass
class Result:
    rows: Optional[List[dict]]  # None if the query failed
    error: Optional[str]
    seconds: float

    @property
    def ok(self) -> bool:
        return self.error is None


class PostgresExecutor:
    def __init__(self):
        from sqlalchemy import create_engine

        host = os.getenv("SM3_POSTGRES_HOST", "localhost")
        port = os.getenv("SM3_POSTGRES_PORT", "5432")
        user = os.getenv("SM3_POSTGRES_USER", "sm3")
        password = os.getenv("SM3_POSTGRES_PASSWORD", "sm3")
        db = os.getenv("SM3_POSTGRES_DB", "sm3")
        self.engine = create_engine(
            f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}",
            connect_args={"options": f"-c statement_timeout={QUERY_TIMEOUT * 1000}"},
        )

    def execute(self, query: str) -> Result:
        from sqlalchemy import text

        start = time.time()
        try:
            with self.engine.connect() as conn:
                rows = [dict(r) for r in conn.execute(text(query)).mappings().all()]
            return Result(rows, None, time.time() - start)
        except Exception as e:  # noqa: BLE001 - any failure of a predicted query counts as an error
            return Result(None, _short(e), time.time() - start)


class Neo4jExecutor:
    def __init__(self):
        from neo4j import GraphDatabase

        uri = os.getenv("SM3_NEO4J_URI", f"bolt://localhost:{os.getenv('SM3_NEO4J_BOLT_PORT', '7687')}")
        self.driver = GraphDatabase.driver(
            uri, auth=(os.getenv("SM3_NEO4J_USER", "neo4j"), os.getenv("SM3_NEO4J_PASSWORD", "password"))
        )

    def execute(self, query: str) -> Result:
        from neo4j import Query

        start = time.time()
        try:
            with self.driver.session(database=os.getenv("SM3_NEO4J_DATABASE", "neo4j")) as session:
                rows = [rec.data() for rec in session.run(Query(query, timeout=QUERY_TIMEOUT))]
            return Result(rows, None, time.time() - start)
        except Exception as e:  # noqa: BLE001
            return Result(None, _short(e), time.time() - start)


class GraphDBExecutor:
    def __init__(self):
        import requests

        self.session = requests.Session()
        self.session.auth = (os.getenv("SM3_GRAPHDB_USERNAME", "admin"), os.getenv("SM3_GRAPHDB_PASSWORD", "root"))
        host = os.getenv("SM3_GRAPHDB_HOST", "localhost")
        port = os.getenv("SM3_GRAPHDB_PORT", "7200")
        repo = os.getenv("SM3_GRAPHDB_REPOSITORY", "sm3_graphdb")
        self.url = f"http://{host}:{port}/repositories/{repo}"

    def execute(self, query: str) -> Result:
        start = time.time()
        try:
            resp = self.session.post(
                self.url,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=QUERY_TIMEOUT,
            )
            if resp.status_code != 200:
                return Result(None, f"HTTP {resp.status_code}: {resp.text.strip()[:300]}", time.time() - start)
            data = resp.json()
            if "boolean" in data:  # ASK query
                rows = [{"boolean": data["boolean"]}]
            else:
                rows = [{var: cell.get("value") for var, cell in b.items()} for b in data["results"]["bindings"]]
            return Result(rows, None, time.time() - start)
        except Exception as e:  # noqa: BLE001
            return Result(None, _short(e), time.time() - start)


class MongoExecutor:
    """Runs MQL (mongosh syntax, e.g. ``db.patients.aggregate([...])``) inside the sm3_mongodb container.

    The queries are mongosh JavaScript, not JSON, so they are executed with mongosh via ``docker exec``; no local
    mongosh installation is needed.
    """

    def __init__(self):
        self.container = os.getenv("SM3_MONGODB_CONTAINER", "sm3_mongodb")
        user = os.getenv("SM3_MONGODB_USER", "sm3")
        password = os.getenv("SM3_MONGODB_PASSWORD", "sm3")
        self.uri = f"mongodb://{user}:{password}@localhost:27017/sm3?authSource=admin"

    def execute(self, query: str) -> Result:
        start = time.time()
        # Cursors (find/aggregate) are materialised; other values (e.g. countDocuments) are returned as one row.
        script = (
            "const __r = (" + query.strip().rstrip(";") + ");\n"
            "const __v = (__r && typeof __r.toArray === 'function') ? __r.toArray() : [{value: __r}];\n"
            "print(EJSON.stringify(__v, {relaxed: true}));"
        )
        try:
            proc = subprocess.run(
                ["docker", "exec", self.container, "mongosh", self.uri, "--quiet", "--eval", script],
                capture_output=True,
                text=True,
                timeout=QUERY_TIMEOUT,
            )
            out = proc.stdout.strip()
            if proc.returncode != 0 or not out:
                return Result(None, _short(proc.stderr.strip() or out or f"mongosh exit code {proc.returncode}"),
                              time.time() - start)
            rows = json.loads(out.splitlines()[-1])
            return Result([r if isinstance(r, dict) else {"value": r} for r in rows], None, time.time() - start)
        except subprocess.TimeoutExpired:
            return Result(None, f"Timeout after {QUERY_TIMEOUT}s", time.time() - start)
        except Exception as e:  # noqa: BLE001
            return Result(None, _short(e), time.time() - start)


EXECUTORS = {"sql": PostgresExecutor, "cypher": Neo4jExecutor, "sparql": GraphDBExecutor, "mql": MongoExecutor}


def get_executor(language: str):
    return EXECUTORS[language]()


def _short(e: Any, limit: int = 300) -> str:
    msg = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
    return f"{type(e).__name__}: {msg}"[:limit] if isinstance(e, BaseException) else msg[:limit]
