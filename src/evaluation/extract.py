"""
Pull the query out of raw LLM output, exactly as in the paper's evaluation pipeline.

These heuristics are kept unchanged so that results on the paper's raw outputs (data/results) are comparable. They
have known limits, e.g. the SPARQL pattern stops at the first closing brace, which drops ORDER BY / LIMIT clauses. If
you evaluate your own system, pass clean queries in a ``prediction`` column instead; then no extraction is applied.
"""
import re

NO_ANSWER = "No answer possible based on given input"


def extract_cypher_query(text):
    if not isinstance(text, str):
        return ""
    # Match up to a semicolon or up to the next "[Q]" marker of a few-shot prompt
    match = re.search(r"MATCH.*?(;|(?=\[Q\]))", text, re.DOTALL | re.IGNORECASE)
    if match:
        matched_text = match.group(0).replace("\n", " ").strip()
        if matched_text.endswith("Q"):
            matched_text = matched_text[:-2].strip()
        return matched_text
    return text.strip()


def extract_sparql_query(text):
    if not isinstance(text, str):
        return ""
    match = re.search(r"PREFIX.*?SELECT.*?WHERE\s*\{.*?\}", text, re.DOTALL)
    return match.group(0).replace("\n", " ") if match else ""


def extract_sql_query(text):
    if not isinstance(text, str):
        return ""
    match = re.search(r"SELECT.*?;|SELECT.*?(?=\[Q\])", text, re.DOTALL | re.IGNORECASE)
    return match.group(0).strip().replace("\n", " ") if match else text.strip()


def extract_mql_query(text):
    if not isinstance(text, str):
        return ""
    if NO_ANSWER in text:
        return NO_ANSWER
    for marker in ("[MongoDB]", "[MQL]:", ";", "```python", "mongodb", "```json", "```"):
        text = text.replace(marker, "")
    text = text.strip()
    match = re.search(r"(db\.\w+\.[^;]+)", text)
    return match.group(1).rstrip(";").strip() if match else text


EXTRACTORS = {
    "sql": extract_sql_query,
    "cypher": extract_cypher_query,
    "sparql": extract_sparql_query,
    "mql": extract_mql_query,
}
