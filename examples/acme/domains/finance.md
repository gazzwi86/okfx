---
type: Policy
title: Customer data handling in Finance
description: The finance interpretation of Acme's customer data handling policy.
tags:
- policy
- data-handling
- finance
generated:
  by: human:fmarcus
  at: '2026-02-02T11:00:00Z'
target_context:
  domain: finance
retention:
  access_logs_days: 365
extends:
  resource: /policies/data-handling.md
  integrity: cb48b2b365caf6feab7d18757e4e99cc9f188c04c82eb50a7f2872aa11b0b867
integrity:
  algorithm: sha256
  value: 80a7d8fffb4021783af497525eb358b2802d6e21c4d2c2958e49ef762abaa28c
  sealed_by: human:fmarcus
  sealed_at: '2026-02-02T11:05:00Z'
---

# Access

Access to customer data in finance systems is granted per role and reviewed
monthly, and every grant is recorded against a change ticket.

# Regulatory basis

Finance retains access logs for a year to satisfy the audit trail its
regulators require.
