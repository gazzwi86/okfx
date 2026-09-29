"""Deterministic check that a reported churn rate came from the sanctioned query.

OKF v0.2 §10.2: an attester takes a receipt and returns a verdict. It runs
consumer-side, contains no model call, and is the reason an agent can be trusted
with a number it did not compute - the agent proposes, this disposes.

OKF §12 defers the attester ABI and the receipt wire format to a future revision,
so the signature below is this bundle's own convention rather than a standard one.
OKFX does not execute attesters; `okfx validate` runs the separate `validation`
family. This file is here because the concept it belongs to is a real, conformant
Attested Computation, not because the CLI will call it.
"""


def attest(concept, receipt, parameters):
    """Return a list of reasons the receipt fails to support the reported value."""
    failures = []

    declared = {entry["name"] for entry in concept.get("parameters") or []}
    supplied = set(parameters)
    if not supplied <= declared:
        failures.append(f"undeclared parameters supplied: {sorted(supplied - declared)}")

    for field in concept.get("executor", {}).get("receipt") or []:
        if field not in receipt:
            failures.append(f"receipt is missing {field}")
    if failures:
        return failures

    # Provenance: the SQL that ran must be the sanctioned computation with only
    # declared parameters bound. Anything else means the agent wrote its own query.
    sanctioned = _fenced_sql(concept.get("body", ""))
    if _normalise(receipt["executed_sql"]) != _normalise(sanctioned):
        failures.append("executed_sql is not the sanctioned computation")

    # Fidelity: a churn rate outside [0, 1] cannot have come from this query.
    result = receipt.get("result")
    if not isinstance(result, (int, float)) or not 0 <= result <= 1:
        failures.append(f"result {result!r} is not a proportion")

    return failures


def _fenced_sql(body):
    inside, lines = False, []
    for line in body.split("\n"):
        if line.strip().startswith("```"):
            if inside:
                break
            inside = True
            continue
        if inside:
            lines.append(line)
    return "\n".join(lines)


def _normalise(sql):
    # rstrip takes a set of characters, so this also clears the space a trailing
    # "... @month ;" leaves behind once the semicolon goes.
    return " ".join(str(sql).split()).rstrip(" ;").casefold()
