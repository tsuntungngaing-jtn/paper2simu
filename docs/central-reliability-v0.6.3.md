# Central reliability revision (display version 0.6.3)

PC8 and PC10 feedback: preserve native admission, Case Clock, historical ledger,
unique Executor, frozen paper targets and P2S-DATA-1.0. These are staged offline
helpers, not proof of deployment.

- CLI: preserve known PID on exception, persist spawn intent and observed PID,
  strict single-turn parser and read-only --inspect. PID is not a creation
  identity. Crash between spawn and receipt remains unresolved. Do not unlock
  or move the state directory; full trusted OS observation/release remains open.
- TRACE: explicit artifact/consumer linkage via server.trace_evidence. Local
  collectors must migrate separately; no inferred adoption or historical
  fabrication. The source release and installer include the companion Skill.
- Deployment: server.deployment_identity.verify compares declared component
  files against independently approved hashes and commit. Matching files does
  not prove loaded process identity. Do not inventory credentials.
- Task graph, scoped refresh, actual dispatch and stdio host tests remain open.
  Do not bypass existing safety gates. Preserve original plan and journal.

Acceptance: focused offline and full Linux/Windows CI, packaged companion
presence, then actual host tests. Local adapter repair, CLI reconciliation,
real stdio, actual role ACL, native hard deadlines and cross-night verification
remain NOT_RUN. Pending checks only block dependent work.

## Task and stdio integration

- Opt-in work_schema work-nodes/2 on existing task-plan.json: id, action,
  owner_role A00–A09, operation_scope, depends_on, failure_edges,
  completion_evidence, resource_domain, revision_binding, attempt_budget.
  Existing requires_submission and requires_idle_solver remain in force.
  Split read-only diagnostics from submission. Validate normal and failure
  graphs; reject failure paths waiting on the failed node. Do not force old
  plans to become invalid; migrate approved revisions preserving original events.
- research_resume renders stable recovery candidates when a blocker has a
  persistent incident_id and node resource_domain. Candidate is read-only
  diagnostic work, not permission to execute its proposed next action.
  Actual host must verify scope, dispatch real worker, approve node and
  record evidence in original journal. No autonomous dispatch is implemented.
- server.task_liveness.repeated_observations compares verified normalized
  business states; timestamps and trace IDs do not reset progress. This helper
  needs actual host integration and does not affect Case Clock or stopping.
- server.stdio_diagnostics.classify classifies supplied tri-state evidence,
  never starts a provider. See [Fluent stdio evidence](fluent-stdio-initialization.md).
- Existing composite refresh remains conservative until trusted action-scope
  adapter is verified. Read-only local diagnosis must not depend on solve
  authorization. Historical claim release and cross-host ownership stay guarded.
