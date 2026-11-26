# Runtime reliability v0.6.1

## Scope and boundaries

The 23 November reported local isolated COMSOL executor is not present in the examined public v0.4.0 or v0.6.0 runtime. The shared JVM still advertises running_stop and deadline_enforcement unsupported. Do not pretend a clock or a local HTTP response repairs that. Keep the existing 1+9 roles, native writer restriction, evidence-bound gate and independent acceptance. Real COMSOL/Fluent and scheduled desktop validation NOT_RUN.

## Five-layer diagnosis

1. Transport: identify actual registered loopback HTTP endpoint; python -m server.reliability loopback <uncredentialed URL> makes one direct GET without proxy or redirect, with timeout. localhost probe uses IPv4; test exact registered IP separately when IPv6 is needed. A 401/405 may show HTTP reachability, not MCP initialization. For a 502 compare timestamped proxy log, actual client response and direct response. No broad proxy exception or security disabling; use only authorized exact local configuration. No automatic environment edits.
2. MCP: actual tool discovery and read-only call in the affected scheduled context. If client refresh is unavailable, preserve job IDs and request an authorized client reload; leave native solver and active jobs alone.
3. Runtime: capture current comsol_queue_status and comsol_execution_capabilities. Compare runtime version, checkout, interpreter, output root, runtime source hash and runtime ID. Expected fingerprint must come from independently approved deployment, not be copied from observed values. Use python -m server.reliability compare expected.json receipt.json. Expected keys: paper2simu_version, runtime_root, python_executable, output_root, runtime_source_sha256, optional runtime_id, max_age_seconds (default 60, <=300), require_hard_deadline (defaults to required). Receipt keys: observed_at_unix, tool_count, read_only_ok, queue, capabilities_response, native_identity_verified, native_evidence_ref, optional original_operation_id and original_job, and native_deadline_test_ref for a claimed hard stop. Record actual source, time and scope in private audit. METADATA_CANDIDATE is a declared offline comparison, not proof of native authority or trusted receipt provenance. Recheck live before mutation; malformed inputs are blocked/errors, never approval.
4. Native: confirm original session, model and endpoint with actual readback when idle; JVM_BUSY means defer native read and poll metadata. A separate CLI's success cannot verify desktop scheduled context. For Fluent use its actual official provider, no assumptions about COMSOL interfaces.
5. Job: reconcile original job_id and operation_id with original output root and native observations. Missing records are unknown. Existing idempotent receipts remain retrievable even when new work is blocked.

## Persistent case clock and task budget

The task prompt sets budgets, not the release. All numbers here are illustrative for the user's current 240/150/15/30 minute task. On the trusted local host, set PAPER2SIMU_REQUIRE_CASE_CLOCK=1 in the actual connector launch environment, preserve COMSOL_OUTPUT_ROOT. Initialize the case clock in that same output root (case-clock.sqlite3). The runtime also enforces a clock already present there, even without the flag. Use a single authorized owner per output root; this is not a malicious-client security boundary.

Example commands (seconds; replace paths/IDs):

    python -m server.case_clock --db <output-root>/case-clock.sqlite3 start P008-c1 --total 14400 --wrap 1800 --solve 9000 --stall 900
    python -m server.case_clock --db <output-root>/case-clock.sqlite3 status
    python -m server.case_clock --db <output-root>/case-clock.sqlite3 watch P008-c1 --interval 30 --max-seconds 14400

Default requires hard deadline. --allow-soft is an explicitly different, user-authorized task policy; never use it to silently bypass hard deadline. Runtime submit_case/submit_study accept task_case_id (MCP comsol_run_case, study_solve, study_solve_async). When required, missing DB, wrong case, expired/closed case or hard-required case on shared JVM blocks new submissions before spending submission budget. Existing stable operation receipts can still be recovered. Always use the original task ID and operation ID; no new ID to evade unresolved history.

Case start is immutable; restart with same ID and values returns original start, not a fresh budget. A new case cannot start until old clock exits. A persistent UTC high-water timestamp detects observed backward clock movement, not all clock tampering; stable system time and local supervision required. EXIT latches at no verified progress, wrap window, deadline or explicit authorized close. For a 240 minute case the new-work cutoff is 210 minutes; 15 minutes is the maximum age of verified progress, not a declaration of solver stall. Only trusted new substantive evidence can advance progress:

    python -m server.case_clock --db <output-root>/case-clock.sqlite3 observe P008-c1 <sha256-of-new-progress-artifact> <actual-observation-unix-seconds>

Do not use polling timestamps, old logs, heartbeat or rewritten evidence to reset progress. The clock rejects duplicate hashes, future/stale observations, and observations after exit. Hash matching is not independent native verification. The clock exposes solve_limit_seconds but does not enforce the running solve cap; a host must compare actual job times and available time before submitting. The watch command is a bounded independent clock observer; it prints status and exits, does not launch/kill processes, acquire native logs, or prove a native job stopped. It needs a real running local scheduler/operator and cannot survive host power loss. Record native stop status separately. Do not use a 20-minute LLM schedule as precise 15-minute supervision.

## Unresolved job admission and recovery

Queue rejects new operations if journal errors or recovery_pending remain. Idempotent matching original receipt lookup still works. This is intentionally conservative across the output root. Do not erase, rename or move unresolved journals to bypass. No new remote reconciliation override is introduced: authorized operator must independently verify original native terminal state and archive/resolve according to existing recovery protocol; if unavailable, HOLD and continue independent document work. No assumption that an empty active list means the old native worker stopped. No global COMSOL/Fluent restart or process kill.

The queue guard controls queue entry, not every arbitrary native API mutation or already running job. Continue using v0.6.0 host admission and unique writer; apply case phase to all new repair/build/mutation decisions at host. The user-specified hard deadline must remain blocked until a verified isolated provider and stop mechanism are recovered. Do not claim that 150-minute solve cutoff or 240-minute hard native stop has been implemented.

## Rollout and acceptance

On each machine, preserve checkpoints and original output root, reconcile active jobs before changing connector executable. Update checkout and installed Skill, install version-matched runtime in dedicated environment, verify local version, then refresh/reopen the authorized client. Never stop shared solver solely to refresh MCP. Verify tool discovery and actual read-only calls in manual AND scheduled contexts. Capture the five-layer evidence and report capabilities. For hard deadlines find original isolated worker source, establish its provenance, and test with controlled licensed minimal job and independent observer, including long native call, restart, identity change and no collateral stop. Until then record HARD_DEADLINE_UNSUPPORTED.

Offline regression covers direct loopback scope, 502 classification, fingerprint mismatch and freshness, duplicate evidence, immutable clocks, wrap/deadline/stall, hard-required block, unknown jobs, corrupted journals and idempotent original receipt. Actual proxy, desktop, licensed solver and watchdog integration remain NOT_RUN. Existing formal model checks are abstract and do not prove new runtime native control.
