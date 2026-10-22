"""Zero-BEM validator diagnostics on opened H/J/K/L data.
Truth is permitted here ONLY to evaluate error and oracle controls, never in formal fits.
No reportable diameter or physical qualification is issued by this program.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import h5py,numpy as np
from truth_and_score import truth_from_sources,sha256,write_csv
from load_field_library import load_library,complex_array
from field_forward_reference import sample_complex,pixel_mean
from fit_reference import Objective,solve_start


def optical(cfg):
    c=cfg['conditional_model']
    return dict(pixel_nm=c['object_pixel_nm'],q=c['q'],camera_n=c['camera_n'],score_n=c['score_n'],xy_limit_nm=c['xy_limit_nm'],min_gap_nm=c['min_surface_gap_nm'],expected_node_metadata=dict(n_particle=complex(*c['particle_n_re_im']),NA=c['NA'],object_pixel_nm=c['object_pixel_nm']))


def array_sha(a):
    a=np.ascontiguousarray(a)
    return hashlib.sha256((str(a.shape)+'|'+str(a.dtype)).encode()+a.tobytes()).hexdigest()


def signed_image(group, model, dataset='at_offset/C'):
    z=group[dataset][()]
    if np.iscomplexobj(z):raise ValueError('Static contrast must be real')
    z=np.asarray(z,float)
    if z.shape==(model.n,model.n):
        j=(model.n-model.s)//2;z=z[j:j+model.s,j:j+model.s]
    if z.shape!=(model.s,model.s) or not np.isfinite(z).all():raise ValueError('Invalid image')
    return z


def local_jacobian(model,theta, factor=1.):
    p=np.asarray(theta,float);lo=np.array([model.Ds[0],model.Hs[0],-model.xy_limit,-model.xy_limit]);hi=np.array([model.Ds[-1],model.Hs[-1],model.xy_limit,model.xy_limit])
    cols=[]
    for j,step in enumerate(np.array([.02,.02,.05,.05])*factor):
        a=p.copy();b=p.copy();a[j]=max(lo[j],p[j]-step);b[j]=min(hi[j],p[j]+step)
        if b[j]<=a[j]:raise ValueError('Invalid derivative domain')
        cols.append(((model.forward(b).score_C-model.forward(a).score_C)/(b[j]-a[j])).ravel())
    return np.stack(cols,axis=1)


def project_size_direction(J, residual):
    # Numerical diagnosis only. Rank choices must be reported and varied.
    outputs=[]
    A=J[:,1:];norms=np.linalg.norm(A,axis=0)
    active=norms>0
    B=A[:,active]/norms[active] if np.any(active) else np.empty((J.shape[0],0))
    U,s,_=np.linalg.svd(B,full_matrices=False)
    for cutoff in (1e-6,1e-8,1e-10):
        rank=int(np.sum(s>cutoff*s[0])) if len(s) and s[0]>0 else 0
        basis=U[:,:rank];d=J[:,0];perp=d-basis@(basis.T@d)
        v=residual.ravel()-basis@(basis.T@residual.ravel())
        den=float(perp@perp); dnorm=float(np.linalg.norm(d))
        reliable=bool(dnorm>0 and np.sqrt(den)>1e-8*dnorm)
        outputs.append(dict(rank_cutoff=cutoff,nuisance_rank=rank,nuisance_column_norms=norms.tolist(),singular_values=s.tolist(),diameter_direction_norm=dnorm,projected_D_norm=float(np.sqrt(den)),q_fraction=float(np.sqrt(den)/dnorm) if dnorm else None,
                            predicted_delta_D_local_nm=float(perp@v/den) if reliable else None,
                            scope='LOCAL_LINEARIZATION_NOT_ACCURACY_OR_CRLB'))
    return outputs


def oracle_control(model,Y,true,free):
    obj=Objective(model,Y,6000);records=[]
    for D0 in (50.,100.,160.):
        p=np.asarray(true,float).copy();p[0]=D0
        if 1 in free:p[1]=450.
        records.append(solve_start(obj,p,free,per_start_calls=1800,max_nfev=300))
    return dict(best_witness=obj.best,starts=records,calls=obj.calls,role='ORACLE_DIAGNOSTIC_NOT_FORMAL_ESTIMATOR')


def _direct_field_shift_checked(group,model,theta):
    if 'wide' not in group:return dict(status='MISSING_WIDE',qualified=False)
    w=group['wide']
    missing=[k for k in ('Eref','Esca','fine_x_nm','fine_y_nm') if k not in w]
    if missing:
        return dict(status='MISSING_WIDE_METADATA',qualified=False,missing=missing,
                    action='Recover coordinates from the SAME original render; do not guess or borrow training axes')
    er=complex_array(w['Eref']);es=complex_array(w['Esca'])
    fx=np.asarray(w['fine_x_nm'][()],float);fy=np.asarray(w['fine_y_nm'][()],float)
    if er.shape!=(len(fx),len(fy),3) or es.shape!=er.shape:raise ValueError('Bad raw wide field axes; no guessed transpose')
    # Direct holdout arrays already use the audited camera coordinate convention.
    ref=sample_complex(er,fx,fy,model.query,model.query)
    sc=sample_complex(es,fx,fy,model.query-theta[2],model.query-theta[3])
    bg=pixel_mean(np.sum(abs(ref)**2,axis=-1),model.q)
    if np.any(bg<=0) or not np.isfinite(bg).all():raise ValueError('Invalid reference')
    C=(pixel_mean(np.sum(abs(ref+sc)**2,axis=-1),model.q)-bg)/bg
    Y=signed_image(group,model);a=(model.n-model.s)//2;pred=C[a:a+model.s,a:a+model.s]
    e=float(np.linalg.norm(pred-Y));signal=float(np.linalg.norm(Y))
    return dict(status='COMPUTED',abs_L2=e,max_abs=float(np.max(abs(pred-Y))),signal_L2=signal,rel_L2=e/signal if signal>0 else None,
                scope='SAME_DIRECT_FIELD_SHIFT_COMPARISON_NOT_SOLVE_GEOMETRY_CERTIFICATE')


def direct_field_shift(group,model,theta):
    """Optional source-field test: failure is explicit, never destroys valid image diagnostics."""
    try:
        return _direct_field_shift_checked(group,model,theta)
    except Exception as exc:
        return dict(status='DIRECT_FIELD_COMPARISON_FAILED',qualified=False,
                    error=f'{type(exc).__name__}: {exc}',
                    scope='ONLY_THIS_CHECK_BLOCKED; not a pass and not a substitute for source repair')


def run(repo,cfg,out,sets=None,oracle=False):
    repo=Path(repo).resolve();out=Path(out);out.mkdir(parents=True,exist_ok=True)
    lib=repo/cfg['inputs']['train'];actualsha=sha256(lib)
    if actualsha!=cfg['inheritance']['expected_library_sha256']:raise ValueError('Library bytes changed: dataset/attrs diff required before inheritance')
    model,report=load_library(lib,kind='F2',optical=optical(cfg))
    if model.model_id!=cfg['inheritance']['expected_model_id']:raise ValueError('Inherited canonical model identity mismatch')
    truth,src=truth_from_sources(repo,cfg['truth_sources'])
    candidates=list(csv.DictReader((repo/cfg['inheritance']['v131_out']/'old_per_particle_candidates.csv').open(encoding='utf-8-sig')))
    index={(r['data_set'],r['case']):r for r in candidates}
    rows=[];failures=[]
    for ds in (sets or cfg['diagnostics_v132']['sets']):
        hp=repo/cfg['offline_batch']['sets'][ds]
        oldid=json.loads((repo/cfg['inheritance']['v131_out']/'observation_identity'/f'{ds}.json').read_text(encoding='utf-8-sig'))
        if sha256(hp)!=oldid['sha256']:raise ValueError(f'{ds}: observation file changed; do not resume prior candidates/profiles')
        with h5py.File(hp,'r') as hf:
            for name in sorted(hf):
                try:
                    t=truth[(ds,name)];p=np.array([t[k] for k in ('D_nm','h_nm','x_nm','y_nm')]);Y=signed_image(hf[name],model,cfg['inputs']['observation_dataset']);F=model.forward(p).score_C
                    old=index[(ds,name)];pfit=[float(old[k]) for k in ('candidate_D','h','x','y')];Ffit=model.forward(pfit).score_C
                    loss=float(np.linalg.norm(Ffit-Y));prior=float(old['loss'])
                    if abs(loss-prior)>max(1e-12,1e-7*prior):raise ValueError('Current model/observation does not reproduce published candidate residual')
                    J=local_jacobian(model,p);Jh=local_jacobian(model,p,.5);J2=local_jacobian(model,p,2.)
                    e=Y-F;n=float(np.linalg.norm(Y));L=float(np.linalg.norm(e))
                    detail=dict(case=name,data_set=ds,truth=t,theta_candidate=pfit,observation_array_sha256=array_sha(Y),model_id=model.model_id,
                                source_checks='H5 identity verified; original solve geometry still separate',
                                model_at_truth_error_L2=L,candidate_residual_L2=loss,signal_L2=n,relative_model_error=L/n if n>0 else None,
                                local_projection=project_size_direction(J,e),
                                derivative_half_abs_norms=np.linalg.norm(J-Jh,axis=0).tolist(),derivative_double_abs_norms=np.linalg.norm(J-J2,axis=0).tolist(),
                                same_direct_field_shift=direct_field_shift(hf[name],model,p))
                    if oracle:
                        detail['oracle_D']=oracle_control(model,Y,p,[0]);detail['oracle_Dh']=oracle_control(model,Y,p,[0,1])
                    (out/f'{ds}_{name}.json').write_text(json.dumps(detail,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
                    np.savez_compressed(out/f'{ds}_{name}.npz',Y=Y,F_at_recorded_truth=F,F_candidate=Ffit,theta_validator=p,theta_candidate=pfit,J=J,J_half=Jh,J_double=J2)
                    rows.append(dict(data_set=ds,case=name,D_recorded=t['D_nm'],h_recorded=t['h_nm'],candidate_D=pfit[0],err_D=pfit[0]-t['D_nm'],model_at_truth_error_L2=L,candidate_residual_L2=loss,signal_L2=n,
                                     candidate_worse_than_legal_truth_point=bool(loss>L+max(1e-12,1e-7*L)),role='OPENED_DEVELOPMENT_DIAGNOSTIC'))
                except Exception as exc:
                    failures.append(dict(data_set=ds,case=name,error=f'{type(exc).__name__}: {exc}'))
    if rows:write_csv(out/'error_separation.csv',rows)
    (out/'diagnostic_status.json').write_text(json.dumps(dict(computed=len(rows),failures=failures,model_id=model.model_id,physical_qualified=False,reportable_certified=False),indent=2)+'\n')
    # A diagnostic empirical envelope only: direct reference vs model, not a universal bound.
    if rows and not failures:
        (out/'development_envelope.json').write_text(json.dumps(dict(model_id=model.model_id,epsilon_L2=max(r['model_at_truth_error_L2'] for r in rows),construction='maximum recorded-truth error over all opened development observations',scope='EMPIRICAL_DEVELOPMENT_ONLY_NOT_UNIFORM_PHYSICS_BOUND',numerical_allowance_included=False),indent=2)+'\n')
    return not failures


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--config',required=True);ap.add_argument('--out',required=True);ap.add_argument('--sets',nargs='*');ap.add_argument('--oracle',action='store_true');a=ap.parse_args()
    cfg=json.loads(Path(a.config).read_text(encoding='utf-8'));return 0 if run(a.repo,cfg,a.out,a.sets,a.oracle) else 2
if __name__=='__main__':raise SystemExit(main())
