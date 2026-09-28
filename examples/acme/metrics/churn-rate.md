---
type: Metric
title: Churn Rate
description: Percentage of subscribers who cancel their service per month.
tags:
- billing
- retention
- kpi
status: stable
generated:
  by: reference_agent/gemini-2.5-pro
  at: '2026-06-18T10:30:00Z'
verified:
- by: human:gwilliams
  at: '2026-06-20T09:00:00Z'
stale_after: '2026-12-31T00:00:00Z'
sources:
- id: retention-policy
  resource: /policies/retention.md
  title: Subscriber Retention Policy
  author: human:jsmith
  last_modified: '2026-06-15T00:00:00Z'
validation:
- resource: /references/validators/churn_rate.py
  description: Audit thresholds are positive integers and currencies are ISO 4217
    codes.
rules:
  currency_default: USD
  audit_threshold: 10000
integrity:
  algorithm: sha256
  value: fc1702e0ed2792f4ae39a247a7f181b41b989f4b14e47ddba183c09deb40a1a5
  sealed_by: human:gwilliams
  sealed_at: '2026-09-28T04:43:14Z'
---

# Definition

Subscribers who cancel in a calendar month over active subscribers at month
start.[^retention-policy]

[^retention-policy]: [Subscriber Retention Policy](../policies/retention.md)
