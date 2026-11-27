<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/sm3-logo-dark.svg">
    <img src="docs/assets/sm3-logo.svg" alt="SM3-Text-to-Query" width="380">
  </picture>
</p>

<p align="center"><ins>S</ins>ynthetic <ins>M</ins>ulti-<ins>M</ins>odel <ins>M</ins>edical Text-to-Query Benchmark</p>

<p align="center">
  <a href="https://doi.org/10.52202/079017-2812">Paper</a> ·
  <a href="https://arxiv.org/abs/2411.05521">arXiv</a> ·
  <a href="#data">Data</a> ·
  <a href="#citation">Citation</a>
</p>

This repository contains the data and code for our paper:

> **SM3-Text-to-Query: Synthetic Multi-Model Medical Text-to-Query Benchmark**<br>
> Sithursan Sivasubramaniam, Cedric Osei-Akoto, Yi Zhang, Kurt Stockinger, Jonathan Fürst<br>
> *Advances in Neural Information Processing Systems 37 (NeurIPS 2024), Datasets and Benchmarks Track*

SM3-Text-to-Query asks the same medical questions of four database systems with three data models:
PostgreSQL (SQL), MongoDB (MQL), Neo4j (Cypher) and GraphDB (SPARQL), all loaded with the same
synthetic patient data from [Synthea](https://github.com/synthetichealth/synthea).

![Differences across query languages and database systems for the same user request](./docs/assets/querydifference.png)

## Getting Started

### 1. Set up the databases

Requirements: Docker with Docker Compose, and about 8 GB of memory available to Docker.

```bash
docker compose up -d --build
```

This starts PostgreSQL, MongoDB, Neo4j and GraphDB, plus one loader container per database. Each loader imports
the Synthea data from [`data/`](data), runs a small self-test and exits. Loading takes about 15 minutes in
total (measured on a laptop with 8 GB for Docker); MongoDB is the slowest. Check progress with:

```bash
docker compose ps -a          # all four *_loader containers should end with "Exited (0)"
docker compose logs -f mongodb_loader
```

| Database   | Host port      | User / password | Database / repository |
|------------|----------------|-----------------|-----------------------|
| PostgreSQL | 5432           | sm3 / sm3       | `sm3`                 |
| MongoDB    | 27018          | sm3 / sm3       | `sm3` (authSource `admin`) |
| Neo4j      | 7687 (browser: 7474) | neo4j / password | `neo4j`          |
| GraphDB    | 7200           | admin / root    | `sm3_graphdb`         |

If a port is already in use, set `SM3_POSTGRES_PORT`, `SM3_MONGODB_PORT`, `SM3_NEO4J_BOLT_PORT`,
`SM3_NEO4J_HTTP_PORT` or `SM3_GRAPHDB_PORT`, e.g. `SM3_POSTGRES_PORT=15432 docker compose up -d`.

The data is kept in Docker volumes: `docker compose down` stops everything, and the next `up` skips the import.
`docker compose down -v` deletes the data.

To use your own database servers instead of Docker, run the loader scripts in [`src/setup_dbs/`](src/setup_dbs)
directly; their connection settings are read from environment variables (see each script's config file).

### 2. Test the deployment

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/test_databases.py
```

The script runs one query per database and exits with code 0 if all four return the expected result.
Use the same `SM3_*_PORT` variables if you changed a port.

### 3. Text-to-Query

Run your own Text-to-Query system on the train/dev data.

## Data

- `./data/synthea_data` contains the Synthea data used as the basis for PostgreSQL, GraphDB (RDF), Neo4j, and MongoDB.
- `./data/train_dev` contains the annotated train and dev splits for all four query languages: SQL, SPARQL, Cypher, and
  MQL. The test set is not released publicly, to enable a fair evaluation as is common practice in other
  Text-to-Query benchmarks such as Spider or BIRD.
- `./data/processed_data` contains different data splits, including the responses from the respective databases.
- `./data/question_templates` contains the 408 question templates used to construct SM3-Text-to-Query.
- `./data/results` contains the results for each of the evaluated database systems and query languages for each of
  the five prompts, the four LLMs, and the three repetitions.

See [`data/README.md`](data/README.md) for details. Croissant metadata for the dataset is in
[`data/metadata.json`](data/metadata.json).

## Code

- `./src/setup_dbs` contains the loaders (one per database, each with its Dockerfile) that set up the four database systems (PostgreSQL, GraphDB,
  Neo4j, and MongoDB) and populate them with Synthea data.
- `./src/run_experiments` contains the code to replicate our experiments for all database models, LLMs, prompts, and
  few-shot sampling (repetitions).
- `./src/evaluation` contains the code to evaluate the results obtained by the LLMs for our four databases, including
  the necessary data-cleaning logic. It computes Execution Accuracy (EA) and Valid Efficiency Score (VES) for each
  combination of LLM, database model, and prompt setting.

See [`src/README.md`](src/README.md) for details.

## Errata and Changes Since the Paper

The code exactly as used for the NeurIPS 2024 paper is tagged
[`neurips2024`](https://github.com/jofulab/SM3-Text-to-Query/tree/neurips2024). Check out that tag to reproduce the
reported numbers.

Since then, the prompt schemas in
[`src/run_experiments/prompts/schemas.py`](src/run_experiments/prompts/schemas.py) have been corrected to match the
deployed databases. The databases, gold queries, and gold answers are unchanged.

- **SQL** ([#8](https://github.com/jofulab/SM3-Text-to-Query/issues/8)): `sql_schema` now matches the DDL in
  `setup-postgres.py`. The changes are column types in `patients` and `providers`, the five address columns in
  `payers`, nullability in `payer_transitions`, and several primary keys.
- **MQL** ([#9](https://github.com/jofulab/SM3-Text-to-Query/issues/9)): removed `patients.EXPENSES`. The setup
  never created it, and no gold query uses it. The MongoDB setup now also skips the unused `patient_expenses` collection.
- **Cypher** ([#10](https://github.com/jofulab/SM3-Text-to-Query/issues/10)): added the missing `Allergy.stop`
  property, which 40 gold queries use.

Known data limitation ([#7](https://github.com/jofulab/SM3-Text-to-Query/issues/7)): some columns in
`data/synthea_data` are empty in every row, because Synthea did not populate them in this run. The empty columns are
`allergies.STOP`, `claims.DIAGNOSIS8` and `REFERRINGPROVIDERID`, `claims_transactions.MODIFIER1`, `MODIFIER2` and
`LINENOTE`, and the address and phone columns of `payers`. As a result, questions about when an allergy stopped always
have a NULL answer.

## Citation

If this repository is useful for your work, we would appreciate it if you cited our paper:

```bibtex
@inproceedings{sivasubramaniam2024sm3,
  title     = {{SM3-Text-to-Query}: Synthetic Multi-Model Medical Text-to-Query Benchmark},
  author    = {Sivasubramaniam, Sithursan and Osei-Akoto, Cedric and Zhang, Yi and
               Stockinger, Kurt and F{\"u}rst, Jonathan},
  booktitle = {Advances in Neural Information Processing Systems 37 (NeurIPS 2024),
               Datasets and Benchmarks Track},
  year      = {2024},
  doi       = {10.52202/079017-2812},
  url       = {https://doi.org/10.52202/079017-2812}
}
```

## License

This repository is released under the Apache License 2.0 (see [LICENSE](LICENSE)).

## Contact

Jonathan Fürst, jonathan.fuerst@zhaw.ch
