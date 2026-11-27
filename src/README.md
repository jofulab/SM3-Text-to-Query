# Source Code

| Path | Purpose | Docs |
|------|---------|------|
| [`setup_dbs/`](setup_dbs) | Loaders that import the Synthea data into PostgreSQL, MongoDB, Neo4j and GraphDB; run by `docker compose up` from the repository root | [README](setup_dbs/README.md) |
| [`test_databases.py`](test_databases.py) | Runs one test query per database; exit code 0 if all four are loaded correctly | below |
| [`evaluation/`](evaluation) | `evaluate.py` scores predicted queries on the dev set by execution accuracy | below |
| [`run_experiments/`](run_experiments) | Re-runs the paper's LLM prompting experiments | [README](run_experiments/README.md) |

All scripts can be started from any directory. Host-side dependencies are in `requirements.txt` (test and
evaluation) and `requirements-experiments.txt` (experiments) in the repository root.

## Connection settings

`test_databases.py` and `evaluation/` connect to the databases started with docker compose on `localhost`. If you
changed a host port when starting the databases, set the same variable when running the scripts:

| Database   | Env vars (default) |
|------------|--------------------|
| PostgreSQL | `SM3_POSTGRES_PORT` (5432), `SM3_POSTGRES_HOST`, `SM3_POSTGRES_USER`, `SM3_POSTGRES_PASSWORD`, `SM3_POSTGRES_DB` |
| MongoDB    | `SM3_MONGODB_CONTAINER` (`sm3_mongodb`); MQL is executed with mongosh inside this container |
| Neo4j      | `SM3_NEO4J_BOLT_PORT` (7687) or `SM3_NEO4J_URI`, `SM3_NEO4J_USER`, `SM3_NEO4J_PASSWORD` |
| GraphDB    | `SM3_GRAPHDB_PORT` (7200), `SM3_GRAPHDB_HOST`, `SM3_GRAPHDB_REPOSITORY` (`sm3_graphdb`) |

`SM3_QUERY_TIMEOUT` sets the per-query timeout in seconds (default 120).

## Evaluation

```bash
python src/evaluation/evaluate.py --language sql --predictions my_predictions.csv --out per_question.csv
python src/evaluation/evaluate.py --language cypher --gold-as-prediction --limit 100   # setup check: 100%
```

- [`evaluate.py`](evaluation/evaluate.py) reads a CSV with one row per dev question (in `data/train_dev/dev.csv`
  order) and a `prediction` column, or an `answers` column with raw LLM output as written by `run_experiments/`.
  See `--help` and the main [README](../README.md#3-evaluate-your-text-to-query-system) for the metric.
- [`executors.py`](evaluation/executors.py) runs a query on one of the four databases.
- [`extract.py`](evaluation/extract.py) pulls the query out of raw LLM output (the heuristics used in the paper).
