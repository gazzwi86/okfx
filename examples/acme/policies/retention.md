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
integrity:
  algorithm: sha256
  value: 2ed217f8f8e3ac8fe0415a7e1adbe5bbf78468a9449a32f6d0afe11e122bfa75
  sealed_by: human:jsmith
  sealed_at: '2026-09-29T04:44:02Z'
---

# Scope

Every subscription product Acme bills for, in every market.

# Cancellation

A cancellation takes effect at the end of the paid period. The subscriber
counts as active until that date.

# Audit

Cancellations above the audit threshold go to the Group Finance desk within ten
working days.
