---
okf_version: "0.2"
---

# Policies

* [Subscriber Retention Policy](policies/retention.md) - how Acme measures, reports and audits cancellations, company-wide.

# Metrics

* [Churn Rate](metrics/churn-rate.md) - the metric, defined once. Sealed, and declares a validator.
* [Churn Rate (EU)](metrics/churn-rate.eu.md) - the EU overlay: EUR, and a lower audit threshold.
* [Churn Rate (US)](metrics/churn-rate.us.md) - the US overlay, inheriting the base currency.
* [Churn Rate (AU)](metrics/churn-rate.au.md) - the AU overlay, with a pinned base and its own provenance.

# Computations

* [Churn Rate query](computations/churn-rate.md) - the sanctioned computation. An agent supplies the month and never writes the query.

# Projects

* [Churn Rate in billing](projects/billing/churn-rate.md) - the project implementation, three levels down.

# References

* [Running a computation on BigQuery](references/skills/run-on-bq.md) - what a runner does and what it must return.
* [Attesters](references/attesters/) - deterministic receipt checks.
* [Validators](references/validators/) - deterministic document checks the concepts above declare.
