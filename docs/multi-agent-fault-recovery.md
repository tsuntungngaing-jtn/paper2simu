# Unified fault routing F1–F7
Read scheduled-connection-recovery.md and job-deadline-contract.md first. Preserve prior identity and exact redacted error, UTC, native last state, elapsed budget, pending operation. Host observes and journals; Supervisor issues BLOCK or REQUEST_STOP; orchestrator freezes dependent submissions. Recovery diagnoses with version-matched official documentation first (Documentation Expert); Executor applies approved model/numerical repair, separately authorized environment operator handles transport/runtime repairs only. No repair agent can execute. Stop requests are not stop receipts; no auto kill, global process-name kill, security/license changes, duplicate jobs, blind restart, or alternate native bypass.

| Fault | Dispatch and first check |
| F1 transport/MCP/502 | Recovery + Docs; configured registered provider, proxy log and direct loopback per existing protocol; distinguish tool response, native attach, job identity |
| F2 runtime/license/MPI/JVM | Recovery + Docs; distinguish normal busy, license and compute launch; existing MPI/licensing preflight |
| F3 geometry/mesh/API | Recovery + Docs + Physics as needed; schema, topology, selection and effective readback |
| F4 divergence/initialization | Recovery + Docs; native log, numerical settings, authorized one-mechanism repair |
| F5 physical/energy | Physics + Recovery; equations, BCs, units, balances before tuning |
| F6 QoI/definition | Paper + Acceptance + Experiment; check stale dataset and frozen definitions before conditional trials |
| F7 agent coordination | Orchestrator + Supervisor; expired/missing assignments, actual worker IDs, stale evidence, permissions; redispatch read-only work |

States READY → RUNNING → ANOMALY → DIAGNOSING → RECOVERING → VERIFYING → RESUMED or HOLD/CLOSED. No new submit at ANOMALY or UNKNOWN; monitoring may continue; original operation reconciled using runtime/session/job/operation and native evidence, not empty queue alone. Retry bounded by original budget; no new evidence -> HOLD. On reconnect restore journal, never reset elapsed or charge. At cutoff stop new submissions and preserve original job; move to next independent case only if terminal or verified isolation and explicit queue policy. HTTP 502 does not imply solver stopped. A host/scheduler must actually run checks on every turn; no self-running service is added by this release. See offline guard route_fault and recovery_next for deterministic recommendations; host must implement and verify actions. Test mock faults, then separate native verification.
