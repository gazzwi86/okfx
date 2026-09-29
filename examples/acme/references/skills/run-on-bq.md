---
type: Reference
title: Running a sanctioned computation on BigQuery
description: How a runner executes an Attested Computation and what it must return.
status: stable
---
# Procedure

1. Read the concept's `# Computation` fence. Do not edit it.
2. Bind each value the caller supplied to the matching entry in `parameters`, as
   a BigQuery named parameter. Refuse any value whose name is not declared.
3. Submit the query and wait for it to finish.

# Receipt

Return exactly the fields the concept's `executor.receipt` names:

- `job_id` - the BigQuery job, so the attester can re-read the run rather than
  trust this response.
- `executed_sql` - the SQL the service actually ran.
- `result` - the value being reported.
