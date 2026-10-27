# V164 scope and changes

Scientific change: replace only the restricted straight-path continuation question with 24 bounded fixed-D conditional model-separation tasks. No four-parameter diameter fits. Three groups, two declared diameter displacements, four declared height constraints, two initial points. New authorized cap 10,000 real attempts; no BEM/render/camera/noise/Jacobian batches.

Preserved bytes: v152_budget_store.py, v152_gls_core.py, v157_height_design.py. V163 optical source and the already reconciled CRLF source remain fixed at commit 06c54419c590b6ddadc50cd6117a7a54b2cf5ddf.

New components: bounded nuisance-only optimizer, checkpoint preservation of all feasible witnesses, exact-D/exact-height checks, explicit common feasible pool, per-start hard cap, strict source/test/ledger binding, independent final point-set verification, complete installer and embedded launcher. All output minima are attainable upper bounds, not certified global minima or confidence intervals.

Final new suite: 65 actually executed local tests; 195 actual phase reports. The older 247-test V163 production receipt is rechecked as historical evidence, not counted as new tests.
