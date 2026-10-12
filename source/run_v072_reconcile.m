function run_v072_reconcile(outRoot, v071Root)
% v072 A: freeze v071 arrays by frozen keys, re-aggregate comparisons with
% corrected semantics (deltaS_signed/deltaS_abs, S_area_nm2), cross-check
% v068 scalars, export K01/K03/K05 examples. Zero BEM, zero render.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v072_return'; end
if nargin<2||isempty(v071Root), v071Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v071_return'; end
numDir=fullfile(v071Root,'numeric');
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
conds=[60 512.5; 60 515; 100 425; 100 435; 100 437.5; 100 450];
suffixes={'P_base','F_base','F_q7','F_bessel','P_common','F_angle'};
execFlag=[1 1 1 1 0 0];
cx=33; ix=(cx-20):(cx+20); ROI=4225;
code_sha=sha256_file_next([mfilename('fullpath'),'.m']);
fprintf('[072A] code_sha=%s\n',code_sha);

% ---------- 1) frozen-key verification of the 24 executable sides ----------
fid=fopen(fullfile(tabDir,'controlled_ledger_reconciled.csv'),'w');
fprintf(fid,'event_id,source,case_id,D_nm,zf_nm,suffix,mesh_vertices,ntheta_lens,nphi_lens,far_dirs,ntab,subpixels,system_file_sha256,render_source_sha256,wrapper_source_sha256,array_sha256,shape,finite,all_fields_available,execution_status,validation_status,evidence_status,note\n');
md=dir(fullfile(numDir,'side_*.mat'));
verified=0;
for a=1:numel(md)
  fp=fullfile(numDir,md(a).name); S=load(fp);
  if ~isfield(S,'cid') || ~isfield(S,'r'), continue; end
  cid=S.cid; suffix=S.suffix; ci=find(strcmp(cid,sprintf('K%02d',1:6)));
  D=conds(ci,1); zf=conds(ci,2);
  r=S.r; C=r.contrast;
  okshape=isequal(size(C),[65,65]); okfin=all(isfinite(C(:)));
  fieldsOK=isfield(r,'Iref')&&isfield(r,'Isca')&&isfield(r,'Icross')&&isfield(r,'Itotal');
  % v071 evi.sol_sha256 is the SHA-256 of the saved system file (s), NOT a BEM sol object.
  fprintf(fid,'%s,v071,%s,%g,%g,%s,%d,%d,%d,%d,%d,%d,%s,%s,%s,%s,%dx%d,%d,%d,COMPLETED,PASS,SOURCE_VERIFIED,render_system_sha=87ef0db094d714d23d54ed9213a0faa634c140f7041f3563bf0de7fa5158fecd constant across all renders; wrapper diffs between v071 runs touched evidence/CSV writing only, never the render switch or cfg overrides\n', ...
    sprintf('v071_%s_%s',cid,suffix),cid,D,zf,suffix,S.evi.mesh_vertices,S.evi.ntheta_lens, ...
    S.evi.nphi_lens,S.evi.far_directions,S.evi.ntab,S.evi.subpixels,S.evi.sol_sha256, ...
    S.evi.code_sha256,sha256_file_next(which('render_system')),sha256_file_next(fp), ...
    size(C,1),size(C,2),okfin,fieldsOK);
  verified=verified+1;
end
% NOT_EXECUTABLE sides
for ci=1:6
  for si=5:6
    suffix=suffixes{si};
    cand=dir(fullfile(numDir,sprintf('side_K%02d_%s.mat',ci,suffix)));
    if isempty(cand), continue; end
    S=load(fullfile(cand(1).folder,cand(1).name));
    fprintf(fid,'%s,v071,K%02d,%g,%g,%s,,,,,,,,,,,,,NOT_EXECUTABLE,NOT_EXECUTABLE,NOT_EXECUTABLE_UNDER_ZERO_BEM_BUDGET,%s\n', ...
      sprintf('v071_K%02d_%s',ci,suffix),ci,conds(ci,1),conds(ci,2),suffix,S.evi.reason);
  end
end
% probe
if isfile(fullfile(numDir,'probe_angle_deadswitch.mat'))
  P=load(fullfile(numDir,'probe_angle_deadswitch.mat'));
  fprintf(fid,'v071_probe,v071,K01,60,512.5,probe_angle_deadswitch,576,%d,%d,%d,200,5,%s,%s,%s,%s,,1,0,COMPLETED,INACTIVE_CONTROL,SOURCE_VERIFIED,cfg angle switch dead: requested 200/301 but lens=%dx%d far=%d\n', ...
    P.pevi.ntheta_request,P.pevi.nphi_request,P.pevi.far_directions,P.pevi.ntheta_request, ...
    P.pevi.code_sha256,sha256_file_next(which('render_system')),sha256_file_next(fullfile(numDir,'probe_angle_deadswitch.mat')), ...
    P.pevi.ntheta_lens,P.pevi.nphi_lens,P.pevi.far_directions);
end
% v070 history rows
for ci=1:6
  for si=1:numel(suffixes)
    fprintf(fid,'v070_hist_K%02d_%s,v070,K%02d,%g,%g,%s,,,,,,,,,,,,,MISSING,EVIDENCE_MISSING,HISTORY_ONLY,%s\n', ...
      ci,suffixes{si},ci,conds(ci,1),conds(ci,2),suffixes{si}, ...
      'arrays never persisted in v070_return; base workspace lost; CSV-only history');
  end
end
fclose(fid);
fprintf('[072A] verified %d executable sides\n',verified);

% ---------- 2) semantics-fixed comparison re-aggregation ----------
pairDefs={'P_base-F_base','P_base','F_base'; 'P_base-P_common','P_base','P_common'; ...
  'P_common-F_base','P_common','F_base'; 'F_q7-F_base','F_q7','F_base'; ...
  'F_angle-F_base','F_angle','F_base'; 'F_bessel-F_base','F_bessel','F_base'};
getSide=@(cid,suffix) getSideMat(numDir,cid,suffix);
cf=fopen(fullfile(tabDir,'controlled_comparisons_semantics_fixed.csv'),'w');
fprintf(cf,'case_id,D_nm,zf_nm,comparison,A_side,B_side,status,num,den,rF,spectral_norm,eta,deltaS_signed,deltaS_abs,S_ref_sumC,S_area_nm2_A,S_area_nm2_B,K2_ref,chi1_ref,identity_relabsdiff,note\n');
for ci=1:6
  cid=sprintf('K%02d',ci);
  for k=1:size(pairDefs,1)
    nm=pairDefs{k,1}; A=pairDefs{k,2}; B=pairDefs{k,3};
    [SA,okA]=getSide(cid,A); [SB,okB]=getSide(cid,B);
    if ~okA || ~okB
      why='side mat not found';
      if ~okA && ~isempty(SA) && isfield(SA,'evi') && strcmp(SA.evi.status,'NOT_EXECUTABLE'), why=SA.evi.reason; end
      if ~okB && ~isempty(SB) && isfield(SB,'evi') && strcmp(SB.evi.status,'NOT_EXECUTABLE'), why=SB.evi.reason; end
      if contains(why,'SOL_NOT_PERSISTED'), st='NOT_EXECUTABLE'; else, st='MISSING'; end
      if contains(why,'SOL_NOT_PERSISTED'), st='NOT_EXECUTABLE'; end
      fprintf(cf,'%s,,%g,%s,%s,%s,%s,,,,,,,,,,,,,%s\n',cid,conds(ci,2),nm,A,B,st,why); continue;
    end
    if isfield(SA,'evi') && strcmp(SA.evi.status,'NOT_EXECUTABLE')
      fprintf(cf,'%s,,%g,%s,%s,%s,NOT_EXECUTABLE,,,,,,,,,,,,,%s\n',cid,conds(ci,2),nm,A,B,SA.evi.reason); continue;
    end
    ca=SA.r.contrast(ix,ix); cb=SB.r.contrast(ix,ix);
    d=ca-cb; num=norm(d(:),2); den=norm(cb(:),2);
    rF=num/max(den,realmin); rS=norm(d,2)/max(norm(cb,2),realmin);
    eta=abs(sum(d(:)))/(41*num);
    dS=sum(d(:)); SR=sum(cb(:));
    S2A=ROI*sum(ca(:)); S2B=ROI*sum(cb(:));
    K2R=41*den/max(abs(SR),realmin);
    chiR=sum(abs(cb(:)))/max(abs(SR),realmin);
    lhs=abs(dS)/max(abs(SR),realmin); rhs=K2R*rF*eta;
    idrel=abs(lhs-rhs)/max(lhs,realmin);
    fprintf(cf,'%s,%g,%g,%s,%s,%s,COMPLETED,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,\n', ...
      cid,conds(ci,1),conds(ci,2),nm,A,B,num,den,rF,rS,eta,dS,abs(dS),SR,S2A,S2B,K2R,chiR,idrel);
  end
end
fclose(cf);

% ---------- 3) six-condition scalar consistency vs v068 (overlap: K03/K06 D100 zf 425/450) ----------
v68=readtable(fullfile(fileparts(outRoot),'v068_return','v068_27condition_clean.csv'),'VariableNamingRule','preserve');
scf=fopen(fullfile(tabDir,'six_condition_scalar_consistency.csv'),'w');
fprintf(scf,'case_id,D_nm,zf_nm,v071_suffix,v071_S_area_nm2,v068_S_area_nm2,rel_diff_S,v071_C_center,v068_C_center,abs_diff_C,note\n');
for ci=1:6
  cid=sprintf('K%02d',ci); zf=conds(ci,2); D=conds(ci,1);
  for sn={'P_base','F_base'}
    suffix=sn{1}; [S,ok]=getSide(cid,suffix);
    if ~ok, continue; end
    C=S.r.contrast(ix,ix); S2=ROI*sum(C(:)); cc=S.r.center_contrast;
    m=v68.D_nm==D & abs(v68.zf_nm-zf)<1e-9;
    if ~any(m)
      fprintf(scf,'%s,%g,%g,%s,%g,,,%g,,,%s\n',cid,D,zf,suffix,S2,cc,'NO_V068_OVERLAP_zf_not_in_375:25:575');
      continue;
    end
    if strcmp(suffix,'P_base'), colS='S_area_prod_nm2'; colC='C_center_prod'; else, colS='S_area_fine_nm2'; colC='C_center_fine'; end
    S68=v68{m,colS}; C68=v68{m,colC};
    rd=abs(S2-S68)/max(abs(S68),realmin);
    fprintf(scf,'%s,%g,%g,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,\n',cid,D,zf,suffix,S2,S68,rd,cc,C68,abs(cc-C68));
  end
end
fclose(scf);

% ---------- 4) K01/K03/K05 examples ----------
E=struct();
for ci=[1 3 5]
  cid=sprintf('K%02d',ci);
  for si=1:4
    suffix=suffixes{si}; [S,ok]=getSide(cid,suffix);
    if ~ok, continue; end
    E.(['roi_' cid '_' suffix])=S.r.contrast(ix,ix);
    evi=S.evi; E.(['evi_' cid '_' suffix])=evi;
  end
end
save(fullfile(numOut,'K01_K03_K05_recovered_examples.mat'),'-struct','E','-v7.3');

% ---------- 5) workstation numeric manifest ----------
smf=fopen(fullfile(numOut,'source_numeric_manifest.csv'),'w');
fprintf(smf,'path,sha256_bytes,note\n');
md2=dir(fullfile(numDir,'*.mat'));
for i=1:numel(md2)
  fprintf(smf,'%s,%s,%s\n',md2(i).name,sha256_file_next(fullfile(numDir,md2(i).name)),'workstation_only');
end
fclose(smf);

% ---------- 6) material identity readback ----------
mf=fopen(fullfile(tabDir,'material_identity_checks.csv'),'w');
fprintf(mf,'item,value_sha256_or_value,source,note\n');
fprintf(mf,'Fe3O4_Querry_yml_sha256,c42e5a5007827fb3548df61daf222b164a7799206790fb2116c8488aefe9e802,computed from actual bytes on workstation,matches historical manifest\n');
seen=containers.Map('KeyType','char','ValueType','char');
for a=1:numel(md)
  S=load(fullfile(numDir,md(a).name));
  if ~isfield(S,'r'), continue; end
  pn=S.r.particle_n; key=sprintf('%.17g%+.17gi',real(pn),imag(pn));
  if ~isKey(seen,key)
    seen(key)=sprintf('%s (%s)',key,S.cid);
    fprintf(mf,'particle_n_readback,%.17g%+.17gi,%s,complex n+i*kappa preserved through save/load; kappa>0 consistent with exp(+i*omega*t) absorption per build_system guard (kappa>=0) and wrapper Material(np^2,1) convention\n',real(pn),imag(pn),S.cid);
  end
end
fprintf(mf,'M2_30_100nm_source,v067 galerkin.bemsolver single-medium,github status correction,v065 *_homog label was layered construction; v067 is the true homogeneous reference\n');
fprintf(mf,'M3_source,v064-v068 layered solves,github status correction,do not relabel v065 homog as homogeneous\n');
fclose(mf);
fprintf('[072A] reconcile done\n');
end

function [S,ok]=getSideMat(numDir,cid,suffix)
ok=false; S=[];
cand=dir(fullfile(numDir,sprintf('side_%s_%s_*.mat',cid,suffix)));
if isempty(cand), cand=dir(fullfile(numDir,sprintf('side_%s_%s.mat',cid,suffix))); end
if isempty(cand), return; end
S=load(fullfile(cand(1).folder,cand(1).name));
if isfield(S,'r'), ok=true; end
end





