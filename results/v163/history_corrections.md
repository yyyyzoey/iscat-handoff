# V163 historical corrections

V161 used a separate tools/v161_design.py, not the approved full launcher workflow. Its 204 coefficients have reversed free/exact semantics and finite-design dimension errors caught as zero compensation. Its eight probes collapse the ANON id and mix all four particles. Do not use them as nonlinearity or precision evidence.

The original archive is preserved with SHA/CRC evidence. Loader use and full V161 resource total remain unverified. V163 keeps the approved GLS and optical model, and must complete the exact task set.

## Results addendum (post-launcher)

The launcher ran end to end (prepare, run_all, final_pack) with exit 0 and the
results were committed as parent commit
`b97331140907f0fdf7101fdf8711c6170a5c4bf8`; the code commit of the deployed
execution tree is `5ccd552d65a698a67f9550da74629ec36f65f5a0`. The addendum below
only adds read-only evidence and re-packs the return archive. It performs no
model forward call and consumes no budget.

1. The contract requires the return ZIP to carry the external mechanical
   receipt of the original V162 return. That receipt
   (`audit/v162_portable_check_receipt.json`) was regenerated here by actually
   executing the supplied `tools/v163_bundle/audit/audit_v162_return.py` against
   the V162 return ZIP exported from this repository's own frozen object
   `results/v162/iscat_v162_return.zip` (sha256
   `47e7a249511c8bd998f48d30418757d00690cec6290ce83b0dee60ec5678a381`, 417589
   bytes, identical to the `C:\iscat\v162` worktree copy and to the V162
   handoff's separate review) and against the V162 handoff archive
   (`iscat_v162_handoff.zip`, sha256
   `4dc3f129f46110002dd5c56b7186794a20cfddfafc8e5a1d77cad44a902f840b`). All 222 collected node ids and 666 phase reports
   match the V162 handoff inventory; SQLite integrity is `ok`; LOADER_1 is
   `FAILED` with cap 100 / used 0 and zero attempts; 12 groups and 1224 design
   evaluations were re-counted. The regenerated receipt is content-identical to
   the author-supplied copy in the handoff bundle (byte length differs only by
   JSON indentation/newline: 505 vs 484 bytes).
2. `audit/v162_zip_mechanical_recheck.json` (source:
   `audit/v162_zip_mechanical_recheck.py`, no bundle/packer imports, SQLite
   opened read-only) independently re-derives every printed field from the raw
   frozen bytes: CRC, member set, 1:1 manifest hashes, tests 222/666, ledger
   rows and the packed `tasks/LOADER_1/result.json` seal. All checks pass.
3. `audit/independent_recheck_v163.py` re-parses the final V163 return ZIP,
   re-derives the ledger from `logs/v163_budget.sqlite` read-only, re-derives
   the 247/741 test receipt, and recomputes all 72 nonlinear-probe identities
   from the raw stored arrays (`source_context/v156/*.json` plus the anchor
   `C`) by pure algebra.
4. As in V162, the ZIP cannot carry its own digest, so `archive_receipt.json`
   and the `audit/independent_recheck_v163.*` outputs are external to the
   delivered ZIP, written after the final pack, and committed next to it. This
   mirrors the official packer, which likewise excludes `archive_receipt.json`
   from members. For the same self-reference reason the addendum's own results
   commit SHA cannot appear inside the archive it creates; it is reported in
   the delivery message and is recoverable from this repository's git history
   (`git -C <repo> log -1 -- results/v163`).

Mechanical, ledger and algebraic reconstruction do not constitute physical or
experimental validation; `all_reportable_D_null=true` and
`EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED=false` remain in force.
