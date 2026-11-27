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


## PC8 PR39 feedback follow-up

- migration_preview takes explicit reviewed metadata for existing legacy IDs,
  preserves existing gates and refuses missing/conflicting metadata. No write.
  Renderer exposes missing resource/incident mapping; strict completion
  requires current revision and review receipt. An omitted paper node must be
  proposed under the original authorized task, not guessed from a report.
- Liveness normalizes set-like fields independent of list order/duplicates.
- Windows CLI records creation FILETIME through its owned Popen handle when
  available and a separate exit receipt. Unknown creation identity and
  spawn/receipt crash gaps still block; no automatic or forced clear.
- receipt_evidence supports independently indexed retained redacted JSON
  bytes; TRACE replay requires exact event projection; stdio replay requires
  same host/turn/provider and rejects conflicting observations. These are
  replay adapters, not live host capture or authentication.
- ZIP manifest now contains build_protocol, source_commit and source_binding.
  Exact published bytes are checked against Git blob hashes. Non-Git and
  changed/CRLF-transformed sources are explicitly not exact-bound.
  This is not a signed release or proof of runtime loading.
- Actual PC8 host adapter, original task migration, original TRACE collector,
  actual loaded deployment identity, CLI hard crash reconciliation, native
  attachment, ACL and production migration remain NOT_RUN.


## PC8 Round 2 counterexample revision

- Legacy mixed logs: use research_resume.legacy_journal_preview to inventory
  raw lines by hash, unknown event type, unknown node, missing evidence and
  native reconciliation requirement. It is deliberately read-only and never
  substitutes a filtered legacy log for the authoritative journal. Independently
  approve mapping and replay through the existing writer; no fabricated work
  completions. Strict work completion requires review_context (retained root
  and separately approved index); exact task/node/revision/evidence, decision,
  role and distinct worker IDs must match. The host still authenticates identities
  and the index. Existing strict refresh without a review context fails closed.
- Recovery key uses stable reviewed incident ID, task, resource and node,
  excluding mutable classification. Suppress earlier generated IDs as well.
  Host incident lifecycle, recurrence generations and bounded attempt execution
  remain open; never invent aliases or reset budgets.
- Production observations use observation_replay with original turn IDs, one
  final observation per turn, stable state codes and independently verified
  milestone IDs. Free-text descriptions are excluded; conflicts reject replay.
  Legacy repeated_observations is a low-level comparator, not production proof.
- TRACE replay requires thread identity; cross-thread consumption is rejected
  until an authorized handoff contract exists. Empty/ignored input does not
  verify bytes; expose counts. Structural checks do not authenticate a host.
- stdio replay preserves known failed stages even if an earlier stage is
  unknown. An empty chain cannot verify bytes. Do not promote a host-reported
  initialize error into a confirmed process exit or native diagnosis.
- CLI exit receipt binds spawn digest and observed creation identity; spawn
  binds intent digest. No automatic release or native claim changes.
- Release source binding checks the complete Git-tracked publication path set,
  not just the supplied files. Still not a signed release, approved deployment
  inventory, or actual loaded identity.

No live host capture, real ACL, production legacy mapping, actual agent claim
engine, cross-host transfer, or evidence-based reservation release is supplied
by this revision. Native tests and PC8 Fluent recovery remain open.
