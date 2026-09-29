---
type: Metric
extends:
  concept: metrics/churn-rate
target_context:
  region: US
generated: { by: human:gwilliams, at: 2026-06-22T14:00:00Z }
rules:
  audit_threshold: 25000
---
# Audit

Cancellations above the US threshold go to the New York Finance desk within ten
business days.
