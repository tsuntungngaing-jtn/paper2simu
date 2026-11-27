# Paper2Simu v0.6.3 candidate — Host connection recovery

[Connection supervisor](docs/connection-supervisor-v0.6.3.md): bounded host-side refresh, persistent recovery attempts, actual scheduled Executor verification and explicit missing-host-adapter state. Real desktop/native validation NOT_RUN.

## v0.6.2 historical job reconciliation

The [historical reconciliation contract](docs/historical-ledger.md) describes how a local resource administrator can record an independently reviewed resource decision for one historical job. The original manifest, scientific outcome and case budget retain their original meaning.

## v0.6.1 isolated executor integration

[Windows isolated executor contract](docs/isolated-executor-v0.6.1.md): reviewed source integration, durable SQLite coordination, Case Clock and Verification Gate launch binding, private input snapshot, operator-only submission, reviewer-readable status and Recovery Memory. PR #35 candidate `ff01168317e8530c1e33cf5d14c4a25e920d0881` passed Linux/Windows and existing verification CI. Commercial native validation remains NOT_RUN; production hard deadlines remain blocked until deployment-specific validation. Shared JVM running-stop remains unsupported. See the integration contract for opt-in installation, cooperative resource scope, conservative claim retention and rollback.

## v0.6.1 runtime reliability

[Deployment and recovery protocol](docs/runtime-reliability-v0.6.1.md): direct loopback diagnostic, live fingerprint checks, persistent case clock, bounded independent clock observer, unresolved journal admission blocks, and CI dependency correction. The shared JVM still lacks running-job hard deadline enforcement; the opt-in Windows isolated route is integrated offline but must pass native deployment validation before production hard deadline use. No native integration or autonomous process restart claimed. Existing multi-agent architecture and v0.6.0 knowledge packs remain intact.

## v0.6.0 upgrade

- [Knowledge packs](docs/knowledge-packs-v0.6.0.md): r1 and r2; source review labels are inherited, not independent re-verification.
- [Persistent recovery memory](docs/recovery-memory.md): private SQLite reservation and outcome records; default r2 retrieval; NEW/HOLD never grants execution permission.
- [Verification-driven gate](docs/verification-driven-v0.6.0.md): feature map, artifact-bound verification, bounded state model, TLA+ specification, property-based tests, targeted mutations, CI and paired evaluation.
- Preserves v0.5.2 multi-agent roles, article knowledge, SolidWorks and solver routing. Source integration does not establish native validation. CI, TLC, property tests and native experiments must be reported from actual results.


[System requirements](docs/multi-agent-system-v0.5.1.md) · [Role registry](agent-knowledge/registry.json) · [Orchestration and deployment](docs/multi-agent-orchestration.md) · [F1–F7 fault protocol](docs/multi-agent-fault-recovery.md) · [Learning and benchmark](docs/multi-agent-learning-and-benchmark.md)

Ten roles (host + nine specialists), separate Executor and supervisory veto, independent acceptance, knowledge receipts and deterministic offline admission checks. Actual Codex dispatch, MCP permission isolation, native solver and cross-machine recovery NOT_RUN. No new background daemon. Preserve [0.4.5 single-agent](https://github.com/tsuntungngaing-jtn/paper2simu/tree/release/paper2simu-0.4.5) and [0.5.0 multi-agent](https://github.com/tsuntungngaing-jtn/paper2simu/tree/release/paper2simu-0.5.0) as independent control groups. The following retained README contains historical instructions; current v0.6.3 contract takes precedence.

## Article knowledge and SolidWorks

Use the [optional workflows](docs/paper-knowledge-and-solidworks.md) to build reusable evidence packs with `textbook2skill` v0.3.0, create editable parts and assemblies with `solidworks-cad-modeling`, or hand geometry to COMSOL or Fluent. The CAD route covers native modeling and verification, excluding DFM/DFA. Both companion skills are separate packages and needed only for their respective routes. Retain all v0.5.1 multi-agent admission, independent acceptance and fault recovery gates. Actual companion invocation, native CAD and solver handoff remain NOT_RUN.

The source repository does not ship a stale generated release manifest: run the release builder to create a ZIP containing its own manifest and SHA-256 sidecar.

# Paper2Simu — Paper-to-Simulation for COMSOL and Ansys Fluent

**Current candidate version: v0.6.3. Commercial-solver verification of this release remains NOT_RUN.**

Paper2Simu unifies the evidence-first COMSOL Automatic pipeline (up to v0.7.6) and the ComsoFlent v0.1.0 MCP-routing preview. The project is no longer named ComsoFlent. The canonical repository is [paper2simu](https://github.com/tsuntungngaing-jtn/paper2simu). Legacy names in historical notes are attribution and compatibility references, not separate active products.

**Execution scope:** The user reports an actual Fluent-workstation connection. This does not independently establish that all Ansys simulation tools, restart flows, or full CFD reproductions have been verified. COMSOL and Fluent use separate MCP providers, environments, model files and solver settings. The unified Skill orchestrates routing and scientific evidence; it does not silently load or operate a different solver.

**Skill entry:** [paper2simu/SKILL.md](paper2simu/SKILL.md) or the compatibility [root SKILL.md](SKILL.md). Additional architecture: [legacy ComsoFlent migration design](docs/comsoflent-v0.1.0.md), [operations guard](docs/operations-reliability-v0.7.7-rc1.md), [vendor-native convergence](docs/native-convergence-policy.md).

**Installation:** Python project `paper2simu==0.6.3` retains `comsol-automatic` and `comsol-skill-mcp` command aliases for existing COMSOL setups; new aliases: `paper2simu`, `paper2simu-comsol-mcp`. These aliases start the **COMSOL MCP service**, not a Fluent solver. Install official [Ansys PyFluent MCP](https://github.com/ansys/pyfluent-mcp) separately with its documented Python environment and register a distinct host server ID. Do not assume a single shared virtualenv can satisfy both products.

**Release migration:** `python scripts/release.py --output ../Paper2Simu-v0.6.3.zip` and `python scripts/install_skill.py` produce the new package/install name without overwriting an existing directory. Keep the old install until a complete rollback-tested integration is accepted. Never transfer COMSOL tokens or private solver artifacts into the public Git repository.

## Execution/acceptance separation (v0.2.2+)

The [canonical skill](paper2simu/SKILL.md) handles solver connection, authorized execution and evidence delivery. For paper reproduction, the agent loads packaged [acceptance prompt](prompts/paper-reproduction-task.md), [input reconstruction card](prompts/paper-input-reconstruction.md), and [conditional calibration card](prompts/conditional-calibration.md) automatically; fill the **task card** only (no hand-paste of the full policy each turn). Configurable paper-metric default is strict <15% with \(J=\max e_i/0.15\). Pure modeling without reproduction still executes without a PASS claim. See [migration/API notes](docs/execution-acceptance-separation.md) and [filled example](examples/paper-reproduction-task-example.md).

The controller reports execution, checks and paper comparisons separately. Failed/partial artifacts are deliverable. Optional legacy checks remain available, but historical policies below are not automatically activated by loading the skill. Live solver validation of this change remains NOT_RUN.

## Fluent licensing preflight (v0.2.3)

Skill version **0.2.3** adds Windows Fluent / Ansys licensing-client preflight for agent hosts: launch identity, `%APPDATA%\Ansys` write rights for dynamic `ansyscl` port files, log locations, and official PyFluent-MCP session-log notes. See [Fluent licensing preflight](docs/fluent-licensing-preflight.md) and the Fluent section in [connectors](docs/connectors.md). Connection recovery is not paper acceptance.

## Paper2Simu v0.5.0 — Multi-agent orchestration

[Orchestration](docs/multi-agent-orchestration.md) adds five Codex specialist role files, event-based delegation, structured handoff validation and matched control/experiment protocol. The parent is the sole solver writer. Explicit fallback when subagents or effective isolation are unavailable. Native and actual subagent integration NOT_RUN. See [installation](docs/multi-agent-orchestration.md#deployment).

## Paper2Simu v0.4.5 — Single-agent native workflow

[Native supervised workflow](docs/native-supervised-workflow.md) adds staged agent-led recovery, offline supervision decision helper and independent Desktop editability contract. No subagents, GUI driver or daemon; native verification NOT_RUN.

## Paper2Simu v0.4.0

[Dependency-scoped progress](docs/dependency-scoped-progress.md) adds optional work nodes to the existing handoff journal. The resumed agent can continue authorized modeling and evidence work while a new solve is blocked. Use the [cross-host capability contract](docs/cross-host-capability-contract.md) to compare the actual COMSOL runtime fingerprint and the separate official Fluent provider.

COMSOL preserves prior terminal job states, supports receipt lookup and deduplication by operation ID, and honors build-only and individual study requests for the original heat-sink example. Requests for a hard deadline are rejected before execution on the bundled COMSOL worker. See the [deadline contract](docs/job-deadline-contract.md), [COMSOL model setup](docs/comsol-human-equivalent-workflow.md), and [Desktop and native evidence](docs/comsol-observability-and-desktop.md). Workstation and commercial-solver verification remain NOT_RUN.

## Paper2Simu v0.3.10

[Windows Fluent MPI startup preflight](docs/fluent-windows-mpi-preflight.md) covers compute-node startup failures after license checkout. Use an empty one-process local trial and a controlled two-process comparison through the official provider. Record native startup and gRPC readiness independently. Workstation verification remains NOT_RUN.

## Paper2Simu v0.3.9

The [loopback HTTP 502 check](docs/scheduled-connection-recovery.md#loopback-http-502) compares proxy logs with a direct probe of the registered local MCP URL. After a confirmed proxy exception and client reconnection, verify the original job IDs from the scheduled turn before resuming work. Windows workstation verification remains NOT_RUN.

## Paper2Simu v0.3.8

[Portable native workflows](prompts/portable-workflow-task.md) record independent outcomes for archive restoration, saved-solution readback, fresh parametric replay and scientific validation. The [workflow contract](docs/portable-workflow-contract.md) and offline checker validate record structure, lineage, asset paths and supplied file hashes. The [grid-refinement guide](docs/grid-refinement-reporting.md) distinguishes observed mesh sensitivity from conditional GCI and multi-grid uncertainty methods. Native restore, replay and commercial-solver verification for this release are NOT_RUN.

## Paper2Simu v0.3.5

[Research plans and Codex handoff](docs/research-plan-and-handoff.md) add phase completion criteria and solve budgets to the existing task card. The task plan and trial journal generate `resume.md` for recurring work, with outstanding operations, the accepted checkpoint and the next action. The read-only board combines summaries from the participating hosts.

## Paper2Simu v0.3.3

Scheduled COMSOL and Fluent checks use the registered MCP provider in each turn. The [scheduled recovery instructions](docs/scheduled-connection-recovery.md) cover attachment to an existing solver, original job reconciliation and closing submissions independently of monitoring. Apply the instructions to each existing saved task and verify a scheduled read-only check on each host.

## Paper2Simu v0.3.2

The COMSOL queue reports active and cumulative limits, remaining window time and the live connector version. A local operator can renew the window for the running MCP process while keeping the server connection and job history. See [submission window and recovery](docs/connectors.md#submission-window-and-recovery).

## Paper2Simu v0.3.1

- [Paper input reconstruction](prompts/paper-input-reconstruction.md): record source locations, bounded hypotheses, and a reproduction dashboard. Calibration validation requires distinct holdout run and passing score evidence.
- [Reproduction task card](prompts/paper-reproduction-task.md): reuse saved solutions to audit fixed QoIs, effective settings, and conservation before spending solver time.
- [Conditional calibration](prompts/conditional-calibration.md): compare mesh and tentative effects, advance the accepted checkpoint only on a resolved improvement, and report observed feasible points and holdout scope. See the [P005 example](examples/p005-conditional-calibration.md).
- [Discovery](docs/discovery-surrogate-workflow-v0.3.0.md): opt-in, offline design-space and surrogate screening. Solver work follows the separately authorized MCP route.
- [RSI](docs/context-retrieval-rsi-evaluation.md): optional bounded retrieval and paired held-out comparisons. Favorable comparisons leave policy activation pending independent review.

## Previous COMSOL Automatic capabilities (preserved)


Version **0.7.6** adds **paper-first source precedence and authoritative supplementation review**. `input_intake` now exposes a direct-text/table preference audit and blocks reviewed figure/schematic/engineering inputs from overriding an explicitly located and reviewed original paper numeric input for the same approved physical quantity. A new offline reviewer-mode MCP tool `source_precedence_review` distinguishes original author supplements, institutional standards, relevant peer-reviewed research, quantitative figure digitization, schematic estimates, engineering assumptions and ML outputs. External sources require reviewer-declared provenance/version/physical applicability; "supplement not obtained" and ML imputation never become original evidence. The tool does not verify claims against the internet, select a value, run COMSOL or certify physics. See [authoritative source precedence](docs/authoritative-source-precedence.md).

Version **0.7.5** introduces an **offline knowledge-guided commissioning and evidence-gated recovery harness**, inspired by GCH. Four new MCP tools (`recovery_contract_freeze`, `recovery_commission`, `recovery_propose`, `recovery_assess`) support immutable hash-frozen contracts, reported parameter readback audits, bounded one-parameter repair proposals tied to v0.7.4 diagnostic evidence, and per-observable comparisons against fixed acceptance thresholds. All reported results remain **NOT_RUN** scientifically, and no solver is operated or repair automatically applied. COMSOL/MCP and Fluent/PyFluent are declaration types; only existing COMSOL integration is available. See [knowledge-guided recovery](docs/knowledge-guided-recovery.md).

Version **0.7.4** adds **offline, evidence-driven physical diagnostic hypothesis planning**, inspired by DEScover. New read-only MCP tools `physics_diagnostic_plan` and `physics_diagnostic_record` predeclare falsifiable mechanisms, budgets, source identities, units and tests, order experiments by cost, and preserve reported results in immutable provenance reports. A matched test does **not** prove root cause; `causal_status` remains `UNCONFIRMED`, scientific status `NOT_RUN`, and automatic repair is not authorized. No new COMSOL execution, neural hypothesis discovery, commercial solver code modification or RSI policy mutation is implemented. See [physics diagnostic hypotheses](docs/physics-diagnostic-hypotheses.md).

Version **0.7.3** adds an **offline simulation dataset and Design of Experiments foundation** informed by high-fidelity transonic-wing dataset generation. It provides `simulation_dataset_plan` and `simulation_dataset_record` for evidence-tagged parameter ranges, seeded bounded randomized LHS, supported unit-consistent constraints, case-level train/validation/test labels, per-observable validation placeholders and immutable reported outcome/failure reviews. It does **not** run COMSOL, authenticate source claims, generate optimized LHS/OOD data, certify mesh independence, perform automatic repairs or produce training-ready scientific datasets. Synthetic Python unit tests cover the planning and report layer; COMSOL physical integration **NOT_RUN**. See [simulation dataset and DoE](docs/simulation-dataset-doe.md).

Version **0.7.2** introduces an **offline, conservative figure-configuration selection tool** `paper_figure_route` for 2–6 pre-approved curve or field/colorbar extraction configurations. It executes the existing `paper_figure_analyze` methods, compares bounded quality proxies, records all source/candidate manifests and abstains if results are weak, ambiguous or inconsistent. Inspired by ART of PIV's agentic estimator selection, **not a trained neural selector, PIV optical flow or autonomous ROI discovery**. Real-paper accuracy benchmarking and real-COMSOL physical verification remain **NOT_RUN**. See [adaptive figure routing](docs/adaptive-figure-routing.md).

Version **0.7.1** adds **offline mesh-aware diagnostics** for reviewer-supplied, 2D triangular meshes with nodal scalar values: input schema checks, piecewise-linear spatial comparisons with coverage and numeric error metrics, immutable hash-backed audit reports, and a read-only COMSOL MCP tool `mesh_native_analyze`. This is **not MNC ML**, COMSOL mesh export, automatic mesh repair or mesh independence certification. Tested with synthetic Python unit tests; real COMSOL integration and physical validation remain **NOT_RUN**. See [mesh-native diagnostics](docs/mesh-native-diagnostics.md).

Version **0.7.0** adds **offline paper-to-input intake**, requiring no COMSOL machine or connection. A standard-library-only CLI ingests the 12-column Chinese source ledger in CSV/JSON/ZIP format, distinguishes paper/figure/supplement/assumption sources, highlights potential numeric conflicts and missing/unrecognized units, retains all candidates, and emits reviewed-only `INPUT_DRAFT_ONLY` records. No value is automatically approved and **no simulation is executed**. Usage, limits and test instructions: [offline input intake](docs/offline-input-intake.md).



Version **0.6.0** adds a real **offline scientific figure evidence tool** `paper_figure_analyze` (PDF crop, RGB sampling, single-color plot tracing, colorbar-to-field inversion, optional local OCR). Install optional dependencies with `pip install -e ".[figure-analysis]"`; OCR additionally requires a local Tesseract executable. Read [figure evidence](docs/figure-evidence.md). Inputs/outputs are confined to `COMSOL_OUTPUT_ROOT`; every extraction is `digitized_estimate` and requires review. Synthetic software unit tests exist; published-figure accuracy and physical COMSOL validation remain **NOT_RUN**.


Version **0.5.1** adds [SST diagnosis and pressure validation](docs/sst-pressure-validation.md) and [cross-section dimension checks](docs/geometry-workflow.md#dimensions-across-sections-of-a-paper-figure).

Version **0.5.0** (RSI Infer/Evaluate strengthen, bounded harness RSI):

- Autonomy profiles `COMSOL_RSI_AUTONOMY=strict|assisted|auto` ([rsi-autonomy-profiles](docs/rsi-autonomy-profiles.md))
- Channels: official `doc_default_resolve`, figure `digitized_estimate`, peer `peer_range_prior`
- Endpoint sensitivity budget; DecisionRequest packing; harness retention heuristics (AgentVersion only)
- Digitized/peer never → `reported` / final Scientific PASS

Version **0.4.1**: MCP-only control; add on-disk **agent audit trail** (`.java` / Copy-as-Code snippets + step/progress logs under `COMSOL_OUTPUT_ROOT`) per official blog audit practice—see [agent audit trail](docs/agent-audit-trail.md). No dual bare-Java control path.

Version **0.4.0** (official agentic / Codex alignment, MCP-first):

- Position this package as an **external agent harness**, not Desktop Chatbot; Multiphysics Server ≠ COMSOL Server™
- Client–server status/license notes, connect smoke (`param_set`/`param_get`), MCP mapping of the public agent loop
- Copy-as-Code / live `properties()` discovery; bounded segregated/nonlinear tuning with KPI gates
- Docs: [agentic official alignment](docs/agentic-official-alignment.md), [nonlinear solver tuning](docs/nonlinear-solver-tuning.md)
- Blog ~25%/~30% speed claims remain `NOT_VALIDATED_BASELINE` only—never scientific VALIDATED

Version **0.3.6** (skill hygiene): operator docs state **generalizable rules only**. No trial names, workspace paths, wall-clock control numbers, paper figure IDs, or one-shot geometry recipes in the skill tree. Put case-specific runbooks under `COMSOL_OUTPUT_ROOT`.

Version **0.3.5** (SKILL_UPLIFT_GENERAL_20261029): SegregatedStep API true names (`subdtech`/`maxsubiter`); one-class solver ladder + telemetry classes; forensic≠builder partition A/B; HARD GATE persist after expensive steps; `BLOCKED_SOLVER` delivery matrix. Trial numbers remain forensic only.

- [CHT coupling and energy gates](docs/cht-coupling-energy-gates.md) — outlet `SOFTWARE_DOC_DEFAULT`; S0 requires Inflow + ConvectiveOutflow + Segregated sequence; copy solver **class** not counterpart node tags; missing HT outlet feature is a first-class BC gap before mesh
- Companion ERS: `decision-gate` / `paper-analysis` / `comsol-debug` / `validation` (NONPHYSICAL veto retained)
- Principles index: [docs/uplift-20261029/GENERALIZABLE_PRINCIPLES.md](docs/uplift-20261029/GENERALIZABLE_PRINCIPLES.md)

Version **0.3.2** institutionalizes **paper-silent → official software documentation** defaults for CHT (not a single-case exception):

- Hierarchy: paper explicit > installed official product docs (`SOFTWARE_DOC_DEFAULT`) > option cards / ask user > never GUI/prior-trial habit; counterpart MPH is post-solve compare only
- [CHT coupling and energy gates](docs/cht-coupling-energy-gates.md) — P0 `5b` Inflow default when paper silent; inlet thermal migration playbook (Temperature→Inflow) without greenwashing enthalpy
- Companion ERS policy lives in `paper-analysis` / `decision-gate` / `session-boot` (software-doc default)

Version **0.3.1** added CHT / compare hygiene docs (no new MCP tools; does not upgrade scientific VALIDATED status):

- [CHT coupling and energy gates](docs/cht-coupling-energy-gates.md) — inlet **Inflow** preference, coupling probe export, independent hydraulic vs enthalpy gates
- [Paper-only vs oracle compare](docs/paper-only-vs-oracle-compare.md) — counterpart labels (`Z_ORACLE` / `B_REPLICA` / `PAPER_FIGURE` / `NONE`); build vs compare phase separation

Mandatory global NITF velocity-wiring rewrite rules remain deferred pending clean probe evidence.

Version **0.3.0** added an **outer** uncertainty-aware recursive self-improvement (RSI) layer:

`Experience → Infer → Improve → Evaluate → Calibrate → Retain`

It does **not** replace the existing MCP-only closed-loop controller. Model edits alone are not RSI; only gated `AgentVersion` updates (`A₀ → A₁`) count as harness-side self-improvement.

### V0.1 RSI scope (from 0.3.0)

- Unknown parameter detection + `ParameterBelief`
- Evidence provenance including EvidenceRecord origin `inferred`
- Plausible-range inference (not silent point guesses; not fake confidence intervals)
- U×S decision gate + endpoint sensitivity plan/propagation helpers
- Inference disclosure reports
- Conditional / insufficient scientific validity under inferred inputs
- `ExperienceRecord`, calibration compare, AgentVersion retain/reject
- Unit tests CASE1–7 — **`tested_with_mock`**
- Real-COMSOL endpoint propagation and held-out physical audit — **`NOT_RUN`**

No new MCP tools in 0.3.0 (API + tests first). P3 full Bayesian / MC UQ remains **NOT_IMPLEMENTED**.

Closed-loop reconstruction (EvidenceRecord, DecisionRequest, persistent controller, repair/calibration provenance) remains **`tested_with_mock`**, **not** `tested_with_real_COMSOL`. See [closed-loop controller](docs/closed-loop-controller.md) and [uncertainty-aware RSI](docs/uncertainty-aware-rsi.md).

Geometry reliability extension based on commit a012b21bcfd604adb8843f3b0e734478fc13b4a3 of tsuntungngaing-jtn/comsol-automatic. Not an official COMSOL product. Original provenance and licenses are in NOTICE.md and vendor/installed-mcp/LICENSE.

This package contains the skill, MCP adapter, vendored tools, catalog metadata, original teaching source, tests and installation scripts. It contains no commercial COMSOL models, manuals, research results, credentials or Python environment.

On Windows, extract the full folder to a new directory, then run `powershell -ExecutionPolicy Bypass -File scripts/install.ps1`. Register the MCP command using the new folder's `.venv/Scripts/python.exe -m server.main serve --transport stdio` and its working directory. Set COMSOL_OUTPUT_ROOT to your research workspace, not this folder. See docs/connectors.md for details. Existing skills/connectors are not replaced automatically.

The executable and package remain named comsol-automatic for compatibility. The discoverable skill name is comsol-automatic-6-4-en.

Run `python -m unittest discover -s tests` for Python/protocol checks. Real COMSOL validation must run through MCP. Read docs/validation.md before using results in research.

Software correctness and scientific correctness are reported separately.
