# Independent Executor Integration Implementation Plan

Status: APPROVED_WITH_AMENDMENTS, 2026-11-26.

Goal: integrate recovered Windows supervisor into v0.6.1 without weakening existing gates.
Architecture: explicit shared SQLite resource domain, durable exclusive claims, Runtime admission and immutable isolated launch envelopes. Python, SQLite, Windows Job Objects, pytest and GitHub Actions.

## Global constraints
Version 0.6.1; Orchestrator plus nine roles; no commercial solver, P025, production deployment, service restart or main merge. Case Clock authoritative; example minutes 240/150/15/30 configurable. No budget reset, unverified progress refresh, unknown-resource termination, or resource release without stop proof. All existing tests retained. Final review, Linux/Windows/Verification CI and ZIP checks bind the same candidate SHA.

## Task 1: Durable coordination
- [ ] Add server/coordination.py and tests/test_coordination.py. Explicit initialize(path, resource_id); no implicit recovery/create when missing. SQLite BEGIN IMMEDIATE, schema/domain identity checks, exclusive claim; operation ID idempotency, request hash, owner token, phase and immutable payload. Corrupt/unavailable/unknown history fails closed. No lease timeout release.
- [ ] Test separate instances, output roots and processes, duplicate/conflicting operations, reserved-before-start, receipt loss, owner mismatch and missing/corrupt DB before implementation; run pytest tests/test_coordination.py -q.
- [ ] Native-stop/not-started proof is the only release path. Faults remain durable. Independently review ledger before final integration acceptance.

## Task 2: Isolated supervisor and budgets
- [ ] Adapt server/isolated_batch.py, isolated_worker.py, windows_job.py; add tests/test_isolated_executor.py. Lazy platform imports; command allowlist; no universal 14400-second limit. Persist launch request and input snapshot hash before spawn. Spawn consumes a claim once and never relaunches unknown work.
- [ ] Detached supervisor rechecks immutable input/gate/clock before creating process, owns Windows Job Object; distinguishes task_exit, stop_request, native_stop and scientific status. Persisted clock anomaly/DB errors request owned stop, never extend time. Repeated supervisor entry cannot launch again.
- [ ] Use controlled workers/API doubles only, test deadline, stall, clock reversal, restart, persistence failure, exception and stop-unconfirmed behavior. Run pytest tests/test_isolated_executor.py -q, native COMSOL NOT_RUN.

## Task 3: Runtime and verification binding
- [ ] Add server/isolated_runtime.py and tests/test_isolated_integration.py; edit runtime.py/main.py. Runtime captures role/worker/resource-domain config. Bind review to actual operation, case, resource ID, executor, study/cores and input SHA256, reverify before launch. Reuse verification_gate.verify and check_multi_agent_v051; candidate is necessary, never sufficient.
- [ ] Guard all runtime.call/SerializedRegistrar paths, direct native lifecycle/code calls and queued jobs against claims; metadata remains nonblocking. Preserve legacy unconfigured shared behavior but block isolated unless coordination configured. Reconcile shared historical manifests fail closed. Common status resolves original operation/job without extending budgets.
- [ ] Record linked idempotent failures in Recovery Memory; no automated redispatch. Test registration/ACL, shared conflicts, expired/stale evidence, input changes, reconnection budgets and history ambiguity. Run targeted pytest then full pytest tests.

## Task 4: Cross-platform CI and packaging
- [ ] Add Linux/Windows matrix CI: full suite, executor-specific JUnit and nonzero executed assertion; test doubles only. Keep Verification-Driven Gate and existing suites. Check ZIP source/test manifest completeness and hashes. Run packaging locally and in CI.
- [ ] Document configuration, scope, ownership/transaction states, API, limitations, patch differences and rollback. Explicit native acceptance NOT_RUN.

## Task 5: Review and PR
- [ ] Real independent reviewer reads final diff against 44c8b9a; fix important findings and rerun affected tests.
- [ ] Commit to feature/isolated-executor-v061-integration, push and create PR. Wait for Linux, Windows and Verification CI; correct real failures without deleting tests or weakening assertions. Final reviewer identifies exact final SHA.
- [ ] Deliver outputs report with exact SHA, PR/CI URLs, full changed-file list, test counts, release integrity, patch provenance/diff, independent review and rollback. Do not merge main.
