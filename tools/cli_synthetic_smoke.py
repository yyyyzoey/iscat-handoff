"""Manual CLI wiring smoke: synthetic fields, NOT electromagnetic validation."""
from pathlib import Path
import sys,json,tempfile,subprocess,hashlib
import h5py,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from field_forward_reference import FieldForward,pixel_mean
from load_field_library import load_library
from v133_recover_M import optical

def run():
    with tempfile.TemporaryDirectory() as td:
        repo=Path(td);lp=repo/'library.h5';op=repo/'images.h5'
        D=np.array([30.,70.,130.,200.]);H=np.array([350.,400.,475.,550.]);x=np.linspace(-3,3,13)
        X,Y=np.meshgrid(x,x,indexing='ij');ers=np.zeros((4,4,13,13,3),complex);ers[...,0]=1;ess=np.zeros_like(ers)
        for i,d in enumerate(D):
            for j,h in enumerate(H):
                ess[i,j,:,:,0]=.01*(d/100.)**2*np.exp(-(X**2+Y**2)/(1.2+(h-350)/300))+.00003*(h-450)*X*np.exp(-(X**2+Y**2)/3)
        m=FieldForward(D,H,x,x,ers,ess,kind='F2',pixel_nm=1,q=1,camera_n=5,score_n=3,xy_limit_nm=.5,min_gap_nm=0)
        with h5py.File(lp,'w') as f:
            for i,d in enumerate(D):
                for j,h in enumerate(H):
                    g=f.create_group(f'D{d:g}_h{h:g}');e=m.fields(d,h)[1];ref=m.ref
                    # Standard image consists of query samples at integer x/y.
                    qidx=[2,4,6,8,10];er=ref[np.ix_(qidx,qidx)];es=e[np.ix_(qidx,qidx)]
                    c=(np.sum(abs(er+es)**2,axis=-1)-np.sum(abs(er)**2,axis=-1))/np.sum(abs(er)**2,axis=-1)
                    for k,a in [('Eref',er),('Esca',es),('C',c)]:g.create_dataset(k,data=a)
                    w=g.create_group('wide')
                    for k,a in [('Eref',ref),('Esca',e),('fine_x_nm',x),('fine_y_nm',x)]:w.create_dataset(k,data=a)
                    g.attrs.update(D_nm=d,h_nm=h,n_particle=1.38,NA=.8,object_pixel_nm=1,mesh=-1)
        cfg=json.loads((ROOT/'config/v133_science_config.json').read_text());cfg['inputs']['train']='library.h5'
        cfg['conditional_model'].update(object_pixel_nm=1,q=1,camera_n=5,score_n=3,xy_limit_nm=.5,min_surface_gap_nm=0)
        model,r=load_library(lp,kind='F2',optical=optical(cfg))
        cfg['model_lock'].update(library_sha256=r['library_sha256'],model_id=model.model_id,sentinel_theta_nm=[[50,400,0,0],[90,460,.1,-.1]])
        cfg['M_observations'].update(path='images.h5',cases=['T01']);cfg['reuse']['public_bank']='not_present.h5'
        cfg['template_bank'].update(offsets_nm=[[0,0],[.25,-.25],[-.25,.25]],separation_nm=[15,25,.1,.1])
        with h5py.File(op,'w') as f:f.create_dataset('T01/C',data=model.forward([83.7,430,.12,-.14]).C)
        cp=repo/'config.json';cp.write_text(json.dumps(cfg));out=repo/'out'
        cmd=[sys.executable,str(ROOT/'tools/v133_recover_M.py'),'--repo',str(repo),'--config',str(cp),'--out',str(out)]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=35)
        if p.returncode!=3:raise RuntimeError(p.stdout+p.stderr+(out/'component_status.json').read_text())
        f=json.loads((out/'fits/M_T01.json').read_text());assert f['reportable_D'] is None
        q=subprocess.run(cmd+['--resume'],capture_output=True,text=True,timeout=35);assert q.returncode==3,q.stdout+q.stderr
        return dict(scope='SYNTHETIC_HDF5_CLI_WIRING_ONLY',first_exit=p.returncode,resume_exit=q.returncode,candidate_D=f['candidate_D'],reportable_D=f['reportable_D'],stdout=p.stdout)
if __name__=='__main__':
    r=run();(ROOT/'evidence/cli_synthetic_smoke.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
