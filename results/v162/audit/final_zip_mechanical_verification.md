# V162 return ZIP - independent mechanical verification

- artifact: `iscat_v162_return.zip` (417589 bytes)
- sha256: `47e7a249511c8bd998f48d30418757d00690cec6290ce83b0dee60ec5678a381`
- members: 85 (manifest rows 84 + `manifest_sha256.csv`)
- CRC `testzip()`: True
- members re-hashed and matched to manifest: 84/84
- member set == manifest + manifest file: True
- mismatches: []
- verdict: **MECHANICALLY_CONSISTENT** (scope: ZIP_STRUCTURE_ONLY_NOT_SCIENTIFIC_ACCEPTANCE)

This receipt is external to the ZIP by construction (a ZIP cannot contain its own digest);
the official packer excludes `archive_receipt.json` from members for the same reason.
