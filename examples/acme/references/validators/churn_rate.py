"""The `rules` block must stay sane, whatever a region overlay believes locally.

Runs against the *resolved* document, so a region overlay cannot evade a rule
its company policy declares: the rule is part of the resolved frontmatter by the
time the validator sees it.
"""

import re

# ISO 4217 alphabetic codes are three uppercase letters. Checking the shape rather
# than an allowlist is deliberate: a hardcoded list of "the currencies we use"
# rejects the next region someone adds, which teaches people to delete the check.
# A real deployment would validate against the published code list.
_ISO_4217 = re.compile(r"^[A-Z]{3}$")


def validate(frontmatter, body):
    failures = []
    rules = frontmatter.get("rules") or {}

    threshold = rules.get("audit_threshold")
    if threshold is not None and (not isinstance(threshold, int) or threshold <= 0):
        failures.append(f"rules.audit_threshold must be a positive integer, got {threshold!r}")

    currency = rules.get("currency_default")
    if currency is not None and not _ISO_4217.match(str(currency)):
        failures.append(f"rules.currency_default must be an ISO 4217 code, got {currency!r}")

    return failures
