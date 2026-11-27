#!/usr/bin/env python3
"""
Score Text-to-Query predictions on the SM3 dev set by execution accuracy.

Each predicted query and the corresponding gold query are run on the databases started with ``docker compose up``;
a prediction counts as correct if both return the same result.

    python src/evaluation/evaluate.py --language sql --predictions my_predictions.csv
    python src/evaluation/evaluate.py --language mql --gold-as-prediction --limit 50   # sanity check, ~100%

The predictions CSV has one row per dev question, in the order of data/train_dev/dev.csv, with either
  - a ``prediction`` column holding the query, or
  - an ``answers`` column holding raw LLM output (the format written by src/run_experiments), from which the query
    is extracted with the paper's heuristics (see extract.py).
A ``question`` column is optional; if present it must match dev.csv row by row.

Comparison: results are compared as multisets of rows; row order, column order and column names are ignored, and
numbers are compared after rounding to 6 decimals. For unanswerable questions (class ``unanswerable_*``) a
prediction is correct if it starts with "no" (e.g. "No answer possible based on given input"), as in the paper.
Note: the paper compared the string form of the results instead, so numbers are not directly comparable.
"""
from __future__ import annotations

import argparse
import ast
import csv
import datetime
import decimal
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from executors import get_executor  # noqa: E402
from extract import EXTRACTORS  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DEV_CSV = os.path.join(REPO_ROOT, "data", "train_dev", "dev.csv")
CACHE_DIR = os.path.join(REPO_ROOT, ".sm3_cache")
PROBE_QUERIES = {"sql": "SELECT 1", "cypher": "RETURN 1", "sparql": "ASK {}", "mql": "db.patients.find({}).limit(1)"}
LANGUAGES = {"sql": "sql", "cypher": "cypher", "sparql": "sparql", "sparql1": "sparql", "sparql2": "sparql", "mql": "mql"}


# --------------------------------------------------------------------------- result comparison

def _norm_value(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float, decimal.Decimal)):
        return round(float(v), 6)
    if isinstance(v, str):
        try:  # SPARQL returns every value as a string
            return round(float(v), 6) if v.strip() and v.strip().lower() not in ("nan", "inf", "-inf", "infinity") else v
        except ValueError:
            return v
    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
        return v.isoformat()
    if isinstance(v, dict):
        return json.dumps({k: _norm_value(x) for k, x in v.items()}, sort_keys=True, default=str)
    if isinstance(v, (list, tuple)):
        return json.dumps([_norm_value(x) for x in v], default=str)
    return str(v)  # e.g. neo4j temporal types, UUIDs


def canonical(rows):
    """Order-insensitive, column-name-insensitive form of a result: a sorted list of sorted value tuples."""
    out = []
    for row in rows:
        values = [_norm_value(v) for v in row.values()]
        out.append(sorted(values, key=repr))
    return sorted(out, key=repr)


def same_result(a, b):
    return Counter(map(repr, a)) == Counter(map(repr, b))


# --------------------------------------------------------------------------- data loading

def load_dev():
    csv.field_size_limit(sys.maxsize)
    with open(DEV_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_predictions(path, language, n_rows):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit(f"{path} is empty")
    if "prediction" in rows[0]:
        preds = [r["prediction"] or "" for r in rows]
    elif "answers" in rows[0]:
        preds = [EXTRACTORS[language](r["answers"]) for r in rows]
    else:
        sys.exit(f"{path} needs a 'prediction' (query) or 'answers' (raw LLM output) column")
    if len(preds) < n_rows:
        sys.exit(f"{path} has {len(preds)} rows, but {n_rows} dev questions are evaluated (use --limit to evaluate fewer)")
    questions = [r.get("question") for r in rows]
    return preds, questions


def is_unanswerable(dev_row):
    return dev_row["class"].startswith("unanswerable")


def tags(dev_row):
    try:
        return ast.literal_eval(dev_row["question_type"])
    except (ValueError, SyntaxError):
        return []


# --------------------------------------------------------------------------- gold results (cached)

def gold_results(language, dev, n_rows, executor, refresh=False):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"gold_{language}.json")
    cache = {}
    if os.path.exists(path) and not refresh:
        with open(path) as f:
            cache = json.load(f)
    missing = [i for i in range(n_rows) if str(i) not in cache and not is_unanswerable(dev[i])]
    if missing:
        print(f"Running {len(missing)} gold {language} queries (cached in {os.path.relpath(path, REPO_ROOT)}) ...")
        for k, i in enumerate(missing, 1):
            res = executor.execute(dev[i][language])
            cache[str(i)] = {"rows": canonical(res.rows) if res.ok else None, "error": res.error}
            if k % 100 == 0 or k == len(missing):
                print(f"  gold {k}/{len(missing)}")
                with open(path, "w") as f:
                    json.dump(cache, f)
    return cache


# --------------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--language", required=True, choices=sorted(LANGUAGES),
                        help="query language of the predictions (sparql1/sparql2 are treated as sparql)")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--predictions", help="CSV with a 'prediction' or 'answers' column, one row per dev question")
    src.add_argument("--gold-as-prediction", action="store_true",
                     help="evaluate the gold queries themselves (sanity check of the setup; should give ~100%%)")
    parser.add_argument("--limit", type=int, help="only evaluate the first N dev questions")
    parser.add_argument("--out", help="write per-question results to this CSV")
    parser.add_argument("--refresh-gold", action="store_true", help="re-run the gold queries instead of using the cache")
    args = parser.parse_args()

    language = LANGUAGES[args.language]
    dev = load_dev()
    n_rows = min(args.limit or len(dev), len(dev))

    if args.gold_as_prediction:
        preds, questions = [r[language] for r in dev], [None] * len(dev)
    else:
        preds, questions = load_predictions(args.predictions, language, n_rows)
    for i in range(n_rows):
        if questions[i] is not None and questions[i].strip() != dev[i]["question"].strip():
            sys.exit(f"Row {i}: question does not match dev.csv - predictions must be in dev.csv order.\n"
                     f"  predictions: {questions[i]!r}\n  dev.csv:     {dev[i]['question']!r}")

    executor = get_executor(language)
    probe = executor.execute(PROBE_QUERIES[language])
    if not probe.ok:
        sys.exit(f"Cannot query the {language} database: {probe.error}\n"
                 "Are the databases running? Start them with `docker compose up -d` and check `docker compose ps -a`;\n"
                 "if you changed a host port, set the same SM3_*_PORT variable here.")
    gold = gold_results(language, dev, n_rows, executor, refresh=args.refresh_gold)

    per_row, gold_failed = [], 0
    by_tag = defaultdict(lambda: [0, 0])
    print(f"Evaluating {n_rows} {language} predictions ...")
    for i in range(n_rows):
        pred = (preds[i] or "").strip()
        error, seconds = None, 0.0
        if is_unanswerable(dev[i]):
            correct = pred.lower().startswith("no")
        elif gold[str(i)]["error"] is not None:
            gold_failed += 1
            per_row.append({"index": i, "question": dev[i]["question"], "prediction": pred, "correct": "",
                            "error": f"gold query failed: {gold[str(i)]['error']}", "seconds": ""})
            continue
        elif not pred or pred.lower().startswith("no"):
            correct = False
        else:
            res = executor.execute(pred)
            error, seconds = res.error, res.seconds
            correct = res.ok and same_result(canonical(res.rows), gold[str(i)]["rows"])
        for t in (["unanswerable"] if is_unanswerable(dev[i]) else tags(dev[i])) + ["all"]:
            by_tag[t][0] += int(correct)
            by_tag[t][1] += 1
        per_row.append({"index": i, "question": dev[i]["question"], "prediction": pred, "correct": int(correct),
                        "error": error or "", "seconds": round(seconds, 4)})
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{n_rows}")

    scored = by_tag["all"][1]
    errors = sum(1 for r in per_row if r["error"] and not str(r["error"]).startswith("gold"))
    print(f"\nExecution accuracy ({language}, {scored} questions): {100 * by_tag['all'][0] / max(scored, 1):.2f}%")
    print(f"Predicted queries that failed to execute: {errors}")
    if gold_failed:
        print(f"Skipped {gold_failed} questions whose gold query failed (see --out for details)")
    print("\nBy question type:")
    for t in sorted(k for k in by_tag if k != "all"):
        c, n = by_tag[t]
        print(f"  {t:<14} {100 * c / n:6.2f}%  ({c}/{n})")

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["index", "question", "prediction", "correct", "error", "seconds"])
            w.writeheader()
            w.writerows(per_row)
        print(f"\nPer-question results written to {args.out}")


if __name__ == "__main__":
    main()
