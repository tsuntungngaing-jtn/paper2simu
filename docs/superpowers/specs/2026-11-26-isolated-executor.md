# Independent executor integration design

Status: APPROVED_WITH_AMENDMENTS (2026-11-26). Implementation plan: ../plans/2026-11-26-isolated-executor.md.

Adapt the recovered Windows supervisor behind Runtime, with an explicit shared coordination store and fail-closed admission. Keep version 0.6.1 and Orchestrator plus nine roles.

## Source verification
- Baseline: 44c8b9a404f3a28d104815e5f5c9ebe23b3c9735.
- Recovered executor: 421f3ba8ff809411907f8292cd09bd1044b8f409.
- Original archive: Paper2Simu-Isolated-Executor-Integration-Patch.zip.
- ZIP SHA256: 088f9a98bf9cd4241c4dc337d1c2c2515dd374b97ad542074f89bf2a82b5c2d6.
- integration.patch SHA256: f2f8df194cf628951e6655dbe950949940f19649378ca8b3bb3f2be8f9f23413.
- All 18 archive checksum entries verified; the three recovered executor Git blobs match the candidate source. Windows checkout newline conversion explains working-file hash differences.
- Historical baseline CI succeeded, but is not integration validation. Archive native evidence is historical and excluded from acceptance.

## Required architecture and amendments
Explicit local coordination database and resource identity, shared by all participating Runtime instances and output roots. A single durable owner reserves a resource; missing/corrupt state, unknown ownership and unresolved history block submission. All native Runtime entry points, not just solves, participate. Reservation, launch authorization, process creation, stopped observation and release are distinct durable boundaries. No timeout reclaims a claim.

Case Clock is authoritative. Freeze case deadline, solve deadline and wrap boundary. Bind each case to its original clock path and immutable budget in the resource ledger. Restart, reconnect, replay or another output root cannot rebase it. Polls/heartbeats never refresh progress. Trusted operator progress records are distinct from provider-verified progress; no automatic log parser is advertised.

Verification uses existing independent multi-agent and evidence gates plus actual operator opt-in, configured Executor identity, resource ownership and current budgets. Bind reviewed receipts to operation, case, source SHA256, study, cores, resource, executor and absolute deadlines. Recheck before native creation and resume; hold an immutable Windows input snapshot handle until the owned job is closed. Offline candidate evidence alone never grants provider authority.

Windows detached supervisor owns only its creation-time-assigned Job Object. Record stop requests separately from zero-active-process stop observations, wrapper exit status, task exit and scientific acceptance. Unknown state retains resources; no arbitrary PID cleanup. Shared JVM hard deadlines remain unsupported.

## Validation and delivery
Keep existing tests; add fault injection and controlled Windows tests. Full Linux and Windows regression, nonzero focused tests, Verification-Driven Gate, source/wheel/ZIP completeness and independent review must refer to the final candidate commit. Commit/push feature branch and create PR, no main merge.

No P025, production deployment, commercial solver test or service restart. Native deadline accuracy, real disconnect/crash recovery, scientific result and MPH reopen acceptance remain NOT_RUN.
