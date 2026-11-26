---
name: paper2simu-execution-trace
description: Trace actual Paper2Simu Skill, Agent, workflow and tool execution, bind inputs and outputs to native evidence, and audit required-step conformance during paper reproduction.
metadata:
  protocol: P2S-TRACE-1.0
  compatible-paper2simu: "0.6.2"
---

# Paper2Simu — Skill / Agent execution provenance

## 1. Activation and boundaries
Load for paper reproduction under the master prompt when execution tracing is requested. This companion extends recording only; the canonical Paper2Simu skill, frozen task cards, resource authorization, independent vetoes and P2S-DATA-1.0 remain authoritative. Do not reset clocks, change solver, modify Sheets structure, override a gate or claim native capability. A00 is the host Orchestrator; A01–A09 are real specialist workers, invoked only when applicable. The approved baseline commit is immutable; an updated deployment must record its actual commit and obtain approval for the new baseline.

## 2. Standards mapping
Use W3C PROV Entity/Activity/Agent and used/wasGeneratedBy/wasAssociatedWith/wasDerivedFrom/actedOnBehalfOf; Workflow Run RO-Crate prospective vs retrospective provenance and process/workflow/provenance-run packaging; OpenTelemetry trace/span/links for observable execution; IEEE 1849-2023 XES event logs for conformance; in-toto materials/products/authorized steps for evidence integrity; ASME V&V 20 for applicable CFD/heat-transfer scientific validation. These are design references, not certification. Pin actual telemetry schema and adapter versions. Do not label the custom fields as official OpenTelemetry attributes.

## 3. Preflight and planned trace
Read the canonical Skill, role registry, packaged prompts and applicable workflow, agent handoff and verification contracts. Record actual host/Codex build, installed skill commit and file hashes, runtime/provider/tool schemas, case clock, worker isolation, native resource/Job IDs and available host event interfaces. Establish an independent append-only collector from real host events (e.g. supported Codex JSONL/App Server events), tool receipts and native readback. Test each required source on the local machine; if unavailable mark EVIDENCE_UNAVAILABLE or UNKNOWN, never simulate a worker or claim collection. Freeze a prospective plan with unique step IDs, scope, applicable condition, predecessor dependencies, required roles/components, expected inputs/outputs and acceptance evidence. Preserve plan revisions, conditional branches, parallelism and repeated operation instances.

## 4. Required role and component matrix
| Role | Input | Output | Required downstream evidence |
|---|---|---|---|
| A00 | Task card, queue, capability/clock | Dispatch, conflicts, next action, budget | Real assignment and admission |
| A01 | PDF, supplements, scoped knowledge | Candidates, locations, conflicts, uncertainty | Adopt/reject in input ledger |
| A02 | Build, tool schema, technical question | Supported API/path/values/readback/source | Executor operation or explicit rejection |
| A03 | Frozen spec, native snapshot | Equation, BC, material, mesh checks/blockers | Current independent review receipt |
| A04 | Admitted spec/operation | Operation, native readback, job/artifacts/state | Native receipts and files |
| A05 | Current stage, clock, snapshots | ALLOW/BLOCK/REQUEST_STOP, reasons | Admission, block or authorized stop |
| A06 | Incident, original job, history | Hypotheses, repair, falsifier, rollback | Approved repair or rejected/held proposal |
| A07 | Frozen QoI, native and verification evidence | Gate results, QoI, verdict, limits | Scientific acceptance record |
| A08 | Original events and outputs | Summary, provenance, missing events, candidate | Authorized journal and sync readback |
| A09 | Error, tentative inputs, constraints | Design matrix, prediction, falsifier, holdout | Trial and decision, or explicit disposition |

Use the role registry and original gates as the authority for applicability and detailed role outputs. A06 is conditional on incidents; A09 is conditional on authorized experimental work. Knowledge-only/CAD-only routes do not imply solver submission. Record external Textbook2Skill and SolidWorks CAD Modeling only when applicable; distinguish actual Skill invocation, file read, workflow use, script execution, tool call and knowledge retrieval. Track Paper Input Reconstruction, Conditional Calibration, Verification Gate, Recovery Memory, Research Plan & Handoff when applicable. Never force unnecessary calls to improve coverage.

## 5. Retrospective records
Use the existing journal as authority. Maintain an append-only structured trace view under the task directory, referencing original event bytes, record IDs and artifacts instead of creating competing truth. Each activity instance records schema_version, event_id, paper_id, task_id, case_id, run_id, trial_id, operation_id, native_job_id, step_id, plan_revision, trace_id, span_id, parent_span_id, span_links, agent_role, actual worker/thread/session identity, component_type, component_name, version, commit, content_hash, start/end, actual tool, redacted input/output entity IDs and hashes, evidence refs, status/error, resource observations, consumer_step IDs, disposition and independent review. Store UTC or offset-aware timestamps; use Beijing time in the cloud view. Use stable IDs and revisions, not row numbers. Record source origin, source/assumption lineage and actual native values by D03–D05 references; bind D07/D09/D10/D11/D12/D13/D14 to trace IDs. Do not change D01–D14 meanings, overwrite original events, expose secrets, store private reasoning, or modify cloud schema. Redact payloads; retain access-controlled evidence refs and hash the actual retained bytes. Missing, unknown, not run and not applicable remain distinct.

## 6. Evidence and conformance
L0 REGISTERED: actual registry/installation; L1 LOADED: observed file/config load; L2 INVOKED: real host dispatch/call and identity; L3 OUTPUT_GENERATED: attributable artifact/receipt; L4 CONSUMED: downstream observed input reference plus explicit ADOPTED/REJECTED/HOLD disposition; L5 VERIFIED: current independent applicable review/check evidence. Each level requires its own evidence; do not infer a level from agent narrative, registration or file presence. Where a level is not observable retain UNKNOWN; report evidence gaps rather than inventing use. Hashes prove retained content consistency, not identity or cognitive use. No self-approval. Distinct real worker identity and current revision are required for independent review. Recheck dependencies and invalidated receipts on any relevant revision. Missing required admission evidence blocks affected operations under existing gates; missing new trace evidence blocks a complete-trace claim, not independent authorized work. Report missing/duplicate/out-of-order/unapproved steps, unresolved dependencies, missing consumer dispositions, stale receipts and bypassed vetoes; preserve legitimate conditional/parallel/loop paths. Never treat telemetry success as scientific PASS.

## 7. Outputs and metrics
Provide a planned-vs-observed matrix, trace view, entity/activity/agent dependency graph, agent/skill usage summary, evidence-gap report and artifact manifest at each milestone and case closure. Report role and step coverage, input/output evidence completeness, disposition coverage, independent review coverage and unauthorized actions, with explicit eligible denominators and unknown counts; project target 100% of applicable required items and zero unauthorized operations, not a standards-mandated threshold. Zero eligible denominator is NOT_APPLICABLE. Separate SINGLE_AGENT_FALLBACK from multi-agent runs; no claim of causal accuracy improvement without controlled evaluation. Export optional PROV/RO-Crate/XES views only when their schemas are validated. Integrate existing P2S-DATA-1.0 synchronization: local-first, unique writer, idempotent write/readback, pending queue, no unauthorized columns. Keep raw logs private and share authorized summaries/evidence links only.

## 8. References
- https://www.w3.org/TR/prov-dm/
- https://www.w3.org/TR/prov-o/
- https://doi.org/10.1371/journal.pone.0309210
- https://www.researchobject.org/workflow-run-crate/
- https://opentelemetry.io/docs/specs/otel/trace/api/
- https://github.com/open-telemetry/semantic-conventions-genai
- https://standards.ieee.org/ieee/1849/10907/
- https://www.usenix.org/system/files/sec19-torres-arias.pdf
- https://github.com/in-toto/specification
- https://www.asme.org/codes-standards/find-codes-standards/standard-for-verification-and-validation-in-computational-fluid-dynamics-and-heat-transfer
- https://developers.openai.com/blog/eval-skills

Deployment remains unverified until local adapter and native evidence tests pass. This file is a recording contract, not an installed collector, signature service, verified watchdog or new execution authority.
