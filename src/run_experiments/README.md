# Paper Experiments

Scripts to re-run the LLM experiments from the paper. Each script prompts an LLM to translate the dev questions into
SQL, Cypher, SPARQL or MQL and writes the raw answers to
`data/results/<language>/EXP<n>/dev/dev_<language>_<prompt>_<model>.csv`, the format `src/evaluation/evaluate.py`
scores directly. The outputs of our own runs are already in [`data/results`](../../data/results).

## Setup

```bash
pip install -r requirements-experiments.txt   # from the repository root
```

## Experiments

| Script            | Prompts (per language)                                                         |
|-------------------|--------------------------------------------------------------------------------|
| `run_llm_exp1.py` | with / without schema × 0-shot, 1-shot, few-shot (`prompts/*_prompts_1.py`)    |
| `run_llm_exp2-4.py` | as exp1 (without the 0-shot prompt), with different fixed examples (`*_prompts_2-4.py`) |
| `run_llm_exp5.py` | as exp2-4 with a 5th set of examples (`*_prompts_5.py`), plus BM25-retrieved examples |
| `run_llm_exp6.py` | BM25-retrieved examples only, with / without schema                           |
| `run_llm_exp7.py` | BM25-retrieved examples from different question templates, with / without schema |

`sparql1` and `sparql2` are two variants of the SPARQL prompt with different ontology descriptions. The schemas
shown to the model are in [`prompts/schemas.py`](prompts/schemas.py).

## Running

```bash
python src/run_experiments/run_llm_exp1.py --llm_models gpt-4o-mini --query_languages sql --limit 20
python src/run_experiments/run_llm_exp6.py --llm_models gpt-4o-mini --query_languages cypher --bm25_shots 5
python src/evaluation/evaluate.py --language sql --limit 20 \
    --predictions data/results/sql/EXP1/dev/dev_sql_prompt_schema_fewshots_gpt-4o-mini.csv
```

Options: `--query_languages` (`sql`, `cypher`, `sparql1`, `sparql2`, `mql`), `--datasets` (`dev` or the 200-question
`sample_dev`), `--bm25_shots` (number of retrieved examples for the BM25 prompts), `--limit N` (only the first N
questions). A run can be interrupted and resumed; progress is kept in a `progress_*.json` file next to the CSV.

### Models

| `--llm_models`                                   | Provider                         | Environment variables |
|--------------------------------------------------|----------------------------------|-----------------------|
| `gpt-3.5-turbo-0125` or any other model name     | OpenAI or an OpenAI-compatible server (vLLM, Ollama, ...) | `OPENAI_API_KEY`; `OPENAI_BASE_URL` for other servers (e.g. `http://localhost:11434/v1` for Ollama) |
| `gpt-3.5-turbo-0125-batch`                       | writes OpenAI Batch API request files (see below) | -          |
| `gemini`                                         | Google AI Studio                 | `GOOGLE_API_KEY`, `GEMINI_MODEL` (default `gemini-pro`) |
| `llama3-70b-8192`, `mixtral-8x7b-32768`, `gemma-7b-it` | Groq                       | `GROQ_API_KEY` |
| `llama3-8b`, `llama3-70b-8192-local`             | Text Generation Inference server | `LLAMA_TGI_URL` (e.g. `http://localhost:8080/generate`) |

The paper used gpt-3.5-turbo-0125, gemini-pro, Llama 3 8B/70B (local and via Groq). Several of these models have
since been retired by their providers, so the exact runs may no longer be reproducible; the raw outputs are in
`data/results`.

### OpenAI Batch API

With `--llm_models gpt-3.5-turbo-0125-batch` the script writes the requests to `.jsonl` files in the current folder
(and placeholder answers to the CSVs) instead of calling the API. `exp7_batch.sh` does this for all languages of
experiment 7. Then:

```bash
python src/run_experiments/upload_batch.py <folder with the .jsonl files>
python src/run_experiments/check_batch.py <batch id>          # until the status is "completed"
python src/run_experiments/process_jsonl_results.py <downloaded output .jsonl>   # fills in the CSVs
```

`split_jsonl.py` splits a request file in two if it exceeds the Batch API size limit.
