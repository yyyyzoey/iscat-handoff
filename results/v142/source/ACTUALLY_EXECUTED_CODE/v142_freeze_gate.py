#!/usr/bin/env python3
"""Freeze pre-registered candidate model before the first new N BEM attempt.
This is a *necessary* software prerequisite; source/MAT provenance and
physical qualification must still be recorded separately by Codex.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    a=argparse.ArgumentParser();a.add_argument('--repo',required=True);a.add_argument('--config',required=True)
    a.add_argument('--stability',required=True);a.add_argument('--validator-summary',required=True)
    a.add_argument('--dev-fit-summary',required=True);a.add_argument('--out',required=True);z=a.parse_args()
    repo=Path(z.repo).resolve();cfg=json.loads(Path(z.config).read_text());st=json.loads(Path(z.stability).read_text());v=json.loads(Path(z.validator_summary).read_text());df=json.loads(Path(z.dev_fit_summary).read_text())
    if not st.get('software_stability_pass') or not v.get('candidate_selection_numerical_proposal_pass'):
        raise ValueError('MODEL_PRE_FREEZE_STABILITY_OR_PHYSICAL_DEV_SELECTION_FAILED')
    if st.get('model_id')!=v.get('model_id') or df.get('new_model_id')!=st['model_id'] or df.get('dev_cases')!=6:
        raise ValueError('MODEL_IDS_OR_DEV_CASE_COUNT_DISAGREE')
    # Strict: do not freeze a model with dirty tracked science source.
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    git_status=subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True)
    if git_status.strip():raise ValueError('TRACKED_WORKTREE_DIRTY__COMMIT_SOURCE_BEFORE_MODEL_FREEZE')
    package_tools=['v142_model.py','v142_field_reference.py','v142_gate.py','v142_dev_fit.py','v142_profile_dev.py','v142_validator_only_forward.py']
    installed=repo/'tools'
    hashes={p:sha(installed/p) for p in package_tools if (installed/p).is_file()}
    if set(hashes)!=set(package_tools):raise ValueError('MODEL_ESTIMATOR_QUALITY_SOURCES_NOT_INSTALLED_IN_REPO')
    frozen=dict(schema='iscat142.model_freeze.1',model_id=st['model_id'],parent_model_id=st['old_model_id'],
        freeze_git_commit=head,source_code_sha256=hashes,source_config_sha256=sha(z.config),
        stability_sha256=sha(z.stability),dev_selection_sha256=sha(z.validator_summary),
        dev_fit_sha256=sha(z.dev_fit_summary),N_validator_spec_sha256=sha(repo/cfg['new_blind_N_validator_spec_file']),
        blind_N_not_yet_generated='CODEx_MUST_VERIFY_BEFORE_N',
        freeze_scope='NUMERIC_DEVELOPMENT_FREEZE_NOT_INDEPENDENT_SCIENCE_PASS',
        all_future_N_method_changes_downgrade_N_to_opened_dev=True)
    out=Path(z.out);out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise ValueError('FREEZE_ALREADY_EXISTS__DO_NOT_OVERWRITE')
    out.write_text(json.dumps(frozen,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('FREEZE_WRITTEN_ONLY_SOFTWARE_PREREQUISITES_SATISFIED',head,st['model_id'])
if __name__=='__main__':main()
