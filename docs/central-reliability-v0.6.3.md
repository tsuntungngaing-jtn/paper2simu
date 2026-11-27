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
