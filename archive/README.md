# Archive

Code and notebooks from the original paper work, kept for reference. **They are not maintained** and will not run
as they are (they use hard-coded paths, hosts and files that are not part of this repository). The exact code used
for the paper is available under the git tag [`neurips2024`](https://github.com/jofulab/SM3-Text-to-Query/tree/neurips2024).

For evaluating a system, use [`src/evaluation/evaluate.py`](../src/evaluation/evaluate.py) instead.

| Path | Content |
|------|---------|
| `evaluation/DB_query.py`, `evaluation/Dataframe_query_processing/` | Paper pipeline that executed the LLM outputs on the four databases |
| `evaluation/Evaluation.py` | Paper metrics (execution accuracy as string match of the results, VES) |
| `evaluation/results_analysis.ipynb`, `evaluation/dataset_analysis.ipynb` | Analysis of the results and of the dataset for the paper |
| `evaluation/exp6/`, `evaluation/exp7/`, `evaluation/yi_mql_eval_playground.ipynb`, `evaluation/EXP6_7_mql.csv` | MQL evaluation notebooks for experiments 6 and 7 and their scores |
| `utils/clean_results.py` | Clean-up of raw LLM outputs |
| `croissant/` | Croissant metadata experiments (the dataset's metadata is [`data/metadata.json`](../data/metadata.json)) |
