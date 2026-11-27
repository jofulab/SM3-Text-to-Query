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

### 1. Setup DBs

The first step is to deploy the four database systems (PostgreSQL, MongoDB, Neo4j and GraphDB) and load and transform
the synthetic patient data that has been generated through [Synthea](https://github.com/synthetichealth/synthea).
For convenience, we provide a docker-compose file:

`docker compose up -d` will take care of deploying the docker container for the four databases, loading and transforming
the data.

> Note: Use `docker compose down` to stop the containers again. Using `docker stop container_name` might leave some
> ports blocked and prevent containers from starting properly again on some systems.

**Repository Setup (mandatory):**

Create GraphDB repository named "sm3_graphdb" by entering the GraphDB GUI on a Browser via http://localhost:7200

In the menu on the left, navigate to `Setup` and then `Repositories`. There, create a new repository and select
`GraphDB Repository`. Make sure to give it the name `sm3_graphdb` and leave the other settings on default.
Once it has been created, select the new repository with `Choose repository` in the top right corner.

If you haven't already, decompress (unzip) the [synthea_ttl.zip](data/synthea_ttl.zip) file in this git repo.
In the UI again, navigate to `Import` and select `Upload RDF files` and upload the `.ttl` files from that zip archive.
Then mark all of them and import them into GraphDB. The import can take a while depending on your system.

### 2. Test the Deployment

Set up a Python venv or conda environment and install the requirements from `requirements.txt`.
Use the [test_databases.py](src/test_databases.py) script to test the four databases. If all tests are successful, you
are good to go.

> NOTE: The data for Neo4J and GraphDB takes a while to be loaded, so check that the GraphDB data is fully loaded, 
> before running the test. The Neo4J data should be ready by the time the GraphDB is done.

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

- `./src/docker_configuration` contains the code to set up the four different database systems (PostgreSQL, GraphDB,
  Neo4j, and MongoDB) and populate them with Synthea data.
- `./src/run_experiments` contains the code to replicate our experiments for all database models, LLMs, prompts, and
  few-shot sampling (repetitions).
- `./src/evaluation` contains the code to evaluate the results obtained by the LLMs for our four databases, including
  the necessary data-cleaning logic. It computes Execution Accuracy (EA) and Valid Efficiency Score (VES) for each
  combination of LLM, database model, and prompt setting.

See [`src/README.md`](src/README.md) for details.

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
