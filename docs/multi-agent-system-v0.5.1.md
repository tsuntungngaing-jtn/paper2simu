# Integrated SRS v0.5.1 (2026-11-24)
User survey: accuracy first, central stage/event dispatch, 9 specialist roles, sole Executor, supervisory veto and separate final acceptance, fixed core + dynamic retrieval + validated experience, official-document-first diagnosis, four hours per case by default, cross-host validated knowledge and independently reviewed PRs. Questions 21/22/24 are proposed defaults, not confirmed. No automatic release merge. v0.4.5 and v0.5.0 preserved.

## Requirements and authority matrix
| Role | Authority | Prohibited |
|---|---|---|
| A00 Orchestrator | dispatch and resolve by evidence; control budgets | native writes; veto override |
| A01 Paper Reader | propose source ledger | invent missing inputs |
| A02 Documentation Expert | supported API proposal | native calls |
| A03 Physics Reviewer | independent precheck/block | model write |
| A04 Executor | exclusive scoped native mutation and solve | self approval, change frozen targets |
| A05 Supervisor | process ALLOW/BLOCK/REQUEST_STOP | direct model write, override unknown state |
| A06 Recovery | diagnose F1-F7 and propose repair | execute repair |
| A07 Acceptance | independent gate verdict | execution or changing criteria |
| A08 Recorder | summaries and knowledge candidates | edit canonical log or promote own knowledge |
| A09 Experiment Designer | bounded design and predictions | submit solves or tune L0 |

Use agent-knowledge/registry.json and each ROLE.md: authority, mandatory reading, source index, SOP/checklist, structured report sections, evaluation. Core reads are logged as actual byte hashes and locators, not a claim that the model was trained on a book. External sources are indexes only; retrieve exact edition/build as needed. Current user authorization and scientific contract override historical guidance. Paper establishes physical target; official documentation establishes supported implementation; native readback establishes actual state.

## Stage gates
G1 source consistency, G2 physics, G3 numerics, G4 frozen QoI metrics, G5 promised native archive/readback/editability/replay. Task specifies applicable gates up front; paper reproduction requires G1-G4 and G5 when scoped. Missing mandatory evidence -> NOT_RUN/BLOCKED, not PASS. Execution-only is not reproduction. User's previous 15% per QoI is task-specific; no universal hardcode. Relative error undefined near zero: freeze alternative scale. Four hour wall-time default only for new reproduction cases with user survey policy; task card defines scope and UTC start/deadline, never resets on resume. Hard cutoff must have verified support or explicit authorized alternative; shared JVM cannot promise hard stop. At cutoff block new submissions, reconcile stop or verified isolation before reusing resources. See job-deadline-contract.md.

## Parameter authority
L0 explicit paper values fixed; L1 mesh/time step/relaxation/initialization/numerics under authorized range; L2 paper-missing geometry/material only evidenced tentative range; L3 alternative physics/BC interpretations only as separately labeled validated hypotheses with independent review. Freeze criteria, compare one mechanism or justified DOE, predict/falsify, use holdout and preserve all trials. Do not infer true author values solely from match. See conditional-calibration prompt. Guard requires frozen task, exact scope, fresh supervisor and relevant physics review plus actual writer and native capability; no L0 tuning.

## Nonfunctional
Reliability: identity reconciliation before action, no duplicate unknown submissions, time persists across reconnect. Security: least privilege, actual tool isolation verified, redacted logs, no licensing/permission bypass. Quality: evidence lineage, independent acceptance and no self-approval. Reproducibility: exact commit/build, journal and artifacts. Performance: accuracy first, capped workers, no recursive delegation. Offline check PASS validates declared structure, not authority or solver evidence. Real Codex, MCP ACL, COMSOL/Fluent and hardware recovery NOT_RUN.
