---
type: Metric
extends:
  concept: metrics/churn-rate
target_context:
  region: EU
rules:
  currency_default: EUR
  audit_threshold: 5000
---
# Audit

Cancellations above the EU threshold go to the Dublin Finance desk within 72
hours, per local reporting obligations.
