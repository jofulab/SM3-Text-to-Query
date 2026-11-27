# Data Directory

| Path | Content |
|------|---------|
| `synthea_data/` | The Synthea CSV files (patients, encounters, claims, ...) loaded into PostgreSQL, MongoDB and Neo4j |
| `synthea_ttl.zip` | The same data as RDF (Turtle), loaded into GraphDB |
| `train_dev/` | The annotated `train.csv` (6,000 questions) and `dev.csv` (2,000 questions), plus `sample_dev.csv` (200 questions) |
| `processed_data/` | The train and dev splits with the results and execution times of the gold queries on each database |
| `question_templates/` | The 408 question templates used to construct SM3-Text-to-Query, one folder per table/entity |
| `results/` | Raw LLM outputs of the paper experiments on dev, per query language, experiment, prompt and LLM |
| `metadata.json` | [Croissant](https://github.com/mlcommons/croissant) metadata of the dataset |

The test set is not released publicly, to enable a fair evaluation as is common practice in other Text-to-Query
benchmarks such as Spider or BIRD.

## Columns of `train_dev/*.csv`

- `question`: the natural-language question
- `sql`, `cypher`, `sparql`, `mql`: the gold query in each query language. For unanswerable questions this is the
  text "No answer possible based on given input".
- `question_type`: list of tags, e.g. `['WH', 'factual', 'linking']`
- `class`: the table/entity the question is about, or `unanswerable_medical` / `unanswerable_non_medical`
- `question_template` (train only): the template the question was generated from

`results/<language>/EXP<n>/dev/*.csv` have the columns `question`, `answers` (raw LLM output) and `time_taken`, and
can be scored with `src/evaluation/evaluate.py`.
