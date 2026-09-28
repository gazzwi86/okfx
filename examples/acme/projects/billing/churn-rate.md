---
type: Playbook
title: Churn Rate in the billing service
description: How the billing service computes and audits EU churn.
tags: [billing, retention, kpi, eu]
id: billing-eu-churn-rate
extends:
  concept: metrics/churn-rate.eu
  integrity: f5a29364125b8bd10c7164e51a9b73ba20ee52923cc6a8ea1bd0083d95e38f24
target_context:
  project: billing
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-07-02T08:15:00Z }
rules:
  currency_default: EUR
  audit_threshold: 2500
---
# Implementation

The `billing-churn` job reads the resolved rules from this bundle rather than a
hard-coded constant, so a change to the EU threshold does not need a code
change.
