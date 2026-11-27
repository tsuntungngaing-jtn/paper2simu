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


## PC8 Round 3 revision (display version 0.6.3)

Isolated provider handshake and session_status succeeded with native
connected=false; actual Desktop still failed initialization. Separate lanes.
Bind host/turn/provider and when available launch/origin in retained receipts;
first_missing_stage and first_failed_stage are independent. Replay is not
live host capture.

Legacy audit preserves physical lines and overlapping possible-native markers.
Use python scripts/research_resume.py legacy-preview PLAN JOURNAL for read-only
JSON output. unresolved_native is a review list, never a submission count or
resource release. Strict completion requires retained artifact bytes and
review-bound artifact_sha256 for all refs. refresh accepts review_context
via trusted calling code; no untrusted auto-discovery. Worker authentication,
full migration and scheduled host integration remain open.

Incident projection replays lifecycle events in existing journal, preserves
one node budget across recurrence, rejects duplicate generations. Caller must
authenticate source, review and original budget. No execution authorization.

CLI verify_chain checks intent/spawn/exit/events, links and independent anchor.
inspect_state reports conservative inspection without anchor. No release,
process kill or native terminal inference.

Release shares one path predicate and requires both Skills. Git byte/path
checking is not signed issuance or actual loaded identity.

Open: real production telemetry and ACL, dispatch engine, authorized
cross-thread handoff, legacy migration, cross-host ownership, native
reconciliation/release and production liveness normalization.
All original scientific gates and resource claims remain unchanged.


## Round 4 counterexamples

Strict completion requires a reviewed, nonempty required_artifacts list on the
node; all IDs must appear in the independent review and retained bytes. Legacy
plans without that structured manifest remain readable but cannot claim strict
completion until reviewed mapping is provided. No parsing prose into authority.
Incident events must bind task_id, resource, node and revision. The existing
resume renderer passes the original journal to recovery_candidates; a closed,
stale or exhausted generation cannot propose another attempt. Legacy candidates
without lifecycle evidence remain diagnostic mapping proposals only.
Even legacy stdio context cannot mix different declared launches or origins;
missing scope remains UNKNOWN. Isolated and production readiness stay separate.
The runtime failure-evidence race is addressed by persisting job-error.json
before publishing failed status; explicit evidence write failures are reported.

Round 4 prototype is a design input, not production code. Manual dispatch
positive control and synthetic admission/handoff do not prove host ACL, actual
cross-thread used, cross-process CAS or native ownership. Future dispatch
requires single authoritative journal, stable event IDs and serialized claims
across revisions; do not adopt the prototype's in-process lock or transient
deduplication as production guarantees. Existing native gates remain unchanged.

## Local read-only dispatch architecture pilot

See [read-only dispatch pilot](readonly-dispatch-pilot.md). This is a minimal cooperating local writer and replay contract, not production deployment. It excludes native actions, preserves the original journal and requires authenticated host/ACL and dependency callbacks. Cross-thread handoff remains a pilot view, not a verified production TRACE used edge. No automatic retry or lock release.


## Round 5 counterexamples

R5-01: reject journals with hard links or unknown file identity. Record local
reservation metadata before append, preserve unknown locks. No network
filesystem or cross-host guarantee.
R5-02/03: strict completion now requires independently pinned plan/index
digests and explicit trusted authority callback; completion proposal/review
bind the full plan digest. Legacy unsigned completion remains a mapping
gap, not verified. Incident structural replay without authority labels review
UNKNOWN; optional verified incident review context checks retained scoped
receipt. A structural closure can suppress a candidate but cannot authorize
recovery. Actual source/issuer and production integration remain BLOCKED.
R5-04/05/06: dispatch append checks original journal readiness inside CAS,
rejects native scope and wrong/expired/self-issued grants, binds both sides
of handoff and rejects cross-revision. Trusted callback and actual Provider
ACL are still separate requirements. No production activation.
R5-07/08: reservation diagnostics only; full process birth, reconciliation,
multi-writer cross-revision transactions and carry-forward remain open.

## Round 7 local architecture

Shared CAS writer for dispatch and opt-in revision activation, immutable task-wide controls, cumulative dispatch attempts, old segment retention, unresolved-dispatch guard and reviewed carry candidates only. See [revision transactions pilot](revision-transactions-pilot.md). Reservation inspection does not release; host observation is an injected read-only contract, not a Codex adapter. No native or production migration.

## Round 8 (Round 6 feedback)

R6-01/02/03: require externally verified exact journal checkpoints for all pilot appends, check single-plan budget, reverify historical grant/event/artifact receipts. The callback remains an external trust boundary, not a production issuer. R6-05/06: exact expected serialized tail digest, semantic-only legacy classification, externally anchored owner reconciliation candidate; no lock release. R6-07: active anchored journal and fresh monotonic observation scope. R6-04/08/09/10 remain separate migration, dynamic evidence staging, scientific dependency and liveness work. No native migration or new authority.
