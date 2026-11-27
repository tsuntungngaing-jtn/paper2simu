# v0.6.3 candidate: host connection recovery

Mandatory on resume, scheduled turns and before native dispatch. This fixes the
missing-catalog routing and introduces a persistent, bounded host recovery
controller; it does not claim that stock Codex Desktop exposes a control socket.
See the [official app-server protocol](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)
and upstream [missing tools after recovery](https://github.com/openai/codex/issues/54301).
The latter is a reported symptom, not proof of a particular workstation cause.

## Deployment boundary

A trusted host adapter integrates server.connection_supervisor.step with its
existing authenticated app-server RPC connection. It must own the affected
scheduled thread, use the same app-server instance, have a bounded RPC timeout,
and provide actual observations, not model-generated assertions. Host identity
must identify the app-server deployment across its threads and providers.
No guessing sockets, starting a second app-server, editing auth or permissions,
terminating processes, restarting native solvers, or bypassing the unique writer.
The reload method affects loaded threads globally: authorize it only when other
threads and session-bound provider state have been assessed and refresh is safe.
If no supported host adapter is present, report HOST_REFRESH_UNAVAILABLE, retain
the incident and request the smallest supported operator action once. Skill-only
installation cannot manufacture a host RPC interface.

## Actual turn preflight

Read resume.md and existing journals; capture host/provider/thread/turn IDs,
stable incident ID (unchanged until verified recovery), UTC observed_at, solver
COMSOL or Fluent, context actual_scheduled. Use tri-state booleans (null unknown)
for registered, transport_ok, catalog_ok, readonly_ok, executor_ok, runtime_ok,
native_ok, history_ok, policy_denied, reload_supported, reload_authorized,
refresh_safe. Collect from actual registered tool discovery, read-only call,
host policy and runtime/native records. Do not use a separate CLI success as
scheduled proof. For app-server adapters use supported thread-scoped
mcpServerStatus/list (including pagination where applicable); status inventory
alone does not establish actual executor readback or permissions.
Runtime fingerprint is compared with the independently approved deployment, not
with its own observed value. For official Fluent verify the actual provider
version and session identity, not a COMSOL-specific version string.

Use a private absolute SQLite path shared by all threads of the app-server,
outside research output roots; preserve it across restarts. Call step(db, snapshot,
rpc=host_rpc) with a host-owned synchronous bounded callback. The callback sends
only config/mcpServer/reload with empty params and returns the actual result or
raises on error. Without an adapter, python -m server.connection_supervisor DB
SNAPSHOT_JSON records diagnosis only. Never place credentials or raw errors in
snapshots; link redacted native evidence in the existing journal.

The controller reserves at most two reloads per persistent incident, at least
five minutes apart across the app-server. An unknown or lost acknowledgement
counts as an attempt. No reload on policy denial, configuration mismatch,
transport failure, unknown catalog, Executor permission failure, native attach
failure or unresolved history. For 502 use existing exact loopback diagnostics;
for native attach use existing verified attachment route; for history use
original IDs and existing reconciliation. No automatic permission change.

A reload acknowledgement is not recovery. On the next actual scheduled turn
rediscover tools, perform read-only calls in the real Executor, verify native
identity, runtime and original job IDs, then run all existing admission checks.
If stale catalog persists after bounded attempts, report the exact unblock
condition and notify once; retain schedule and incident. Do not generate repeated
paper-reading work as a substitute for execution. Continue only independent
authorized nodes and maintain original clock and queue. Never reset incident IDs
to obtain more attempts. P2S-TRACE-1.0, if requested, records actual RPC calls
and outcomes and links the original IDs. The supervisor result never grants
native execution authority.

## Rollout acceptance

Offline tests cover classifier, acknowledgement, retry budget, cross-provider
cooldown, stale and wrong context, policy and permission boundaries.
Real Windows Codex Desktop host adapter, licensed COMSOL and Fluent attachment,
active job disconnect/reconnect, actual scheduled Executor tool visibility and
four-host cross-night run remain NOT_RUN until observed. Deploy to a single
idle pilot host first; preserve original output roots and job/clock/coordination
ledgers. Do not advertise autonomous Desktop reconnect where its host control
interface is unavailable. Roll back by disabling the adapter and reverting the
candidate while preserving all original ledgers and recovery observations.
