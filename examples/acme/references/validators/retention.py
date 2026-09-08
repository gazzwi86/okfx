"""Retention windows must be sane, whatever a project believes locally.

Runs against the resolved document, so a project overlay cannot evade the rule
its company policy declares.
"""


def validate(frontmatter, body):
    failures = []
    retention = frontmatter.get("retention") or {}
    for key, value in retention.items():
        if not isinstance(value, int) or value <= 0:
            failures.append(f"retention.{key} must be a positive integer, got {value!r}")
    records = retention.get("customer_records_days")
    logs = retention.get("access_logs_days")
    if isinstance(records, int) and isinstance(logs, int) and logs > records:
        failures.append(
            f"access logs ({logs} days) are kept longer than customer records ({records} days)"
        )
    return failures
