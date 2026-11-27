#!/usr/bin/env python3
"""
Database Testing Script for SM3 Docker Deployment

Tests all four database systems to verify they are correctly deployed and accessible:
- PostgreSQL
- MongoDB
- Neo4j
- GraphDB (SPARQL)

Exit codes:
  0 - All databases pass
  1 - One or more databases fail
"""

from __future__ import annotations
import json
import os
import sys
from typing import Any, Dict, List, Tuple

# Connection settings live in evaluation/executors.py (defaults match docker-compose.yml; override the ports with
# the same SM3_*_PORT env vars used there)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluation"))
from executors import get_executor  # noqa: E402


# ============================================================================
# SHARED UTILITIES
# ============================================================================

def _normalize_value(v: Any) -> Any:
    """
    Make values JSON-serializable and comparable.
    Converts non-serializable types (datetime, Decimal, UUID, etc.) to strings.
    """
    try:
        json.dumps(v)
        return v
    except TypeError:
        return str(v)


def _normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize all values in all rows for comparison."""
    return [
        {k: _normalize_value(v) for k, v in row.items()}
        for row in rows
    ]


def _sorted_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort rows deterministically to enable order-insensitive comparison."""
    return sorted(rows, key=lambda r: tuple(sorted(r.items())))


# ============================================================================
# TESTER
# ============================================================================

class DatabaseTester:
    """Runs test queries on one database and compares them with the expected rows."""

    def __init__(self, name: str, language: str):
        self.name = name
        self.executor = get_executor(language)

    def run_tests(self, tests: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
        all_ok = True
        details = []
        for i, test in enumerate(tests, start=1):
            query = test["query"].strip()
            expected = _sorted_rows(_normalize_rows(test["result"]))
            res = self.executor.execute(query)
            if not res.ok:
                passed, note, actual = False, f"Error: {res.error}", None
            else:
                actual = _sorted_rows(_normalize_rows(res.rows))
                passed = actual == expected
                note = "Matched expected result." if passed else "DIFFERENCE detected."
            details.append({"index": i, "query": query, "passed": passed, "note": note, "elapsed": res.seconds,
                            "expected": expected, "actual": actual})
            all_ok = all_ok and passed
        return all_ok, details


# ============================================================================
# TEST QUERIES
# ============================================================================

POSTGRES_TESTS = [
    {
        "query": """
SELECT DISTINCT p.first, p.last
FROM organizations org
LEFT JOIN encounters e ON org.id = e.organization
LEFT JOIN patients p ON e.patient = p.id
WHERE org.name = 'ROYAL OF FAIRHAVEN NURSING CENTER';
""",
        "result": [{"first": "Glendora96", "last": "Tillman293"}]
    }
]

MONGODB_TESTS = [
    {
        "query": """db.organizations.aggregate([
  { $match: { "NAME": "ROYAL OF FAIRHAVEN NURSING CENTER" } },
  { $lookup: {
      "from": "patients",
      "localField": "ORGANIZATION_ID",
      "foreignField": "ENCOUNTERS.ORGANIZATION_REF",
      "as": "op"
  }},
  { $unwind: "$op" },
  { $unwind: "$op.ENCOUNTERS" },
  { $match: { "NAME": "ROYAL OF FAIRHAVEN NURSING CENTER" } },
  { $group: { "_id": { "first": "$op.FIRST", "last": "$op.LAST" } } },
  { $project: { "_id": 0, "first": "$_id.first", "last": "$_id.last" } }
])""",
        "result": [{"first": "Glendora96", "last": "Tillman293"}]
    }
]

NEO4J_TESTS = [
    {
        "query": """
MATCH (o:Organization {name: 'ROYAL OF FAIRHAVEN NURSING CENTER'})-[:IS_PERFOMED_AT]->(e:Encounter)<-[:HAS_ENCOUNTER]-(p:Patient)
RETURN DISTINCT p.firstName, p.lastName
""",
        "result": [{"p.firstName": "Glendora96", "p.lastName": "Tillman293"}]
    }
]

GRAPHDB_TESTS = [
    {
        "query": """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX syn: <https://knacc.umbc.edu/dae-young/kim/ontologies/synthea#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX pl:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#PlainLiteral>

SELECT DISTINCT ?first ?last WHERE {
  ?organization a syn:Organization;
                syn:id ?organizationId;
                syn:name 'ROYAL OF FAIRHAVEN NURSING CENTER'^^pl: .
  ?encounter a syn:Encounter;
             syn:organizationId ?organizationId;
             syn:patientId ?patientId .
  ?patient a syn:Patient;
           syn:id ?patientId;
           syn:first ?first;
           syn:last ?last .
}
""",
        "result": [{"first": "Glendora96", "last": "Tillman293"}]
    }
]


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def print_section_header(text: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print('=' * 70)


def print_query_result(result: Dict[str, Any]):
    """Print detailed results for a single query."""
    print(f"\n--- Query #{result['index']} ---")
    print(result['query'])
    print(f"\nPassed: {result['passed']}  |  {result['note']} (ran in {result['elapsed']:.3f}s)")

    if result['expected'] is None:
        print("\nActual rows (paste into 'result' once verified):")
        print(json.dumps(result['actual'], indent=2, ensure_ascii=False))
    elif not result['passed']:
        print("\nExpected:")
        print(json.dumps(result['expected'], indent=2, ensure_ascii=False))
        print("\nActual:")
        print(json.dumps(result['actual'], indent=2, ensure_ascii=False))


def print_summary(results: Dict[str, bool]):
    """Print final summary of all database tests."""
    print_section_header("SUMMARY")

    total = len(results)
    passed = sum(1 for p in results.values() if p)
    failed = total - passed

    for db_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}  {db_name}")

    print(f"\n{'=' * 70}")
    if failed == 0:
        print(f"✓ All {total} databases working correctly!")
    else:
        print(f"✗ {failed}/{total} databases failed")
    print('=' * 70)


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all database tests sequentially and report results."""
    print_section_header("DATABASE CONNECTIVITY TESTS")
    print("Testing all four database systems...")

    results = {}
    all_passed = True

    # Test PostgreSQL
    print_section_header("PostgreSQL Tests")
    try:
        tester = DatabaseTester("PostgreSQL", "sql")
        passed, details = tester.run_tests(POSTGRES_TESTS)
        for detail in details:
            print_query_result(detail)
        results["PostgreSQL"] = passed
        all_passed = all_passed and passed
    except Exception as e:
        print(f"\n✗ Could not connect to PostgreSQL: {e}")
        results["PostgreSQL"] = False
        all_passed = False

    # Test MongoDB
    print_section_header("MongoDB Tests")
    try:
        tester = DatabaseTester("MongoDB", "mql")
        passed, details = tester.run_tests(MONGODB_TESTS)
        for detail in details:
            print_query_result(detail)
        results["MongoDB"] = passed
        all_passed = all_passed and passed
    except Exception as e:
        print(f"\n✗ Could not connect to MongoDB: {e}")
        results["MongoDB"] = False
        all_passed = False

    # Test Neo4j
    print_section_header("Neo4j Tests")
    try:
        tester = DatabaseTester("Neo4j", "cypher")
        passed, details = tester.run_tests(NEO4J_TESTS)
        for detail in details:
            print_query_result(detail)
        results["Neo4j"] = passed
        all_passed = all_passed and passed
    except Exception as e:
        print(f"\n✗ Could not connect to Neo4j: {e}")
        results["Neo4j"] = False
        all_passed = False

    # Test GraphDB
    print_section_header("GraphDB (SPARQL) Tests")
    try:
        tester = DatabaseTester("GraphDB", "sparql")
        passed, details = tester.run_tests(GRAPHDB_TESTS)
        for detail in details:
            print_query_result(detail)
        results["GraphDB"] = passed
        all_passed = all_passed and passed
    except Exception as e:
        print(f"\n✗ Could not connect to GraphDB: {e}")
        results["GraphDB"] = False
        all_passed = False

    # Print summary
    print_summary(results)

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
