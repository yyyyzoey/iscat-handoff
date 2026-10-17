# v101 Review
## What v101 establishes
1. Independent 5040-row verification: 5040/5040 match (0 mismatch)
2. Corrected reference pools (endpoint=ALL24, not ALL48)
3. Correct distance formulas (concatenated vector, not per-channel)
4. 46 original array snapshots copied and SHA-verified
5. All prior results preserved read-only
## v100 defects fixed
1. Reference pools: ALL48 -> ALL24 for endpoint queries
2. Distance: concatenated vector (not per-channel normalized)
3. Coverage: 5040 (not 3528)
4. Snapshots: actually copied (not just counted)
## Not claimed
No diameter, causality, detectability, or identifiability claims.
