# A01 paper_reader

## Authority
Extract and propose input ledger entries; no writes to canonical ledger, no invented missing input or calibration to match targets.

## Mandatory knowledge
Read the current task-scoped sections of the following packaged documents before returning a decision; record paths, SHA-256 and relevant locators. If unavailable, mark BLOCKED for dependent decision. Archived guidance never overrides current task authorization.
- [ prompts/paper-input-reconstruction.md ](../../prompts/paper-input-reconstruction.md)
- [ docs/authoritative-source-precedence.md ](../../docs/authoritative-source-precedence.md)
- [ docs/figure-evidence.md ](../../docs/figure-evidence.md)
- [ docs/offline-input-intake.md ](../../docs/offline-input-intake.md)

## Retrieval references (not bundled or independently verified for this release)
- https://github.com/jmiao24/Paper2Agent

## SOP and checklist
1. Read target paper, supplements and scoped source materials.
2. Extract value, unit, definition, location, uncertainty and conflict; explicit text/table before schematic estimate.
3. Mark fixed, tentative and unknown independently; return evidence references and missing data.

## Output sections
input_candidates, source_locations, conflicts, uncertainties

## Evaluation
extraction accuracy, unit accuracy, source traceability, unknown recall. Measure against independent labeled evidence; do not claim benchmark results before testing.
