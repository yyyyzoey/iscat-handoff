"""V162-specific regressions: versioned deployment completeness and pinned ancestry.
No optical solver is imported, invoked, or changed.
"""
import hashlib
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'code'))
import v162_deployment as dep
import v162_run as run
import prepare_v162 as prep


def test_reviewed_parent_and_frozen_science_source_are_distinct():
    assert prep.PARENT_V161 == 'dad7b87554959355926d3523169fae7ac30a39f7'
    assert dep.BASE == '71333a9f193d00012972e8fd6c188805c7a6b18e'
    assert run.BASE == dep.BASE


def test_new_version_requires_nested_entry_and_own_results_directory(tmp_path):
    expected = tmp_path / 'tools/v162_bundle/code/v162_run.py'
    assert dep.validate_installed_layout(expected, tmp_path) == expected.parent.parent
    with pytest.raises(ValueError, match='INSTALL_EXACTLY'):
        dep.validate_installed_layout(tmp_path/'tools/v162_run.py', tmp_path)
    assert "(repo/'results/v162').resolve()" in (ROOT/'code/v162_run.py').read_text()


def test_full_bundle_files_present_and_no_legacy_flat_install():
    listed = dep.bundle_files(ROOT)
    assert 'test_inventory.json' in listed
    assert 'run_all.py' in listed
    assert 'run_workstation_tests.py' in listed
    assert 'config/v162_plan.json' in listed
    assert 'tests/test_v162_intake.py' in listed
    assert 'code/v162_run.py' in listed
    assert not (ROOT/'code/v159_run.py').exists()


def test_incomplete_bundle_rejected_before_any_optics(tmp_path):
    (tmp_path/'code').mkdir()
    (tmp_path/'code/v162_run.py').write_text('pass\n')
    with pytest.raises(ValueError, match='INCOMPLETE_EXECUTION_BUNDLE'):
        dep.bundle_files(tmp_path)


def test_frozen_science_problem_and_budget_unchanged():
    cfg = json.loads((ROOT/'config/v162_plan.json').read_text())
    assert cfg['total'] == 500
    assert cfg['phases'] == {'REPAIR_AND_ANCHOR':260,'NONLINEAR_PROBES':120,'FINAL_VERIFY':120}
    assert cfg['new_BEM'] == cfg['new_render'] == cfg['new_exposure'] == 0
    assert cfg['new_fit'] == cfg['new_fixed_D_optimization'] == cfg['new_Jacobian_batch'] == 0
    assert cfg['new_second_focus'] == cfg['new_noise_draw'] == 0
    assert cfg['designs_per_group'] == 17
    assert cfg['svd_rtols'] == [1e-8,1e-10,1e-12]
    assert cfg['probe_groups'] == [[100000,'ANON_02'],[100000,'ANON_03'],[100000,'ANON_04']]


def test_worktree_preparation_must_start_from_reviewed_v159(tmp_path):
    src=(ROOT/'prepare_v162.py').read_text()
    assert "'worktree','add','-b','v162',str(dst),PARENT_V161" in src
    assert 'RESTORED_FROM_RAW_GIT_BLOB' in (ROOT/'code/v162_deployment.py').read_text()
    assert "'code'" in (ROOT/'code/v162_deployment.py').read_text()


def test_complete_prepare_worktree_installs_entire_bundle_synthetically(tmp_path, monkeypatch):
    """Execute the real preparation main against a tiny Git fixture, never F2c.

    The fake commits stand in for immutable reviewed/frozen SHAs. The program is
    exercised through its real package-manifest, worktree, install and commit path.
    """
    import subprocess
    src = tmp_path/'original';src.mkdir()
    def g(*args):
        return subprocess.run(['git','-C',str(src),*args],capture_output=True,text=True,check=True).stdout.strip()
    subprocess.run(['git','init','-q',str(src)],check=True)
    g('config','user.name','Synthetic QA');g('config','user.email','synthetic@example.invalid')
    g('config','core.autocrlf','false')
    (src/'config').mkdir()
    frozen=src/'config/frozen.json'
    frozen.write_bytes(b'{"constant":1}\n')
    g('add','config/frozen.json');g('commit','-qm','frozen')
    frozen_commit=g('rev-parse','HEAD')
    (src/'history.txt').write_text('simulation of reviewed V159 history\n')
    g('add','history.txt');g('commit','-qm','reviewed parent')
    parent_commit=g('rev-parse','HEAD')
    frozen.write_bytes(b'{"constant":1}\r\n') # deliberately nonidentical to frozen commit
    dst=tmp_path/'new_v162'
    monkeypatch.setattr(prep,'BASE',frozen_commit)
    monkeypatch.setattr(prep,'PARENT_V161',parent_commit)
    monkeypatch.setattr(prep,'inspect_inputs',lambda r:dep.inspect_inputs(r,frozen_commit,('config/frozen.json',)))
    monkeypatch.setattr(prep,'restore_new_worktree',lambda r:dep.restore_new_worktree(r,frozen_commit,('config/frozen.json',)))
    monkeypatch.setattr(prep,'verify_locked_inputs',lambda r:dep.verify_locked_inputs(r,frozen_commit))
    # verify_locked_inputs has PREFIXES default for real repo. Restrict to fixture.
    monkeypatch.setattr(prep,'verify_locked_inputs',lambda r: {key:dep.file_identity(r/key) for key, _ in dep.tree_entries(r,frozen_commit,('config/frozen.json',))})
    monkeypatch.setattr(sys,'argv',['prepare_v162.py','--source-repo',str(src),'--worktree',str(dst)])
    prep.main()
    assert frozen.read_bytes()==b'{"constant":1}\r\n'  # original preserved
    assert (dst/'config/frozen.json').read_bytes()==b'{"constant":1}\n'
    assert (dst/'tools/v162_bundle/test_inventory.json').exists()
    assert (dst/'tools/v162_bundle/run_workstation_tests.py').exists()
    assert (dst/'tools/v162_bundle/tests/test_v162_deployment.py').exists()
    assert (dst/'tools/v162_bundle/code/v162_run.py').exists()
    committed=subprocess.run(['git','-C',str(dst),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    assert committed!=parent_commit
    assert subprocess.run(['git','-C',str(dst),'merge-base','--is-ancestor',parent_commit,committed]).returncode==0
    assert (dst/'results/v162/deployment/preparation_receipt.json').exists()
