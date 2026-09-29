---
type: Attested Computation
title: Churn Rate query
description: The sanctioned way to compute monthly churn rate. An agent supplies
  the month; it never writes the query.
tags: [billing, retention, kpi]
status: stable
runtime: bigquery
parameters:
  - { name: month, type: string, required: true }
executor:
  resource: /references/skills/run-on-bq.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: /references/attesters/churn_rate.py
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-06-19T11:00:00Z }
verified:
  - { by: human:gwilliams, at: 2026-06-20T09:00:00Z }
sources:
  - id: churn-rate-metric
    resource: /metrics/churn-rate.md
    title: Churn Rate
    author: human:gwilliams
    last_modified: 2026-06-18T00:00:00Z
---
# Computation

```sql
SELECT
  COUNTIF(cancelled_in_month) / COUNT(*) AS churn_rate
FROM billing.subscriptions
WHERE month_start = @month
```

The computation binds only the declared `parameters`, and counts a subscriber as
active until the end of the paid period.[^churn-rate-metric]

[^churn-rate-metric]: [Churn Rate](../metrics/churn-rate.md)
