"""The example bundle's attester is real code, so it gets a real test.

OKFX does not execute attesters - OKF §12 defers their ABI - but shipping an
`Attested Computation` concept whose attester does not work would be worse than
shipping none, so the logic the article describes is exercised here: the agent
proposes a number, and something deterministic checks it came from the sanctioned
query rather than one the agent wrote.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from okfx.document import Document

BUNDLE = Path(__file__).resolve().parents[1] / "examples" / "acme"
CONCEPT = BUNDLE / "computations" / "churn-rate.md"


@pytest.fixture(scope="module")
def attester():
    path = BUNDLE / "references" / "attesters" / "churn_rate.py"
    spec = importlib.util.spec_from_file_location("example_attester", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def concept():
    doc = Document.load(CONCEPT)
    return {**doc.frontmatter, "body": doc.body}


def sanctioned_sql(concept) -> str:
    return (
        "SELECT\n  COUNTIF(cancelled_in_month) / COUNT(*) AS churn_rate\n"
        "FROM billing.subscriptions\nWHERE month_start = @month"
    )


def receipt(sql: str, result: float = 0.023) -> dict:
    return {"job_id": "bq:job:1", "executed_sql": sql, "result": result}


def test_the_sanctioned_query_attests(attester, concept):
    assert attester.attest(concept, receipt(sanctioned_sql(concept)), {"month": "2026-06"}) == []


def test_reformatting_the_sanctioned_query_still_attests(attester, concept):
    """Whitespace and a trailing semicolon are not a different computation."""
    noisy = "  select COUNTIF(cancelled_in_month) / count(*) as churn_rate from "
    noisy += "billing.subscriptions where month_start = @month ;"
    assert attester.attest(concept, receipt(noisy), {"month": "2026-06"}) == []


def test_an_agent_authored_query_is_refused(attester, concept):
    """The whole point: the agent may fill parameters, never write the query."""
    failures = attester.attest(concept, receipt("SELECT 0.01 AS churn_rate"), {"month": "2026-06"})
    assert failures == ["executed_sql is not the sanctioned computation"]


def test_a_widened_query_is_refused(attester, concept):
    """A predicate quietly dropped changes the number without looking like an attack."""
    widened = sanctioned_sql(concept).replace("WHERE month_start = @month", "")
    assert "executed_sql is not the sanctioned computation" in attester.attest(
        concept, receipt(widened), {"month": "2026-06"}
    )


def test_an_undeclared_parameter_is_refused(attester, concept):
    failures = attester.attest(
        concept, receipt(sanctioned_sql(concept)), {"month": "2026-06", "region": "EU"}
    )
    assert failures == ["undeclared parameters supplied: ['region']"]


def test_a_missing_receipt_field_is_refused(attester, concept):
    incomplete = receipt(sanctioned_sql(concept))
    del incomplete["job_id"]
    assert attester.attest(concept, incomplete, {"month": "2026-06"}) == [
        "receipt is missing job_id"
    ]


@pytest.mark.parametrize("result", [1.4, -0.1, "0.02", None])
def test_a_result_that_is_not_a_proportion_is_refused(attester, concept, result):
    failures = attester.attest(
        concept, receipt(sanctioned_sql(concept), result), {"month": "2026-06"}
    )
    assert any("is not a proportion" in f for f in failures)


def test_the_concept_is_a_conformant_okf_document(concept):
    assert concept["type"] == "Attested Computation"
    assert [entry["name"] for entry in concept["parameters"]] == ["month"]
    assert concept["executor"]["receipt"] == ["job_id", "executed_sql", "result"]
