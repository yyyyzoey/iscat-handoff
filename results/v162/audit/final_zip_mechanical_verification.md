# V162 return ZIP - independent mechanical verification

- artifact: `iscat_v162_return.zip` (410926 bytes)
- sha256: `f00ac5d9b2700affa33d22652ce71e48723571e001fc510ee4ce2d926a685c5e`
- members: 78 (manifest rows 77 + `manifest_sha256.csv`)
- CRC `testzip()`: True
- members re-hashed and matched to manifest: 77/77
- member set == manifest + manifest file: True
- mismatches: []
- verdict: **MECHANICALLY_CONSISTENT** (scope: ZIP_STRUCTURE_ONLY_NOT_SCIENTIFIC_ACCEPTANCE)

This receipt is external to the ZIP by construction (a ZIP cannot contain its own digest);
the official packer excludes `archive_receipt.json` from members for the same reason.
