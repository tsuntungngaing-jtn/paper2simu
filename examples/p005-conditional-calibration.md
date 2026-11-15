# P005 conditional calibration example

Use the packaged [reproduction task](../prompts/paper-reproduction-task.md) and [calibration card](../prompts/conditional-calibration.md). This example provides no solver authorization. Its trial values are synthetic.

- Reference: Chen et al. (2022), [DOI 10.1016/j.csite.2022.102073](https://doi.org/10.1016/j.csite.2022.102073). Select one MMC geometry and flow rate. Fill the exact reference values, source locations and absolute-temperature or temperature-rise convention before scoring. Declare the installed solver and MCP route.
- Lock the paper heat flux, dimensions, flow rate, materials and applicable physical conditions. For one tentative, let \(\alpha\) blend two justified inlet profiles, scaled so the integral of inlet velocity preserves the assigned volumetric flow. Read back profile, effective boundary face and actual flow before submitting.
- Extract \(R_t\) using Eq. (9), \(h\) using the declared solid–fluid interface and \(T_w\) with Eq. (10)–(11), and bottom-surface temperature spread using Fig. 9. Freeze the definitions and record the wetted area, temperature averages, bottom extrema and coordinates. Log absolute W and the denominator of any heat/energy imbalance.
- Use a saved baseline if it matches. Chen's Table 4 reports grid variation of pressure drop and maximum silicon-base temperature. Compare grid sensitivity of all task-critical QoIs independently. Use a separate, specified flow rate as holdout with the selected hypothesis frozen.

| Synthetic trial | Held fixed | Bottom temperature-spread error | Decision |
|---|---|---:|---|
| Baseline | \(\alpha=0\), base grid | 42% | Baseline for comparison |
| Grid diagnostic | \(\alpha=0\), refined grid | 37% | Numeric drift of 5 percentage points |
| Parameter diagnostic | \(\alpha=1\), base grid | 39% | HOLD. With both QoI predictions below the reference, the 3-point response is smaller than the measured grid drift |

The demonstration assumes signed deviations \(-42\%\), \(-37\%\), and \(-39\%\), respectively. Actual tasks retain the corresponding raw QoIs, errors, evidence paths, solver identities, other protected metrics and authorization references in the task card and trial matrix. This example reports no feasible points and no physical validation.
