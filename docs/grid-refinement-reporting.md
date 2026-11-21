# Grid-refinement reporting

Record the refinement result for each frozen QoI, including its definition, physical domain, units and extraction method. Compare the same physical case and numerical settings apart from the planned spatial refinement. Keep the time step fixed or estimate its effect separately. Record native convergence, final monitor drift, the relevant local resolution (for example gap cells and near-wall spacing), the mesh family, each physical mesh scale `h` and its definition, and the run/mesh/solution IDs. When local or directional refinement changes the mesh family, document the relevant directional scales and justify any effective scalar `h`. Cell counts alone cannot establish comparability.

## Two meshes

| Report | Evidence |
|---|---|
| Observed mesh sensitivity | Report signed `f_coarse − f_fine` in QoI units. If the reference scale is meaningful, also report the relative difference with its denominator. |
| Conditional two-grid GCI | Use Roache (1994), Eq. (10), only after documenting comparable systematic refinement, iterative and extraction errors small relative to the grid response, a defensible source for the order `p`, and the evidence for assuming this problem is in the asymptotic range (which can include relevant prior refinement evidence). Label the estimate conditional and label `p` assumed or externally supported for this pair. |

Use `r = h_coarse/h_fine > 1`. The Eq. (10) fine-grid relative estimate is `GCI_fine = 3 * abs((f_coarse - f_fine)/f_fine) / (r**p - 1)`. Multiply by 100 to report percent. State the factor of safety `F_s = 3` for this procedure. When the fine-grid value is near zero or the change is within iterative/extraction noise, report the signed absolute difference and its noise scale, or use a separately justified predeclared normalization with its units. A two-point fit cannot infer `p` or establish that this run pair is asymptotic. A nominal solver scheme order alone is insufficient evidence.

Roache's examples show why the raw percentages can be misleading. With `r = 1.5`, `p = 1`, and a 4% fine-normalized change, the conditional fine-grid GCI is 24%. With `r = 2`, `p = 2`, and a 6% change, it is 6%. Record assumptions and keep this estimate out of automatic calibration, error bars and reproduction acceptance.

## Three or more meshes

For a Celik et al. (2008) GCI study, record both refinement ratios, the observed order with method and applicability checks, and fine/medium QoI differences with signs. Check observed convergence behavior and the asymptotic evidence. With sign changes, a noisy or poorly resolved trend, or inconsistent grids, keep the observations and justify a suitable alternative method or report the estimate as unavailable. Use the [existing Éça–Hoekstra review](eca-hoekstra-2014-original-paper-review.md) for the separate multi-grid fitting method. Its admission helper checks comparability and does not calculate uncertainty.

Keep grid discretization, iteration, time-step and paper-reference errors distinct. Compare tentative parameter effects with observed numerical variation for the same QoI under the frozen calibration contract. If variation is comparable to the effect, keep the trial at HOLD pending discriminating evidence. GCI is a discretization estimate for a stated QoI and mesh, not a probability interval or evidence of experimental agreement.

Sources

- [Roache (1994), J. Fluids Eng. 116, 405–413, especially Eq. (10) and Eq. (19)](https://doi.org/10.1115/1.2910291)
- [Celik et al. (2008), J. Fluids Eng. 130, 078001](https://doi.org/10.1115/1.2960953)
- [Éça and Hoekstra (2014), J. Comput. Phys. 262, 104–130](https://doi.org/10.1016/j.jcp.2014.01.006)
