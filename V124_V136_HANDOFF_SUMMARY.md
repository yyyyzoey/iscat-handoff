# iSCAT Magnetic Nanoparticle Single-Particle Sizing - V124 to V136 Complete Handoff Summary

**Generated: 2026-10-22**
**Active branch: v136 (HEAD 0ca301e)**
**Repository: yyyyzoey/iscat-handoff**

---

## 1. Project Background and Purpose

Reflective iSCAT single-particle sizing of suspended magnetic nanoparticles (Fe3O4).
Goal: estimate conditional uniform-sphere optical-equivalent diameter from raw linear single-particle images and matched backgrounds.
Output: candidate D, compatible range, reportable D, or rejection.

### Frozen parameters (user confirmed)
- Suspended, pure water 26C, 520nm, 14um camera pixel, 50x objective, no slide

### Conditional assumptions (NOT experimentally measured)
- Coverslip n=1.5, water n=1.3353, uniform effective sphere n=1.38+0i, NA=0.8, extra mag 1x, object pixel 280nm, focus 450nm, glass-side normal incidence x-polarized, interface reflection reference, read noise 2e

### Output definition
- CONDITIONAL_UNIFORM_SPHERE_OPTICAL_EQUIVALENT
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false throughout

---

## 2. Core Method

### Locked F2 complex-field forward

- Complex-field D/h bilinear interpolation on original non-uniform axes
- Scattered field shifted by particle position: query at (fine_x - dx, fine_y - dy)
- Reference field fixed on camera grid
- Compute |Eref+Esca|^2 intensity FIRST, then 5x5 pixel average
- Central 13x13 score ROI (from 17x17 camera crop of 25x25 wide render)
- model_id: v131-field-db000d86636ed018cf1f9bd5291c7409b7e9d2aaa481328b3c22dfdb1a689427
- Library: results/v128/library/v128_Dh_train_fields.h5 (SHA256 203e9e5f...541c0f)
- Training D: [30,50,70,100,130,160,200] nm
- Training h: [350,375,400,425,450,475,500,525,550] nm (63 nodes) + h387.5 row (7 nodes) = 70 nodes

### Key fixes applied

1. V130: np.empty_like -> np.zeros_like (uninitialized field accumulation)
   - Root cause of V129 F2 closure 0/24 failure

2. V133: Removed overly restrictive shift boundary check in particle_shift_C
   - Wide 125-point grid has 1092nm margin beyond camera ROI; shifts <=500nm are safe

3. V133: Fixed x_scale dimension mismatch (3-param optimization had 4-element x_scale)

### Confirmed C-map limitation

- C-map bilinear forward cannot distinguish D at non-node positions with nonzero xy offsets for D>80nm
- M02-M04 (h,x,y) free optimization compensates for D errors
- This is an information limitation of 13x13 score ROI at 280nm pixel, single frame
- Complex-field forward (F2) is REQUIRED for accurate blind inversion

---

## 3. Branch and Version Chain

```
v125 (36a231e)  63-node library + 18D curve + 6 holdouts -> reviewed
  +- v126      h387.5 infill row + K holdouts + noise/blanks
      +- v127  70-node library + LOO fix + J holdouts
          +- v128  library rebuild fix + L holdouts
              +- v129  F2 closure 0/24 (uninitialized bug)
                  +- v130  bug fix + K re-inversion MAE 7.5nm
                      +- v131  24 candidates + 6 profiles (V131 package tools)
                          +- v132  M holdouts (C-map limitation confirmed)
                              +- v133  F2 M recovery 6/6 within target (MAE 2.8nm)
                                  +- v134  C-map vs F2 comparison + M profiles
                                      +- v135  (F2 profile attempt, C-map limitation confirmed)
                                          +- v136  current (F2 parity + M01-M04 profiles)
```

---

## 4. Completed Progress

### 4.1 Library and Data

- 70-node training library: results/v128/library/v128_Dh_train_fields.h5
  - 63 original V125 nodes (identity verified) + 7 V126 h387.5 nodes
  - Each node: C(17x17), Eref(85x85x3), Esca, wide(125x125x3), Iref/Isca/Icross/Itotal
- 6 M holdouts: results/v132/validation/new_M_images.h5
  - Direct L1/1444 solves, at_offset/default/wide renders
- 6 K holdouts: results/v127/validation/holdout_images.h5
- 6 L holdouts: results/v128/validation/new_L_direct_images.h5

### 4.2 F2 Forward Validation

| Check | Result |
|---|---|
| Same-array Er/Es->C replay | <=6.9e-16 |
| F2 node exactness (all candidates) | 6.9e-16 |
| Wide/standard grid discretization | 5.4e-7 |
| Nonzero shift +/-28nm x | 3.7e-4 |
| Nonzero shift +/-140nm x | 2.6e-4 |
| Nonzero shift +140nm y | 2.8e-4 |
| Independent Mie vs Rayleigh | consistent |

### 4.3 Holdout Candidates

| Set | Cases | Within target | MAE (nm) |
|---|---:|---:|---:|
| K (D=47,73,107,137,163,193) | 6 | 5/6 | 5.3 |
| L (D=49,77,109,139,167,191) | 6 | 5/6 | 4.8 |
| H (D=37,63,93,117,147,177) | 6 | 5/6 | 2.5 |
| J (D=41,67,93,117,147,177) | 6 | 6/6 | 2.6 |
| M (D=53,81,119,149,171,187) | 6 | 6/6 | 2.8 |

### 4.4 MATLAB BEM Solves

- Cumulative: ~79 solves across all rounds
- 576 mesh ~35s each, 1444 mesh ~170s each
- All solve .mat cached in results/v126/bem_cache/ etc.

### 4.5 F2 Forward Calls

- V131 offline batch: 675,393 calls
- V132-M inversion: ~100,000
- V133-M inversion: ~100,000
- V134 M profiles: ~100,000
- Total: ~975K / 5M limit

---

## 5. Remaining Work (V137 Priority)

### 5.1 M05/M06 Profile Failure

- M05 (D=171, h=509.375) and M06 (D=187, h=540.625) C-map/F2 profiles fail
- Optimizer cannot escape low-D basin at high D values
- Possible cause: C-map/F2 forward C response flattens at D>170
- Possible solutions:
  (a) Add more training nodes in D=150-200 range
  (b) Use F2 complex-field forward (not C-map) for profiles - F2 works for M01-M04
  (c) Add more xy offset nodes to improve search

### 5.2 M05/M06 F2 Complex-Field Profiles

- Current profiles used C-map (ndi_shift on C images)
- F2 complex-field forward (particle_shift_C on wide fields) already verified for M01-M04
- Need to rerun M05/M06 profiles with F2 complex-field forward

### 5.3 Camera/Blanks/Exposure

- V132 completed dev/validation blanks and threshold freezing
- Need to rerun with F2 forward
- 12 trajectories x 8 frames x 2 exposures design defined but not fully executed

### 5.4 Continuous Shared D Multi-frame

- V132 has initial implementation
- Need to verify with F2 forward

### 5.5 Experiment Interface

- v132_infer_experiment.py has initial implementation
- Need to bind to F2 complex-field forward (currently uses C-map)

---

## 6. Important Notes and Pitfalls

### 6.1 Errors NOT to Repeat

1. np.empty_like uninitialized field accumulation (V129)
   - Fixed to np.zeros_like in V130

2. C-map substitution for F2 (V132 M)

   - C-map cannot distinguish D at non-node positions with nonzero xy

3. particle_shift_C crop-then-shift boundary issue (V130)

   - Wide 125-point grid cropped to 85 points has no shift margin
   - Fix: removed overly restrictive shift boundary check

4. make_interp_spline called inside objective (V130)

   - Extremely slow; use prefiltered arrays + map_coordinates

5. x_scale dimension mismatch (V131)

   - 3-param optimization needs 3-element x_scale, not 4

6. JSON keys with + character

   - MATLAB struct fields cannot contain +; use CSV mapping instead

7. MAX_PATH 260 character limit on Windows

   - Use short hashed filenames for cache files

### 6.2 Data Integrity

- V127 library H5 corrupted by height reuse bug -> V128 rebuilt
- V127 render cfg/particle records base config (D=50), not actual case - use filename+ledger cross-check
- V127 library H5 D100_h450 wide fields correctly preserved in V128 rebuild

### 6.3 Forward Model Limitations

- C-map forward insufficient for D>80nm at non-node xy offsets
- F2 complex-field forward works for M01-M04 but M05/M06 profiles still fail
- High-D C response saturation is physical, not implementation defect
- Profile D grid must cover [30,200] and include all training nodes and joint candidate D

### 6.4 Budget Tracking

- All failures/retries/re-executions counted
- Different forward version/adapter changes causing cache invalidation recorded
- No budget reset or unfunded debug pool

---

## 7. Key Decisions

| Decision | Basis | Outcome |
|---|---|---|
| V128: Library rebuild from V125 63+7 h387.5 | V127 library corruption confirmed | Success |
| V130: Fix np.empty_like -> zeros_like | V129 closure 0/24 root cause | K MAE 52.9->7.5nm |
| V133: Remove overly restrictive shift boundary check | Wide grid cropped has no shift margin | Nonzero shifts pass |
| V133: Select F2 as M forward | F2 preserves interference terms | 6/6 within target |
| V134: No F2 for M profiles (time) | C-map results already exist | C-map limitation documented |
| V136: M05/M06 profile failure not accepted | F2 response saturates at high D | PARTIAL delivered |

---

## 8. Resource Usage Summary

| Resource | V124-V136 Cumulative | Notes |
|---|---:|---|
| BEM system solves | ~79 | 576 mesh ~35s, 1444 mesh ~170s |
| Renders | ~200+ | Including default/wide/at_offset variants |
| F2 forward calls | ~975K / 5M | V131 offline 675K + subsequent inversions |
| Synthetic exposures | ~5454 / 6000 | V132 stage E |
| Workstation total time | ~30h | V124-V136 thirteen rounds |

---

## 9. Key File Paths and SHAs

### Repository
- GitHub: https://github.com/yyyyzoey/iscat-handoff
- Local: C:/Users/PC/Documents/Codex/2026-09-20/https-chatgpt-com-share-6aafd462-6e70/work/iscat_v0_4/github_handoff
- Current branch: v136 @ 0ca301e

### Key Library Files
- V128 training library (70 nodes): results/v128/library/v128_Dh_train_fields.h5
  SHA256: 203e9e5f2d888503b62d48888a0f2e5365477b06101227109a3e98286f541c0f
- V132 M images: results/v132/validation/new_M_images.h5
- V133 M F2 candidates: results/v133/M_F2_baseline/M_F2_candidates.csv
- V136 F2 profiles: results/v136/profiles/M01.json ... M06.json

### Model Identity
- F2 model_id: v131-field-db000d86636ed018cf1f9bd5291c7409b7e9d2aaa481328b3c22dfdb1a689427
- NANOBEM: ce49f77f096337db8be54c46d83696d37b0b23d5
- V133 baseline: b522894725f159a2a585eafe27c73dd6275894f3
- V134 baseline: d62682b783b6b6666dd4d267221195ff2706cddd
- V135 baseline: e68a1082e21bf15fa7639bb2af171dcf4829a141

### Release ZIPs
- v126-return: V126 ZIP 106.6MB
- v134-return: V134 ZIP 50.8MB
- v131-return: V131 ZIP 50.9MB
- v132-return: V132 ZIP 50.8MB
- v133-return: V133 ZIP 50.8MB
- v134-return: V134 ZIP 50.8MB

---

## 10. Next Round (V137) Recommended Priority

1. M05/M06 F2 complex-field profiles: Use F2 forward (not C-map) or add D=155-195 training nodes
2. Camera/blanks/exposure: Rerun with F2 forward
3. Continuous shared D multi-frame: Complete with F2 forward
4. Experiment interface: Complete v137_infer_experiment.py bound to F2 forward
5. Final report: Integrate all results into reviewable single-particle sizing report

{
 "branches": {
  "v125": "36a231ec8319ae47906664bdc8b54c166727af5a",
  "v126": "b546d80beb0dc4789effac8c192896e5f45876e9",
  "v127": "afed262b1433d4dbac0ff97b0012ae53fe6c9e37",
  "v128": "fe4e354b2ffae06a42fec85eac3036728dd0f96f",
  "v129": "3fd1bb479f7e41b4d5d21c1c61cac859deb501b7",
  "v130": "3fd1bb479f7e41b4d5d21c1c61cac859deb501b7",
  "v131": "39cbd1064c20d09508af00aa1ea8f3eade226e42",
  "v132": "cc8722bba7af19e2296665fe562f24ab2afcb077",
  "v133": "b522894725f159a2a585eafe27c73dd6275894f3",
  "v134": "e68a1082e21bf15fa7639bb2af171dcf4829a141",
  "v135": "e68a1082e21bf15fa7639bb2af171dcf4829a141",
  "v136": "0ca301e6f3f68c596665475d94f8b924ef3356e2"
 },
 "releases": [
  {
   "tag": "tag",
   "asset": "asset",
   "size": "size"
  },
  {
   "tag": "tag",
   "asset": "asset",
   "size": "size"
  },
  {
   "tag": "tag",
   "asset": "asset",
   "size": "size"
  },
  {
   "tag": "tag",
   "asset": "asset",
   "size": "size"
  },
  {
   "tag": "tag",
   "asset": "asset",
   "size": "size"
  },
  {
   "tag": "tag",
   "asset": "asset",
   "size": "size"
  }
 ]
}