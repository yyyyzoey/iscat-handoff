"""Targeted finite-profile repair and empirical refinement.
Does not change the F2 forward. Does not accept truth. Does not certify global
optimality, physical provenance, experimental confidence, or reportability.
Old failed attempts remain archived. A point is not 'complete' merely because
an attempt exists or because a budget has not been exhausted.
"""
from __future__ import annotations
import hashlib,json,math,os
from pathlib import Path
import numpy as np
from fit_reference import Objective,solve_start,bounds,BudgetStop
from profile_triage import triage


def digest_array(a):
    a=np.ascontiguousarray(a);return hashlib.sha256((str(a.shape)+'|'+str(a.dtype)).encode()+a.tobytes()).hexdigest()


def safe_dump(path,o):
    if path is None:return
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(o,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8');os.replace(tmp,p)


def legacy_usable(r):
    a=r.get('attempts',[]);loss=r.get('loss');theta=r.get('theta')
    return bool(a and loss is not None and math.isfinite(float(loss)) and float(loss)>=0 and theta is not None and
                all(x.get('success') is True and not x.get('budget_exhausted',False) and x.get('status')!=0 for x in a))


def intervals(rows,cut):
    """Outer grid brackets of empirical-compatible components, NOT confidence CIs."""
    rr=sorted([r for r in rows if r.get('loss') is not None],key=lambda r:r['D'])
    inside=[math.isfinite(float(r['loss'])) and float(r['loss'])<=cut for r in rr]
    ans=[];i=0
    while i<len(rr):
        if not inside[i]:i+=1;continue
        j=i
        while j+1<len(rr) and inside[j+1]:j+=1
        ans.append(dict(first_inside_D=rr[i]['D'],last_inside_D=rr[j]['D'],
                        outer_left_D=rr[max(0,i-1)]['D'],outer_right_D=rr[min(len(rr)-1,j+1)]['D'],
                        touches_lower_support=i==0,touches_upper_support=j==len(rr)-1))
        i=j+1
    return ans


def targeted_profile(model,image,joint,old=None,*,epsilon=None,total_calls=120000,
                     per_point_calls=16000,per_start_calls=2500,max_nfev=500,
                     screening_step=2.5,refinement_step=.5,checkpoint=None,resume=None):
    Y=np.asarray(image,float)
    if Y.ndim!=2 or not np.isfinite(Y).all():raise ValueError('Finite real image required')
    if epsilon is not None and (not math.isfinite(float(epsilon)) or epsilon<0):raise ValueError('Invalid empirical error envelope')
    if old and old.get('model_id')!=model.model_id:raise ValueError('Legacy profile/model mismatch; no silent reuse')
    lo,hi=bounds(model)
    if not (0<refinement_step<=screening_step):raise ValueError('Bad grid steps')
    settings=dict(total_calls=int(total_calls),per_point_calls=int(per_point_calls),per_start_calls=int(per_start_calls),max_nfev=int(max_nfev),screening_step=float(screening_step),refinement_step=float(refinement_step),epsilon=epsilon)
    binding=dict(model_id=model.model_id,observation_sha256=digest_array(Y),
                 estimator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),settings=settings)
    binding_id=hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest()
    points={};calls=0;inherited=0;history=[]
    if resume is not None:
        if resume.get('binding_id')!=binding_id:raise ValueError('Resume identity/settings mismatch')
        points={float(r['D']):r for r in resume['rows']};calls=int(resume['canonical_calls_new']);history=resume.get('history',[])
        inherited=int(resume.get('inherited_complete_points',0))
    elif old:
        for r in old.get('rows',[]):
            p=dict(r);p['D']=float(p['D'])
            if not lo[0]<=p['D']<=hi[0]:raise ValueError('Legacy D outside declared domain')
            if p.get('theta') is not None and abs(float(p['theta'][0])-p['D'])>1e-8:raise ValueError('Legacy witness changes fixed D')
            p['source']='V131_LEGACY';p['point_search_complete']=legacy_usable(p)
            if p['D'] in points:raise ValueError('Duplicate legacy D')
            points[p['D']]=p;inherited+=int(p['point_search_complete'])
    # Every reused profile is verified by caller's input-file identity and by an
    # actual same-image joint witness. No equality to ground-truth D is needed.
    witness=float(np.linalg.norm(model.forward(joint['theta']).score_C-Y));calls+=1
    if abs(witness-float(joint['loss']))>max(1e-12,1e-7*max(witness,float(joint['loss']))):
        raise ValueError('Legacy joint residual does not replay')
    for r in list(points.values()):
        if r.get('theta') is not None and r.get('loss') is not None:
            if calls>=total_calls:break
            actual=float(np.linalg.norm(model.forward(r['theta']).score_C-Y));calls+=1
            if abs(actual-float(r['loss']))>max(1e-12,1e-7*max(actual,float(r['loss']))):
                raise ValueError('Legacy profile witness does not replay; input/model identity investigation required')
    required=np.unique(np.r_[np.arange(lo[0],hi[0]+1e-9,screening_step),model.Ds,hi[0],float(joint['theta'][0])])
    target=set(map(float,required));adaptive_done=False

    def snapshot():
        rr=sorted(points.values(),key=lambda r:r['D']);finite=[r for r in rr if r.get('loss') is not None and math.isfinite(float(r['loss']))]
        best=min(finite,key=lambda r:r['loss']) if finite else None
        cut=(best['loss']+float(epsilon)) if best and epsilon is not None else None
        complete=all(d in points and points[d].get('point_search_complete',False) for d in target)
        return dict(schema='iscat132.profile.1',binding_id=binding_id,binding=binding,model_id=model.model_id,rows=rr,required_D=sorted(target),
                    canonical_calls_new=calls,inherited_complete_points=inherited,coarse_and_scheduled_search_complete=complete,
                    adaptive_refinement_complete=adaptive_done,empirical_norm_cutoff=cut,
                    compatible_components=intervals(rr,cut) if cut is not None else [],best_profile=best,
                    update_joint_required=bool(best and best['loss']<float(joint['loss'])-max(1e-12,1e-7*float(joint['loss']))),
                    reportable_D=None,physical_qualification='NOT_SET_BY_PROFILE',history=history,
                    scope='PRESCRIBED_FINITE_SEARCH_AND_EMPIRICAL_COMPATIBILITY_NOT_GLOBAL_PROOF')

    def point(D):
        nonlocal calls
        if calls>=total_calls:return False
        oldp=points.get(D);best=None
        if oldp and oldp.get('loss') is not None:best=dict(theta=oldp['theta'],loss=float(oldp['loss']))
        valid=[p for p in points.values() if p.get('theta') is not None and p.get('loss') is not None]
        nearest=min(valid,key=lambda p:abs(p['D']-D)) if valid else None
        seeds=[[D,float(h),*joint['theta'][2:]] for h in np.linspace(lo[1],hi[1],4)]
        seeds += [[D,joint['theta'][1],*joint['theta'][2:]]]
        if nearest:seeds.append([D,*nearest['theta'][1:]])
        unique=[]
        for s in seeds:
            if not any(np.max(abs(np.asarray(s)-np.asarray(z)))<1e-8 for z in unique):unique.append(s)
        obj=Objective(model,Y,min(per_point_calls,total_calls-calls));records=[]
        for s in unique:
            if obj.calls>=obj.limit:break
            rec=solve_start(obj,s,[1,2,3],per_start_calls=min(per_start_calls,obj.limit-obj.calls),max_nfev=max_nfev)
            rec['x0']=list(map(float,s));records.append(rec)
            if rec.get('loss') is not None and (best is None or rec['loss']<best['loss']):best=dict(theta=rec['theta'],loss=rec['loss'])
        calls+=obj.calls
        if obj.best_by_D.get(D) and (best is None or obj.best_by_D[D]['loss']<best['loss']):best=obj.best_by_D[D]
        complete=(len(records)==len(unique) and all(r['success'] and not r['budget_exhausted'] and r['status']!=0 for r in records))
        prior_status={'source':oldp.get('source'),'point_search_complete':oldp.get('point_search_complete'),'loss':oldp.get('loss')} if oldp else None
        history.append(dict(D=D,old=prior_status,new_calls=obj.calls,point_search_complete=complete))
        points[D]=dict(D=D,theta=best['theta'] if best else None,loss=best['loss'] if best else None,
                       source='V132_TARGETED_MINIMIZATIONS',point_search_complete=complete,
                       attempts=records,legacy_attempts=oldp.get('attempts',[]) if oldp else [],required_starts=unique)
        safe_dump(checkpoint,snapshot());return complete

    # Repair legacy failures / add coarse midpoints; only absent or incomplete D
    # are revisited. Successful legacy D points are retained unchanged.
    for d in sorted(target):
        if points.get(d,{}).get('point_search_complete'):continue
        point(d)
        if calls>=total_calls:break
    if epsilon is not None:
        for _round in range(8):
            if not all(points.get(d,{}).get('point_search_complete') for d in target):break
            st=snapshot();cut=st['empirical_norm_cutoff'];rr=st['rows'];new=[]
            # Subdivide around compatibility crossings, low-loss regions and all
            # sampled local minima. Finite gridding is expressly not a proof that
            # arbitrarily narrow unvisited minima cannot exist.
            minima={i for i in range(1,len(rr)-1) if rr[i]['loss']<=min(rr[i-1]['loss'],rr[i+1]['loss'])}
            for i,(a,b) in enumerate(zip(rr[:-1],rr[1:])):
                if b['D']-a['D']<=refinement_step+1e-9:continue
                if a['loss']<=cut or b['loss']<=cut or i in minima or i+1 in minima:
                    new.append(float((a['D']+b['D'])/2))
            if not new:adaptive_done=True;break
            target.update(new)
            for d in new:
                if not points.get(d,{}).get('point_search_complete'):point(d)
                if calls>=total_calls:break
            if calls>=total_calls:break
    result=snapshot();safe_dump(checkpoint,result);return result
