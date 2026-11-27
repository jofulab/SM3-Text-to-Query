# Database Loaders

One folder per database. Each contains the loader script, its config file, a `Dockerfile` and pinned
`requirements.txt`. The loaders import the Synthea data from [`data/`](../../data), skip the import if the data is
already there, run a self-test query, and exit with code 0 on success.

| Folder      | Loader              | What it loads                                                     |
|-------------|---------------------|-------------------------------------------------------------------|
| `postgres/` | `setup-postgres.py` | `data/synthea_data/*.csv` into 19 tables                          |
| `mongodb/`  | `setup-mongodb.py`  | the CSVs, embedded into 4 collections (`patients`, `organizations`, `providers`, `payers`) |
| `neo4j/`    | `ingest.py`         | the CSVs as a property graph, as defined in `config_neo4j.yml`    |
| `graphdb/`  | `setup-graphdb.py`  | `data/synthea_ttl.zip` (the paper's RDF data) into repository `sm3_graphdb` |

The normal way to run them is `docker compose up -d` from the repository root (see the main [README](../../README.md)).

## Using your own database servers

The loaders can also run directly against databases you host yourself. Install the folder's requirements and set
the connection via environment variables; the defaults are the docker compose values.

| Loader     | Environment variables |
|------------|-----------------------|
| PostgreSQL | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `SYNTHEA_DATA` (or the matching `--db-*` / `--synthea-data` flags) |
| MongoDB    | `MONGO_HOST`, `MONGO_PORT`, `MONGO_USER`, `MONGO_PASSWORD`, `MONGO_AUTH_SOURCE`, `SYNTHEA_DATA` |
| Neo4j      | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `SYNTHEA_DATA` (requires the APOC plugin) |
| GraphDB    | `GRAPHDB_URL`, `GRAPHDB_REPOSITORY`, `GRAPHDB_USERNAME`, `GRAPHDB_PASSWORD`, `TTL_ZIP` |

Example for PostgreSQL:

```bash
pip install -r src/setup_dbs/postgres/requirements.txt
DB_HOST=localhost DB_PASSWORD=secret SYNTHEA_DATA=data/synthea_data python src/setup_dbs/postgres/setup-postgres.py
```

## Custom Synthea data

Replace the CSVs in `data/synthea_data`. For GraphDB, set `GRAPHDB_CONVERT_FROM_CSV=1` so the loader converts the
CSVs to RDF with the bundled [synthea-rdf](https://github.com/leroykim/synthea-rdf) converter (see
[`graphdb/README.md`](graphdb/README.md)) instead of importing `data/synthea_ttl.zip`. Note that the gold queries and
answers in `data/train_dev` only hold for the released data.
