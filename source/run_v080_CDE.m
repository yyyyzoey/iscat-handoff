function run_v080_CDE(outRoot, v076Root)
if nargin<2||isempty(v076Root), v076Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
if nargin<1, outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v080_return'; end
tabDir=fullfile(outRoot,'tables');
% E: 276 pairs
R=load(fullfile(v076Root,'numeric','v076_dynamic_center_corrected.mat'));
fn=fieldnames(R); states=struct();
for i=1:numel(fn)
  f=R.(fn{i}); if ~isfield(f,'D'), continue; end
  key=matlab.lang.makeValidName(fn{i});
  states.(key)=struct('C400',f.C400,'D',f.D,'zf',f.zf,'amp',f.amp,'ttype',f.ttype,'name',fn{i});
end
sn=fieldnames(states); nS=numel(sn);
idf=fopen(fullfile(tabDir,'v080_identifiability276_audit.csv'),'w');
fprintf(idf,'pair_id,state_i,state_j,D_i,zf_i,a_i,type_i,D_j,zf_j,a_j,type_j,changed,symC,symA,note\n');
pid=0;
for i=1:nS
  for j=i+1:nS
    si=states.(sn{i}); sj=states.(sn{j});
    chg='';
    if si.D~=sj.D, chg=[chg '+D']; end
    if si.zf~=sj.zf, chg=[chg '+zf']; end
    if si.amp~=sj.amp, chg=[chg '+a']; end
    if ~strcmp(si.ttype,sj.ttype), chg=[chg '+type']; end
    nC=norm(double(si.C400(:))-double(sj.C400(:)));
    dC=(norm(double(si.C400(:)))+norm(double(sj.C400(:))))/2;
    symC=nC/max(dC,realmin);
    ai=abs(si.C400(:)); aj=abs(sj.C400(:));
    nA=norm(ai-aj); dA=(norm(ai)+norm(aj))/2;
    symA=nA/max(dA,realmin);
    pid=pid+1;
    fprintf(idf,'%d,%s,%s,%d,%g,%g,%s,%d,%g,%g,%s,%s,%.17g,%.17g,%s\n', ...
      pid,sn{i},sn{j},si.D,si.zf,si.amp,si.ttype,sj.D,sj.zf,sj.amp,sj.ttype,chg,symC,symA,'PRESCRIBED trajectories');
  end
end
fclose(idf);
fprintf('[080E] %d pairs\n',pid);
% D: exposure convergence (analytic sinc reference + 5-node existing data)
ef=fopen(fullfile(tabDir,'v080_exposure16_incremental.csv'),'w');
fprintf(ef,'case,type,a_nm,tau_s,quadrature,absC400_tau0,sinc_ref_400Hz,status,note\n');
for tt=[200 400]
  for aa=[5 20]
    for tau=[1e-4 2e-4]
      sr=abs(sin(pi*400*tau)/(pi*400*tau));
      fprintf(ef,'D60_zf450_M%d_a%d,M%d,%d,%g,5_node_left_from_v078,NOT_EXECUTED,%.6f,NOT_EXECUTED_RESOURCE_LIMIT,higher-order quadrature not executed; analytic sinc reference only\n',tt,aa,tt,aa,tau,sr);
    end
  end
end
fclose(ef);
fprintf('[080D] exposure convergence table written (analytic references only)\n');
end
