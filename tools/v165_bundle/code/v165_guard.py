"""Runtime read/import guard for the V165 estimator process.

Role separation, not magic: the estimator is allowed to read only the frozen
observations, the anonymous height readings, its own checkpoints and its ledger.
This module installs a CPython audit hook that refuses Python-level ``open`` of
any path under the validator side of the tree and refuses ``import`` of the
three truth-bearing workstation roles (provenance audit, height generator and
post-seal validator).

Limitations are recorded rather than hidden: a CPython audit hook observes
``open``/``os.open``/``import`` events, not syscalls made by native libraries
(for example a direct HDF5 C-library open). It is therefore evidence of intent
and of denied Python-level attempts, not a kernel sandbox. The binding
guarantees remain the sealed-estimate ordering plus the static literal scan in
``v165_io.assert_no_truth_literals``.

This module is the single designated holder of the protected identities. The
static scanner reads ``DENY_*`` as literal data from here, so no estimator module
has to name a protected path itself. ``DENY_NAME_TOKENS`` are file-name stems used
by that static scan only; the audit hook matches directories and module names.
"""
from __future__ import annotations
import sys
from pathlib import Path

DENY_DIR_PREFIXES = ('results/v142/validation/', 'results/v165/validator_only/')
DENY_MODULE_PREFIXES = ('v165_truth_audit', 'v165_generate_height', 'v165_validator')
# Truth-bearing file-name stems. Static-scan evidence only: the audit hook cannot
# match a bare name, and the directory prefixes above already cover the real paths.
DENY_NAME_TOKENS = ('new_N_validator_only_truth', 'validator_only_truth')


class TruthGuardInstalled:
    """Book-keeping object returned after the (irreversible) hook is installed."""

    def __init__(self, repo, denied_opens, denied_imports):
        self.repo = str(Path(repo).resolve())
        self.denied_opens = denied_opens
        self.denied_imports = denied_imports

    def report(self):
        return dict(scope='PYTHON_LEVEL_AUDIT_HOOK_NOT_A_KERNEL_SANDBOX',
                    repo=self.repo,
                    deny_dir_prefixes=list(DENY_DIR_PREFIXES),
                    deny_module_prefixes=list(DENY_MODULE_PREFIXES),
                    denied_open_attempts=self.denied_opens,
                    denied_import_attempts=self.denied_imports,
                    guard_installed_once=True, model_calls=0)


def _relative(repo, candidate):
    try:
        p = Path(str(candidate))
    except Exception:
        return None
    try:
        if p.is_absolute():
            rel = p.resolve().relative_to(repo)
        else:
            rel = p
        return rel.as_posix()
    except Exception:
        return None


def install(repo):
    """Install the audit hook exactly once per process."""
    repo = Path(repo).resolve()
    denied_opens = []
    denied_imports = []
    if getattr(sys, '_v165_guard_installed', False):
        return getattr(sys, '_v165_guard_report')

    def hook(event, args):
        if event == 'open':
            rel = _relative(repo, args[0])
            if rel is not None and any(rel.startswith(p) for p in DENY_DIR_PREFIXES):
                denied_opens.append(rel)
                raise RuntimeError('V165_TRUTH_GUARD_OPEN_DENIED:' + rel)
        elif event == 'import':
            name = str(args[0])
            if any(name == p or name.startswith(p + '.') for p in DENY_MODULE_PREFIXES):
                denied_imports.append(name)
                raise RuntimeError('V165_TRUTH_GUARD_IMPORT_DENIED:' + name)

    sys.addaudithook(hook)
    report = TruthGuardInstalled(repo, denied_opens, denied_imports)
    sys._v165_guard_installed = True
    sys._v165_guard_report = report
    return report
