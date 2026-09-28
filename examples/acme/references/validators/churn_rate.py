"""The `rules` block must stay sane, whatever a region overlay believes locally.

Runs against the *resolved* document, so a region overlay cannot evade a rule
its company policy declares: the rule is part of the resolved frontmatter by the
time the validator sees it.
"""

_ISO_4217 = {"USD", "EUR", "GBP", "AUD", "JPY", "CAD", "CHF", "SEK", "NOK", "NZD"}


def validate(frontmatter, body):
    failures = []
    rules = frontmatter.get("rules") or {}

    threshold = rules.get("audit_threshold")
    if threshold is not None and (not isinstance(threshold, int) or threshold <= 0):
        failures.append(f"rules.audit_threshold must be a positive integer, got {threshold!r}")

    currency = rules.get("currency_default")
    if currency is not None and currency not in _ISO_4217:
        failures.append(f"rules.currency_default must be an ISO 4217 code, got {currency!r}")

    return failures
