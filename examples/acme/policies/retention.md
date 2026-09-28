---
type: Policy
title: Subscriber Retention Policy
description: How Acme measures, reports and audits subscriber cancellations.
tags:
- billing
- retention
- policy
status: stable
generated:
  by: human:jsmith
  at: '2026-06-15T00:00:00Z'
verified:
- by: human:jsmith
  at: '2026-06-15T00:00:00Z'
target_context:
  org: acme
rules:
  currency_default: USD
  audit_threshold: 10000
validation:
- resource: /references/validators/churn_rate.py
  description: Audit thresholds are positive integers and currencies are ISO 4217
    codes.
integrity:
  algorithm: sha256
  value: f4f127378ea5371f696ed72ea3073a66b3b4250bf4ea56df4eabc8379faa94e6
  sealed_by: human:jsmith
  sealed_at: '2026-09-28T04:43:14Z'
---

# Scope

Every subscription product Acme bills for, in every market.

# Cancellation

A cancellation takes effect at the end of the paid period. The subscriber
counts as active until that date.

# Audit

Cancellations above the audit threshold go to the Group Finance desk within ten
working days.
