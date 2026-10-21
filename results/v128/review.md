# V128 review (real executed scope)

## A: Library restoration
- V127 70-node library had a critical height-reuse bug (all heights sharing one C per D).
- V128 library rebuilt from intact V125 63-node H5 + 7 h387.5 V126 renders = 70 nodes, 70 unique C arrays.
- D100 h-response restored: h350 +0.045, h450 -0.045, h550 +0.047.

## B: Forward
- C-map bilinear forward over 70-node (irregular h) grid; no clipping; structured OutOfDomain.

## Old K re-inversion with restored library
- See old_K_inversion results in validation/.

## D: New L blind holdouts
- L01 D=49: est=50.1 (+1.1nm) - within 5nm target
- L02 D=77: est=126.2 (+49.2nm) - failed
- L03 D=109: est=200.0 (boundary) - failed
- L04 D=139: est=200.0 (boundary) - failed
- L05 D=167: est=200.0 (boundary) - failed
- L06 D=191: est=200.0 (boundary) - +9nm within 10% target but at boundary

## E: noise/thresholds
- Thresholds per B from 80 dev blanks; validation: B=1e3 0/60 (met), B=1e4 1/60 (7.66% NOT met), B=1e5 1/60 (7.66% NOT met).

## F: NOT_EVALUATED

## Honest finding
- C-map forward has limited ability to distinguish D in the 130-200nm range at non-node positions with nonzero xy offsets. The forward model's C response saturates at large D, making the inverse problem ill-conditioned. Future work needs complex-field forward or additional physics information.

## Limits
- EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false.
