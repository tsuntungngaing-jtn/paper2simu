# Paper2Simu v0.6.1 independent executor integration — design for review

Date: 2026-11-26 (Asia/Shanghai)
Status: DESIGN_REVIEW_PENDING; implementation and integrated validation NOT_RUN.

## Verified provenance
- Repository: https://github.com/tsuntungngaing-jtn/paper2simu
- Work branch: feature/isolated-executor-v061-integration
- CI baseline: 44c8b9a404f3a28d104815e5f5c9ebe23b3c9735
- Recovered source / current branch HEAD: 421f3ba8ff809411907f8292cd09bd1044b8f409
- Original ZIP: C:/Users/Dell/Documents/Codex/2026-11-23/qin/outputs/Paper2Simu-Isolated-Executor-Integration-Patch.zip
- ZIP SHA256: 088f9a98bf9cd4241c4dc337d1c2c2515dd374b97ad542074f89bf2a82b5c2d6
- Embedded integration.patch SHA256: f2f8df194cf628951e6655dbe950949940f19649378ca8b3bb3f2be8f9f23413
- All 18 embedded SHA256SUMS entries verified.
- All three recovered executor Git blobs match candidate-v051 source after newline normalization. Checkout uses CRLF; raw working-file hashes therefore differ.
- Historical baseline CI: https://github.com/tsuntungngaing-jtn/paper2simu/actions/runs/45763666889 and https://github.com/tsuntungngaing-jtn/paper2simu/actions/runs/45763666888. Both successful, neither validates the future integration.
- Installed canonical skill declares 0.5.1; source project declares 0.6.1. No live solver MCP was called or its deployed version verified: not needed for this offline development task.

## Alternatives
1. Recommended: adapt the recovered supervisor behind Runtime, with an explicit shared coordination store and fail-closed admission. Keeps the native ownership mechanism and current Runtime behavior, while adding durable coordination and evidence binding.
2. Retain output-root-local locks: smallest change, but cannot satisfy cross-root and cross-Runtime exclusion; rejected.
3. Replace all execution with a separate broker service: stronger centralization but introduces installation/service lifecycle changes beyond this integration; deferred.

## Proposed integration
- Keep version 0.6.1 and the existing Orchestrator plus nine roles. Development review uses a separate real reviewer agent; it does not pretend to be a scientific reproduction run.
- Runtime owns the public submission/status interface. Register isolated submit for operator only, status for operator/reviewer; retain the current reviewer allowlist and block direct execution routes for reviewer.
- Introduce a SQLite coordination ledger at a stable, explicitly configured local resource-domain path independent of Runtime root and output root. Isolated execution requires this domain to be configured. Participating shared and isolated Runtime submissions transact against the same domain. Store original operation/job IDs, request hashes, output location, owner identities, deadlines and resource claims.
- Do not claim exclusion against unconfigured/legacy connectors, other users or machines. Unknown ownership, corrupt journals, unresolved submissions or unavailable coordination block admission. Never infer ownership from a process name and never kill or modify an unknown process. Resource-domain configuration is a deployment precondition, not automatic production deployment.
- Reconcile original IDs before new admission; identical retries return the original receipt without launch, conflicts block. Preserve historical manifests and expose unresolved history explicitly. Failed scheduling can release a claim only with evidence that native launch never occurred.
- Preserve the Windows Job Object creation-time assignment and detached supervisor. Import Windows dependencies lazily so Linux can inspect/test the package; unsupported platforms or missing dependencies return explicit blocked results.
- Persist separate executor state, native stop confirmation, termination reason and evidence. Supervisor disappearance, unconfirmed stop, or an exit receipt without proven native termination retains the claim. No PID/name-based cleanup and no timeout-based lease reclamation.
- Case Clock remains authoritative for immutable task budgets. Support 240/150/15/30 minutes as an example task configuration, not universal limits. Freeze per-job absolute deadline at admission, bounded by requested deadline, solve budget and case work cutoff; never recompute it on replay. Stop new submissions at the wrap boundary and reserve the wrap window for finalization.
- The detached supervisor observes persisted case status and no-progress limits as well as the frozen solve deadline. Polling and heartbeat timestamps never refresh progress. Only an evidence-bound trusted observer may record new progress; missing trustworthy progress fails closed at the stall limit.
- Reuse Verification Gate and its existing multi-agent admission checks; bind current receipt hashes, expiry, case, operation/action, revision, model content and resource reservation to the actual launch. Recheck under admission coordination. Offline candidate approval alone is not a provider execution grant; operator access and all runtime checks remain necessary.
- Add idempotent failure/recovery records linked to the original operation/job in Recovery Memory. Recovery recommendations cannot resubmit, release claims or reset budgets without verified reconciliation and fresh admission.
- Keep shared JVM hard-deadline capability unsupported. Describe isolated enforcement as implemented Windows ownership machinery with commercial native validation NOT_RUN.

## Validation and release plan
- Preserve all existing tests and add regressions for registration, reviewer denial, shared/isolated contention, cross-process/cross-root/cross-Runtime contention, replay/unknown IDs, expired cases, restart budgets, missing/stale evidence, unconfirmed native stop, dependency/platform blocking and package completeness.
- Use controlled test workers and Windows API test doubles; no COMSOL connection or license. Exercise real OS ownership on harmless synthetic workers only where the test is explicitly scoped and supported.
- Run full suites on Linux and Windows CI with result artifacts and counts; include offline ZIP manifest/hash and source/test completeness checks. Existing required verification CI remains required.
- Independently review the final code. Fix findings and repeat affected checks; final independent review, both platform CI results and offline release checks must identify the same final commit.
- Commit and push only to the requested feature branch and create a PR. No main merge in this task. Report final SHA, changed paths, patch differences, review record, CI URLs, pass/fail/skip counts, NOT_RUN native checks and limitations.
- Rollback: revert the integration commit(s) on the feature/release path; preserve all durable journals and unresolved resource claims. Do not delete ledgers or restart services as a rollback shortcut.

## Explicit exclusions
P025, production installation, existing COMSOL service restarts, commercial/native solver tests, scientific validation, claims of proven native hard deadlines, and merging to main.

## Review checkpoint
No implementation edits have been made. The brainstorming skill requires a reviewed design before implementation. After design approval, create the concrete implementation plan, execute it and obtain independent review.
