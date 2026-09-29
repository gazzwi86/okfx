from __future__ import annotations

from pathlib import Path

import pytest
from conftest import write

from okfx import validation
from okfx.document import Document
from okfx.resolve import ResolveError, resolve

PASSING = "def validate(frontmatter, body):\n    return []\n"
FAILING = "def validate(frontmatter, body):\n    return ['retention is too long']\n"
RAISING = "def validate(frontmatter, body):\n    raise RuntimeError('validator is broken')\n"
HANGING = "import time\n\n\ndef validate(frontmatter, body):\n    time.sleep(30)\n    return []\n"
WRONG_SHAPE = "def validate(frontmatter, body):\n    return 'not a list'\n"


def validator(bundle: Path, name: str, source: str) -> str:
    path = bundle / "references" / "validators" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return f"/references/validators/{name}"


def doc_with(bundle: Path, resource: str, body: str = "") -> Document:
    path = write(
        bundle / "concept.md",
        f"type: Policy\nvalidation:\n  - resource: {resource}\n    description: A check.",
        body,
    )
    return Document.load(path)


def test_a_passing_validator_reports_nothing(bundle: Path):
    doc = doc_with(bundle, validator(bundle, "ok.py", PASSING))
    assert validation.run(doc, allow=True) == []


def test_a_failing_validator_reports_its_messages(bundle: Path):
    doc = doc_with(bundle, validator(bundle, "fail.py", FAILING))
    failures = validation.run(doc, allow=True)
    assert [f.message for f in failures] == ["retention is too long"]


def test_a_validator_that_raises_is_a_failure_not_a_silent_pass(bundle: Path):
    doc = doc_with(bundle, validator(bundle, "raise.py", RAISING))
    failures = validation.run(doc, allow=True)
    assert len(failures) == 1
    assert "validator is broken" in failures[0].message


def test_a_validator_that_hangs_times_out_as_a_failure(bundle: Path):
    doc = doc_with(bundle, validator(bundle, "hang.py", HANGING))
    failures = validation.run(doc, allow=True, timeout=1.0)
    assert len(failures) == 1
    assert "timed out" in failures[0].message


def test_a_validator_returning_the_wrong_shape_is_a_failure(bundle: Path):
    doc = doc_with(bundle, validator(bundle, "shape.py", WRONG_SHAPE))
    failures = validation.run(doc, allow=True)
    assert len(failures) == 1
    assert "list of strings" in failures[0].message


def test_a_missing_validator_is_an_error(bundle: Path):
    doc = doc_with(bundle, "/references/validators/nowhere.py")
    with pytest.raises(validation.ValidationError, match="does not exist"):
        validation.run(doc, allow=True)


def test_validators_are_refused_unless_the_caller_opts_in(bundle: Path):
    doc = doc_with(bundle, validator(bundle, "ok.py", PASSING))
    with pytest.raises(validation.ValidatorsRefused, match="arbitrary Python"):
        validation.run(doc)


def test_the_environment_variable_is_also_an_opt_in(bundle: Path, monkeypatch):
    monkeypatch.setenv("OKFX_ALLOW_VALIDATORS", "1")
    doc = doc_with(bundle, validator(bundle, "ok.py", PASSING))
    assert validation.run(doc) == []


def test_a_document_declaring_nothing_needs_no_opt_in(bundle: Path):
    path = write(bundle / "plain.md", "type: Policy")
    assert validation.run(Document.load(path)) == []


def test_an_overlay_cannot_evade_a_rule_its_base_declares(bundle: Path):
    resource = validator(bundle, "fail.py", FAILING)
    write(
        bundle / "base.md",
        f"type: Policy\nvalidation:\n  - resource: {resource}\n    description: A check.",
    )
    overlay = write(bundle / "overlay.md", "type: Policy\nextends: {resource: /base.md}")
    resolved = resolve(Document.load(overlay))
    failures = validation.run(resolved, allow=True)
    assert [f.message for f in failures] == ["retention is too long"]


def test_the_example_validator_runs_against_the_resolved_document(example_project: Path):
    """An overlay cannot evade a rule its base declares: the rule is inherited."""
    doc = resolve(Document.load(example_project))
    assert "/references/validators/churn_rate.py" in [
        entry["resource"] for entry in doc.frontmatter["validation"]
    ]
    assert validation.run(doc, allow=True) == []
    doc.frontmatter["rules"]["audit_threshold"] = -1
    failures = validation.run(doc, allow=True)
    assert len(failures) == 1
    assert "must be a positive integer" in failures[0].message


def test_the_example_validator_checks_currency_shape_not_an_allowlist(example_project: Path):
    """A hardcoded list of "our" currencies rejects the next region someone adds."""
    doc = resolve(Document.load(example_project))
    for accepted in ("EUR", "SGD", "ZAR"):
        doc.frontmatter["rules"]["currency_default"] = accepted
        assert validation.run(doc, allow=True) == []
    for refused in ("EURO", "usd", "$", 42):
        doc.frontmatter["rules"]["currency_default"] = refused
        failures = validation.run(doc, allow=True)
        assert len(failures) == 1, refused
        assert "ISO 4217" in failures[0].message


def test_a_validator_outside_the_bundle_is_refused(bundle: Path, tmp_path: Path):
    """Validators are executed, so this is the escape that matters most."""
    (tmp_path.parent / "evil.py").write_text("def validate(f, b):\n    return []\n", "utf-8")
    doc = Document.load(
        write(
            bundle / "a.md",
            "type: Policy\nvalidation:\n  - resource: ../evil.py\n    description: X.",
        )
    )
    with pytest.raises(ResolveError, match="leaves the bundle"):
        validation.run(doc, allow=True)
    assert validation.run(doc, allow=True, allow_outside=True) == []
