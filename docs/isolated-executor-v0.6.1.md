# Isolated executor integration (v0.6.1)

This is an opt-in Windows batch backend behind Runtime. It does not change the shared JVM capability: running hard stop and hard-deadline enforcement remain unsupported for shared MPh work. Offline tests do not establish a validated COMSOL native deadline.

## Provisioning and scope

A trusted local operator provisions a NEW database once, while the resource is known idle. Never initialize over an existing or unresolved ledger. Its parent directory must already exist and be private to the operator. Use local storage, not an unreliable network filesystem.

```console
python -m server.coordination initialize /absolute/private/coordination.sqlite3 host-resource --root /absolute/output-a --root /absolute/output-b
```

On Windows supply absolute Windows paths. The root directories must exist and be readable. All connectors sharing native resources (including a license/concurrency domain) must use the exact same database and resource identity. Enroll every existing output root during provisioning so legacy manifests participate in admission. Runtime registers its own output root for operator access; reviewer readback does not enroll a root. Unavailable enrolled roots block new work.

Set these environment variables before constructing Runtime:

| Variable | Meaning |
| --- | --- |
| PAPER2SIMU_COORDINATION_DB | Absolute path of the provisioned database |
| PAPER2SIMU_RESOURCE_ID | Exact resource domain identity stored at initialization |
| PAPER2SIMU_ALLOW_ISOLATED | Must be `1` to submit isolated work |
| PAPER2SIMU_EXECUTOR_ID | Stable authenticated local Executor configuration; must match reviewed actor/executor identities |
| COMSOL_TOOL_ROLE | `operator` or `reviewer`; reviewer cannot execute |
| COMSOL_OUTPUT_ROOT | Existing task output and evidence workspace |
| COMSOL_ROOT | Configured COMSOL installation used to locate bin/win64/comsolbatch.exe |

Install `.[isolated]` for Windows pywin32 support. The runtime checks platform, dependencies and executable before admission; this is not a license test. Linux supports offline tests and blocked-platform readback, not Windows native submission.

Isolation applies only to cooperating Runtime instances on one host using this domain. Different databases, legacy/unpatched services, other users and remote machines are not automatically discovered or coordinated. A database path is not a distributed lock. Do not enable native execution until all conflicting routes are enrolled or independently excluded. No process name search, unknown-process termination, service restart or automatic legacy takeover is performed.

The local operator, evidence workspace, Python process, environment and database are trusted. MCP is not a sandbox. Caller-provided evidence is not cryptographically authenticated by the offline Verification Gate. Reviewer role filtering and the configured identity form a deployment trust boundary, not protection against an administrator altering files or Python.

## Durable ownership and history

SQLite immediate transactions enforce one unreleased claim. Each claim binds operation ID, generated coordination job ID, owner Runtime token, kind and immutable request digest. Phases are reserved, launching, running and stopping; release is a separate proof-bearing field. Only the owner may advance or release a claim. Consuming reserved to launching is single-use, so another supervisor cannot restart the original job.

Lost launch receipt, crash before/after creation, corrupt manifest, unknown native status and stop-observation failure retain the claim. An executor exit or output file is not native stop evidence. Isolated release requires a zero-active-process observation from the owned Job Object; queue cancellation before entry can use never-started evidence. Shared synchronous calls release only on successful return, while exceptions, unknown connection state, failed solve and arbitrary code retain the claim conservatively. Shared process/server lifetime is distinct from synchronous native operation lifetime.

Operation replay returns the original record; conflicting requests block. Shared native job IDs and operation IDs resolve through bound manifests across Runtime/output roots. Both shared and isolated submissions count towards configured host submission limits. Direct native calls, startup/JVM initialization, connection/disconnection, metadata that enters Java, modeling and serialization paths use the same domain. Metadata-only job/status polling does not enter Java.

Legacy completed/cancelled manifests can establish closed history but cannot be reused as new operation IDs. Unresolved legacy work, duplicate IDs and misbound manifests block. Registered-root enumeration errors do not mean idle. Database schema/domain, hashes and audit counts are validated; there is no automatic corruption repair or TTL-based release. Restoring a fully valid old database snapshot cannot be detected without an external anchor and is unsupported while work is unresolved.

## Case Clock and progress

Example task configuration (seconds):

```console
python -m server.case_clock --help
```

Use CaseClock.start with total=14400, solve=9000, stall=900, wrap=1800 for the requested 240/150/15/30-minute task. These are task values, not universal skill limits. The resource ledger binds a case ID permanently to its original clock path, start, total deadline, wrap cutoff, solve limit and stall limit. Use new case IDs for genuinely new cases; do not replace an old clock to restart a budget.

Isolated submission requires an absolute finite deadline within both the case work cutoff and solve budget. The detached supervisor uses that frozen deadline, monotonic elapsed time and the persisted Case Clock. Clock regression, closed/stalled case or clock/database failure initiates stop only against its owned Job Object. A separate watchdog requests stop at the frozen deadline even if metadata I/O is blocked. An OS scheduling delay or failed native termination may miss the deadline; timestamps expose this and no hard real-time guarantee is claimed.

Polling and supervisor heartbeat never call CaseClock.observe. Repeated evidence hashes do not count as progress. The existing local clock observe interface trusts an operator to supply hashes/timestamps of actual new native progress; it does not authenticate or parse native solver logs. Without trusted progress observations the configured stall timer expires. Native scientific acceptance remains separate.

## Review and MCP interface

`comsol_isolated_batch_submit(input_file, study_tag, operation_id, deadline_at_unix, task_case_id, verification, cores=4)` is operator-only. `comsol_isolated_batch_status(operation_id)` and the unified `comsol_job_status` are reviewer-readable. The implementation retains the candidate core allowlist 1..4; there is no universal four-hour deadline cap.

`verification` uses scripts.verification_gate's request format and the existing multi-agent admission rules. Each receipt additionally carries identical `launch_binding` data generated by `server.isolated_runtime.launch_binding`: source path/hash, operation/case, study/cores, resource and Executor identities, solve deadline, case deadline and work cutoff. Snapshot revision must equal the reviewed input SHA256. Independent supervisor and physics reviewers remain mandatory. Artifact hashes, expiry and identity are checked again before CreateProcess and before ResumeThread; a fresh expiry check follows artifact hashing.

The submitted MPH must be inside the output root. Runtime copies its reviewed bytes to the isolated job directory. The supervisor holds a Windows read handle denying write/delete while verifying and executing this snapshot; external snapshot replacement is blocked. Missing/changed/expired evidence or model changes require fresh review; the original consumed operation remains unresolved until owned reconciliation. EVIDENCE_BOUND_CANDIDATE retains execution_authorized=false in the offline helper.

Recovery Memory records original operation/job identities and failure evidence idempotently. Records and recommendations do not authorize release, reset budgets or resubmit. Manual recovery requires actual owned native-state evidence; no public forced-release or PID-kill endpoint is supplied.

## Differences from the recovered patch

The patch only coordinated one output root, used a fixed 14400-second maximum, exposed unregistered source files and lacked Runtime clock/gate/memory integration. This version adds a shared durable ledger and root inventory, global case binding, guarded Runtime entry points, operator/reviewer MCP registration, immutable review-bound launch envelopes, snapshot locking, budget checks, common history lookup and conservative recovery. Native relative stoptime is no longer treated as evidence of a stop; the owned supervisor records actual observations. Generic command execution remains private test plumbing, not an MCP submit capability.

All baseline repository tests are retained. The standalone archive's tests were not part of the recovered repository commit; relevant behaviors are covered by the new controlled suites. Its universal-four-hour and release-after-spawn-error assertions conflict with this task's amended contract and are not carried forward as product requirements.

## Release and rollback

Linux and Windows CI run full tests plus four mandatory focused modules. JUnit validation rejects empty/all-skipped suites and reports executed/pass/fail/skip counts. ZIP validation compares every source/test Python file, required policy resources, manifest hashes and outer checksum. Existing Verification-Driven Gate is retained. All evidence must identify the same candidate commit before any main merge.

Rollback is a reviewed revert of integration commits. Preserve coordination, case-clock, operation and recovery databases and all job manifests. Do not downgrade a running supervisor, remove claims, recreate a database or restart COMSOL as a shortcut. An old Runtime does not understand the new coordination protocol; disable submission and reconcile owned jobs first.

NOT_RUN: commercial COMSOL deadlines/termination accuracy, native COMSOL client-disconnect and supervisor-crash recovery, result/checkpoint reopen, licenses, scientific convergence and paper metrics. No P025, deployment or service restart is included.
