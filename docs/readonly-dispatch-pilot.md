# Read-only dispatch pilot (v0.6.3)

Opt-in local architecture experiment. It is NOT a production host adapter,
real ACL, native admission or automatic dispatch. The host must supply actual
authenticated receipts and dependency admission; missing integration is BLOCKED.

server.readonly_dispatch.snapshot reads the original journal and returns its
SHA-256 and events. append_event takes that expected digest and an actual
event projection bound to independently indexed retained receipt bytes.
A canonical adjacent writer-reservation directory serializes cooperating local
processes. A stale digest rejects append. A crash or uncertain write retains
reservation; never delete it to retry. All writers, including the original
trial writer, must cooperate before using this in production. Network shares,
multiple hosts, aliases, actual host authentication and ACL are NOT_RUN.

States: INTENT -> DISPATCHED -> CLAIMED -> RUNNING -> OUTPUT_RECORDED.
FAILED or OUTCOME_UNKNOWN do not permit silent redispatch. The host records
intent before a supported dispatch, then actual ack, claim and run receipts.
This pilot does not call the host itself; the callback must attest each exact
operation, worker, role, scope, expiry and actual read-only ACL. Native scopes
and A04 are excluded. ready_check must enforce original verified dependency
and blocker state. No work_completed event is generated: existing strict
completion and independent scientific acceptance remain authoritative.
No retry or cross-revision migration in this pilot.

Cross-thread handoff view binds actual producer/consumer dispatch, worker and
thread, recorded artifact digest, explicit ADOPTED and independent reviewer.
Append verifies retained bytes and separate send/read/review receipts with
exact handoff binding via trusted verifier. Journal replay deduplicates edges.
It does NOT promote these edges to the existing TRACE used view or claim
host authenticity; real source authentication/authorized cross-thread
integration remain open. HOLD/REJECTED/UNKNOWN are not adopted events.

Tests are synthetic receipt positive/negative cases and local two-process
contention using the same journal. No commercial solver is used. Before
production: test actual host calls, cross-revision plan history, failure
reconciliation, shared resource domains and original writer integration.
