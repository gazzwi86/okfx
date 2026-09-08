---
type: Playbook
title: Customer data handling in the ledger service
description: How the ledger service implements the finance interpretation of the data
  handling policy.
tags:
- policy
- data-handling
- finance
- ledger
id: ledger-data-handling
generated:
  by: reference_agent/gemini-2.5-pro
  at: '2026-03-09T16:20:00Z'
target_context:
  project: ledger
retention:
  access_logs_days: 400
extends:
  resource: /domains/finance.md
  integrity: 80a7d8fffb4021783af497525eb358b2802d6e21c4d2c2958e49ef762abaa28c
integrity:
  algorithm: sha256
  value: a6e79f25a853657b8a3d75fd5c2dcb2112ee1f8c193da61f4f954bd620f31bf8
  sealed_by: reference_agent/gemini-2.5-pro
  sealed_at: '2026-03-09T16:25:00Z'
---

# Retention

Ledger access logs are retained for four hundred days: a year of regulatory
window plus the thirty-five day settlement tail.

# Implementation

Retention is enforced by the `ledger-retention` job, which reads the resolved
policy from this bundle rather than from a hard-coded constant.
