# Paper2Simu v0.6.4-dev — Round 9 integrated local pilot

Display version v0.6.4-dev; Python PEP 440 0.6.4.dev0. Existing PR #39
retains history; no release tag, production upgrade or native run.

Nine integrated workstreams:
1. CheckpointStore: explicit empty genesis enrollment, separate local SQLite
   store, prepare before journal append, finalize after fsync and byte check.
   Pending blocks later writes. Admin must protect DB and supply trusted verifier.
   Database rollback, distributed fencing and pending recovery are not solved.
2. Artifact dependencies: reviewed complete input-key and parent graph,
   digest checks, transitive invalidation and candidate-only carry.
3. Dynamic evidence: retain exact new bytes, additive delta, independent review,
   require a newly approved authority before use. No mutable in-place authority.
4. ResearchTransaction: current checkpoint + existing DAG + readiness/budget
   + maximum three outstanding read-only specialists for candidate proposals.
   No automatic claim or actual call from a candidate.
5. Host observation: existing active-journal bound observation; unsupported
   actual dispatch is explicitly blocked until host enrollment and real ACL.
6. Recovery: existing evidence-based owner reconciliation candidate; no clear.
7. TRACE: existing durable handoff view remains candidate-only; no production used.
8. Cross-host: explicit remote coordination blocker, no distributed grant.
9. Evaluation: deduplicated recorded events; actual host/native/used metrics
   unknown without real source. No claim of measured autonomy improvement.

The first three are local executable components, not production trust services.
The other six compose existing checks and explicit blockers; actual host and
distributed service integration remain required. A00 + A01–A09 responsibilities
and existing scientific threshold/clock/queue/native resource gates unchanged.
No production writers are switched to this pilot. Earlier opt-in APIs remain
available for fixture testing; use ResearchTransaction for this local store.
The store must be independently enrolled, not reconstructed from a suspect
journal. Crash between prepare and finalize keeps pending state and local
reservation, even if journal bytes appear complete. No automatic release.

Round 8 CI failure: existing dispatch takes precedence over exhausted budget
for an already recorded node; zero-budget new dispatch still rejects. Tests
check both. No acceptance threshold changes.

Store-backed append also enforces the three-outstanding-specialist cap inside the shared writer reservation, not merely in candidate selection. Added integration regression for genesis enrollment, actual append, checkpoint finalization, candidate removal and truncated-journal rejection. The authority in that test is synthetic.
