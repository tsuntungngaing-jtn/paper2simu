# Case catalog
Use comsol_list_cases for compact metadata; request one case_id with detail=true for its path and workflow. The catalog references locally licensed official files and one original teaching example; it redistributes no official model or manual. Paths were inherited from an earlier-version catalog and must be checked against the actual installation. File availability is not license or solver verification.

The English catalog preserves case IDs and paths. It intentionally does not carry forward historical validation claims. Match the installed official tutorial for settings and numerical comparisons; don't use the original prescribed-convection heat sink as proof of coupled turbulent flow.

For the original heat sink, `comsol_run_case` defaults to build-only and saves geometry, physics, mesh and study nodes. Set `solve=true` to run both studies, or specify `std1` (stationary) or `std2` (transient) for a single study. A transient-only run leaves the stationary/transient agreement check unexecuted.
