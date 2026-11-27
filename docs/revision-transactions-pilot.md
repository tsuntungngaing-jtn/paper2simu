# Round 7: local revision transactions and reconciliation (v0.6.3)

This is an opt-in local read-only pilot. All journal writers must cooperate
with the same canonical reservation; no production scheduler migration.

RevisionHistory pins genesis digest and retains full plan objects by canonical
SHA-256. A trusted external verifier must approve genesis and every exact
activation receipt. activate_revision writes one revision_activated event using
the same CAS/reservation primitive as dispatch append. The old plan and events
remain in the original journal; old dispatches are partitioned for audit.
New dispatches require the explicit history, current digest and remaining
original attempt budget. Node identity, roles, domains, budget and task-wide
fields cannot change. No automatic new node or native migration. Every node
must have a fresh revision identity. Unresolved dispatch blocks activation.
Legacy, native, incident and prior work review events require separate
migration/reconciliation rather than filtering. Carries are retained evidence
candidates only, never completion or TRACE used. A new independent review is
required. No automatic retirement of actual native work.

inspect_reservation is strictly read-only: reports original prefix match,
partial tail, intended event match, unexpected tail or unknown. Captures own
Windows creation time / Linux boot and start ticks where available. Owner
liveness and independent approval are not inferred. No lock removal or
native release even with matching bytes. Crash before metadata remains unknown.

observe_dispatch accepts a supported read-only observer callback only after
binding call registration and permission to task/node/plan/worker/thread.
No Codex endpoint, automatic dispatch, actual host ACL or native admission is
implemented. A returned observation is not task completion. Without an
adapter returns BLOCKED_HOST_ADAPTER. Synthetic receipts remain synthetic.

Tests cover stale plan, cumulative attempts, changed budget, native history
refusal, two process activation CAS, read-only reservation inspection, and
host observation scope. Actual host, multi-machine and native gates remain
unvalidated.
