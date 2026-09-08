---
type: Policy
title: Customer data handling
description: How Acme handles customer data, company-wide.
tags:
- policy
- data-handling
status: stable
generated:
  by: human:ahormati
  at: '2026-01-14T09:00:00Z'
verified:
  by: human:ahormati
  at: '2026-01-16T09:00:00Z'
target_context:
  org: acme
retention:
  customer_records_days: 2555
  access_logs_days: 90
validation:
- resource: /references/validators/retention.py
  description: Retention windows are positive integers and access logs are kept no
    longer than records.
integrity:
  algorithm: sha256
  value: cb48b2b365caf6feab7d18757e4e99cc9f188c04c82eb50a7f2872aa11b0b867
  sealed_by: human:ahormati
  sealed_at: '2026-01-16T09:00:00Z'
---

# Scope

This policy covers every system that stores customer data, in any environment.

# Retention

Customer records are retained for seven years. Access logs are retained for
ninety days.

# Access

Access to customer data is granted per role, reviewed quarterly.
