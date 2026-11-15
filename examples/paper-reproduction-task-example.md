# Filled task-card example — COMSOL conduction reconstruction

**Illustrative training example, not a published paper and not an executed simulation.** For a real reproduction job the agent loads packaged `prompts/paper-reproduction-task.md`, `paper-input-reconstruction.md`, and `conditional-calibration.md` when calibrating; this file is only a **filled task card**. The card alone is not a replacement policy.

- Solver: COMSOL, via the simulation machine's configured COMSOL MCP. Discover actual version/modules/session before modeling; do not launch Fluent. No machine connection or launch authorization is asserted by this example.
- Source: analytical constant-property one-dimensional conduction benchmark. Reference derivation, not claimed paper data: L=0.01 m, A=0.0001 m², k=10 W/(m K), end temperatures 310 K/300 K, insulated lateral walls. Q=k A ΔT/L=1 W; midpoint T=305 K.
- Scope: stationary solid heat transfer, rectangular prism 0.01 ×0.01 ×0.01 m, explicit constant conductivity; no convection/radiation. Conditional model replaces any unresolved material identity with the stated constant k and labels it an assumed benchmark material.
- Output: a new `conduction-reconstruction` directory under the configured output root; never overwrite input models.
- Main reference quantity: integrated axial heat rate Q in W, both end sections with sign convention documented, reference magnitude1 W. Primary comparison Q error <15%. Midpoint temperature is supplementary diagnostic, not an extra acceptance criterion.
- Conservation: stationary inward plus outward heat rate zero with no volumetric source/storage. Normalize absolute imbalance by1 W; example engineering tolerance <1%, predeclared for this simple benchmark, not universal.
- Mesh: two meaningfully refined meshes with at least twice the axial subdivisions, compare Q; example sensitivity target <2%. Report two-grid sensitivity only. If unmet, use third mesh within budget or report incomplete. Time step: not applicable (stationary).
- Native convergence: retain actual configured stopping test and observed reason; no extra residual floor. Record warnings and native flux definitions.
- Budget proposal for an operator to authorize: ≤3 solves, ≤2 reversible repair rounds, ≤30 minutes, ≤4 cores and8 GB. If unsuitable for the discovered host, revise before running.
- Declared necessary checks: numerical (actual native convergence), scientific (conservation and mesh sensitivity), reopen (saved-model readback and Q). Required check results and actual evidence paths must be attached; do not prefill PASS.
- Expected reconstruction type: conditional analytical benchmark. All execution/check results initially NOT_RUN.

Example controller comparison contract (a project input, not a skill default):

```json
{"acceptance_spec":{"required_checks":["numerical","scientific","reopen"],"criteria":[{"id":"case1:Q","metric":"relative_error","reference":1.0,"tolerance":0.15,"unit":"W"}]}}
```

## Illustrative REPRODUCTION_DASHBOARD (not executed)

### A. SOURCE_MAP

| input_id | quantity | source location | origin | evidence | conflict / missing |
|---|---|---|---|---|---|
| L | length | benchmark derivation | paper_reported | L=0.01 m in task card | — |
| k | conductivity | benchmark derivation | paper_reported | k=10 W/(m·K) | — |
| mat_id | material library tag | n/a | software_documented | constant-k substitute | not a named library material |

### B. BASELINE_INPUTS

| input_id | value+unit | layer | in equations/geometry | notes |
|---|---|---|---|---|
| L | 0.01 m | lock | yes | prism length |
| A | 1e-4 m² | lock | yes | cross-section |
| k | 10 W/(m·K) | lock | yes | constant property |
| T_hot / T_cold | 310 K / 300 K | lock | yes | end temperatures |

### C. ITERATION_DELTA

| trial_id | parent | change → new value | expected | measured e/J | decision | artifact |
|---|---|---|---|---|---|---|
| T000 | — | baseline build | — | NOT_RUN | KEEP | conduction-reconstruction/T000/ |
| T001 | T000 | (example only) mesh×2 axial | lower Q sensitivity | NOT_RUN | HOLD | — |

### D. OUTPUT_VS_BENCHMARK

| metric_id | case | paper benchmark | reproduced output | error | gate | status | best trial |
|---|---|---|---|---|---|---|---|
| case1:Q | stationary | 1.0 W (derivation) | NOT_RUN | — | <15% | NOT_RUN | — |

Summary lines (example placeholders): reconstruction type = conditional analytical; best comparable trial = NOT_RUN; open items = numerical/scientific/reopen checks.

## Same prompt, Fluent selection

Reuse the same packaged acceptance prompt without a second policy document. Change only the task card solver line, for example:

- Solver: Fluent, via the simulation machine's configured official PyFluent MCP. Discover actual version/session before modeling; do not launch COMSOL.
- Keep the same metric IDs, relative-error `<15%` (or an explicit override), conservation and two-grid sensitivity definitions, budgets and `acceptance_spec` shape.
- Route Fluent native reports for fluxes/residuals; still report execution, checks and paper agreement separately.

Do not maintain a Fluent-only acceptance document. For a real paper replace the analytical source and task quantities with verified paper-specific inputs and locations. Do not relabel this example as real-COMSOL or real-Fluent testing evidence.
