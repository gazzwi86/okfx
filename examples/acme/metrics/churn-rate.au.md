---
type: Metric
extends:
  resource: churn-rate.md
  integrity: fc1702e0ed2792f4ae39a247a7f181b41b989f4b14e47ddba183c09deb40a1a5
target_context:
  region: AU
generated: { by: human:gwilliams, at: 2026-06-22T14:00:00Z }
rules:
  currency_default: AUD
  audit_threshold: 15000
---
# Audit

Cancellations above the AU threshold go to the Sydney Finance desk within five
working days, per AUSTRAC reporting obligations.
