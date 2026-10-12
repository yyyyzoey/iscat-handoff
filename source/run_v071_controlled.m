function run_v071_controlled(outRoot, mode)
% v071: honest controlled comparison after v070 audit.
% Executable sides: P_base, F_base, F_q7, F_bessel (frozen angle grids of saved far).
% NOT_EXECUTABLE: P_common (prod far needed on 100/151), F_angle (fine far needed on 200/301)
%   because build_system sol objects were not persisted in v065 *_s_*.mat and
%   cfg.numerics.ntheta/nphi is a dead switch inside render_system (verified by probe).
% mode: 'k01' (default) | 'all' | 'verify' (loads numeric mats only, no render)
if nargin<1 || isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v071_return'; end
if nargin<2 || isempty(mode), mode='k01'; end
projectRoot=fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
if strcmp(mode,'verify')
  % Independent-session recheck: no BEM, no render, only numeric mats on disk.
  numDir=fullfile(outRoot,'numeric');
  conds=[60 512.5; 60 515; 100 425; 100 435; 100 437.5; 100 450];
  suffixes={'P_base','F_base','F_q7','F_bessel','P_common','F_angle'};
  pairDefs={'P_base-F_base','P_base','F_base'; 'P_base-P_common','P_base','P_common'; ...
    'P_common-F_base','P_common','F_base'; 'F_q7-F_base','F_q7','F_base'; ...
    'F_angle-F_base','F_angle','F_base'; 'F_bessel-F_base','F_bessel','F_base'};
  cx=33; ix=(cx-20):(cx+20); Nroi=numel(ix)^2;
  computeComparisons(numDir,outRoot,'controlled_comparisons_recheck_v071.csv',conds,suffixes,pairDefs,ix,Nroi);
  f1=fullfile(outRoot,'controlled_comparisons_v071.csv');
  f2=fullfile(outRoot,'controlled_comparisons_recheck_v071.csv');
  t1=fileread(f1); t2=fileread(f2);
  if strcmp(t1,t2), fprintf('[071:verify] PASS: recheck CSV identical to original (%d bytes)\n',numel(t1));
  else, fprintf('[071:verify] FAIL: recheck differs\n'); end
  return;
end
addpath(fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
if ~isfolder(outRoot), mkdir(outRoot); end
numDir=fullfile(outRoot,'numeric'); if ~isfolder(numDir), mkdir(numDir); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
od65=fullfile(projectRoot,'v065_return');

fprintf('[071:preflight] matlab=%s\n[071:preflight] render_system=%s\n[071:preflight] build_system=%s\n', ...
    version, which('render_system'), which('build_system'));
code_sha=sha256_file_next([mfilename('fullpath'),'.m']);
rs_sha=sha256_file_next(which('render_system'));
fprintf('[071:preflight] code_sha=%s render_system_sha=%s\n',code_sha,rs_sha);

conds=[60 512.5; 60 515; 100 425; 100 435; 100 437.5; 100 450];
suffixes={'P_base','F_base','F_q7','F_bessel','P_common','F_angle'};
execFlag=[1 1 1 1 0 0];
if strcmp(mode,'k01'), caseSel=1; else, caseSel=1:6; end
cx=33; ix=(cx-20):(cx+20); roiLen=numel(ix);

render_ledger={};
for ci=caseSel
  cid=sprintf('K%02d',ci); D=conds(ci,1); zf=conds(ci,2); sid=sprintf('D%d',D);
  for si=1:numel(suffixes)
    suffix=suffixes{si}; exec=execFlag(si);
    if ~exec
      if strcmp(suffix,'P_common'), sfar=fullfile(od65,sprintf('%s_s_576.mat',sid)); want=[100 151];
      else, sfar=fullfile(od65,sprintf('%s_s_1444.mat',sid)); want=[200 301]; end
      L=load(sfar,'s'); sv=L.s;
      evi=struct('status','NOT_EXECUTABLE','reason','SOL_NOT_PERSISTED_AND_CFG_ANGLE_DEAD_SWITCH', ...
        'ntheta_request',want(1),'nphi_request',want(2), ...
        'ntheta_lens',numel(sv.lens.theta),'nphi_lens',numel(sv.lens.phi), ...
        'far_directions',size(sv.far,1),'sol_file',sfar, ...
        'sol_sha256',sha256_file_next(sfar),'code_sha256',code_sha);
      key=sprintf('%s|%s|%s',cid,suffix,evi.sol_sha256(1:16));
      save(fullfile(numDir,sprintf('side_%s_%s.mat',cid,suffix)),'evi','key','cid','suffix','-v7.3');
      fprintf('[071] %s %s: NOT_EXECUTABLE (far_dirs=%d want=%d, lens=%dx%d)\n', ...
        cid,suffix,evi.far_directions,want(1)*want(2),evi.ntheta_lens,evi.nphi_lens);
      continue;
    end
    if strcmp(suffix,'P_base'), sfar=fullfile(od65,sprintf('%s_s_576.mat',sid));
    else, sfar=fullfile(od65,sprintf('%s_s_1444.mat',sid)); end
    sol_sha=sha256_file_next(sfar);
    L=load(sfar,'s'); sv=L.s; c=sv.cfg;
    switch suffix
      case 'P_base',  c.sampling.subpixels=5;
      case 'F_base',  c.sampling.subpixels=5;
      case 'F_q7',    c.sampling.subpixels=7;
      case 'F_bessel',c.sampling.subpixels=5; c.numerics.bessel_table_points=8001;
    end
    c.focus_nm=[0,0,zf];
    key=sprintf('%s|%s|%s|%d|%d|%g|%d',cid,suffix,sol_sha(1:16), ...
      c.numerics.bessel_table_points,c.sampling.subpixels,zf,sv.mesh_vertices);
    kh=hashstr16(key);
    fmat=fullfile(numDir,sprintf('side_%s_%s_%s.mat',cid,suffix,kh));
    if isfile(fmat)
      S=load(fmat); r=S.r; evi=S.evi;
      fprintf('[071] %s %s: CACHE_HIT %s\n',cid,suffix,kh);
    else
      t0=tic; r=render_system(sv,c); rsec=toc(t0);
      evi=struct('mesh_vertices',sv.mesh_vertices, ...
        'ntheta_lens',numel(sv.lens.theta),'nphi_lens',numel(sv.lens.phi), ...
        'far_directions',size(sv.far,1),'ntab',c.numerics.bessel_table_points, ...
        'subpixels',c.sampling.subpixels,'focus_z_nm',zf, ...
        'fine_grid_len',numel(r.fine_x_nm),'sol_sha256',sol_sha, ...
        'far_sha256',hashdata(sv.far),'code_sha256',code_sha, ...
        'render_seconds',rsec,'identity_err',r.intensity_identity_relative_error, ...
        'status','COMPLETED','cache_key',key);
      save(fmat,'r','evi','key','cid','suffix','-v7.3');
      fprintf('[071] %s %s: COMPLETED render %.1fs (lens=%dx%d dirs=%d ntab=%d q=%d)\n', ...
        cid,suffix,rsec,evi.ntheta_lens,evi.nphi_lens,evi.far_directions,evi.ntab,evi.subpixels);
    end
    render_ledger(end+1,:)={cid,suffix,evi.mesh_vertices,evi.ntab,evi.subpixels,zf, ...
      evi.render_seconds,evi.status}; %#ok<AGROW>
    if strcmp(suffix,'P_base') && strcmp(cid,'K01') && ~isfile(fullfile(numDir,'probe_angle_deadswitch.mat'))
      cp=sv.cfg; cp.numerics.ntheta=200; cp.numerics.nphi=301; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
      t0=tic; render_system(sv,cp); psec=toc(t0);
      pevi=struct('status','INACTIVE_CONTROL','reason','cfg.numerics.ntheta/nphi ignored by render_system', ...
        'ntheta_request',200,'nphi_request',301,'ntheta_lens',numel(sv.lens.theta), ...
        'nphi_lens',numel(sv.lens.phi),'far_directions',size(sv.far,1), ...
        'probe_seconds',psec,'code_sha256',code_sha);
      save(fullfile(numDir,'probe_angle_deadswitch.mat'),'pevi','key','cid','suffix','-v7.3');
      fprintf('[071] probe: cfg 200/301 -> lens=%dx%d dirs=%d (dead switch confirmed)\n', ...
        pevi.ntheta_lens,pevi.nphi_lens,pevi.far_directions);
      render_ledger(end+1,:)={'K01','probe_angle_deadswitch',sv.mesh_vertices,200,5,zf,psec,pevi.status}; %#ok<AGROW>
    end
  end
end

% ---------- side scalars (frozen 41x41 ROI = full-grid 33 +/- 20) ----------
sc=fopen(fullfile(outRoot,'controlled_side_scalars_v071.csv'),'w');
fprintf(sc,'case_id,D_nm,zf_nm,suffix,executable,C_center,S_area,S_plus,S_minus,chi1,K_pixelL2,roi_size\n');
md=dir(fullfile(numDir,'side_*.mat'));
for a=1:numel(md)
  S=load(fullfile(numDir,md(a).name));
  if ~isfield(S,'r') || ~isfield(S,'cid'), continue; end
  C=S.r.contrast(ix,ix); N=numel(C);
  Sarea=sum(C(:)); Sp=sum(max(C,0),'all'); Sm=sum(min(C,0),'all');
  fprintf(sc,'%s,%g,%g,%s,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%d\n', ...
    S.cid,S.r.cfg.particle.diameter_nm,S.r.cfg.focus_nm(3),S.suffix, ...
    1,S.r.center_contrast,Sarea,Sp,Sm,sum(abs(C(:)))/max(abs(Sarea),realmin), ...
    sqrt(N)*norm(C(:))/max(abs(Sarea),realmin),roiLen);
end
fclose(sc);

% ---------- plan rows ----------
pfid=fopen(fullfile(outRoot,'controlled_plan24_v071.csv'),'w');
fprintf(pfid,'case_id,D_nm,zf_nm,suffix,ntheta_lens,nphi_lens,ntab,subpixels,far_directions,execution_status,reason\n');
for ci=1:6
  cid=sprintf('K%02d',ci); D=conds(ci,1); zf=conds(ci,2);
  for si=1:numel(suffixes)
    suffix=suffixes{si};
    cand=dir(fullfile(numDir,sprintf('side_%s_%s_*.mat',cid,suffix)));
    if isempty(cand), cand=dir(fullfile(numDir,sprintf('side_%s_%s.mat',cid,suffix))); end
    if isempty(cand)
      fprintf(pfid,'%s,%g,%g,%s,,,,,,MISSING,side_mat_not_found\n',cid,D,zf,suffix); continue;
    end
    S=load(fullfile(cand(1).folder,cand(1).name));
    if strcmp(S.evi.status,'NOT_EXECUTABLE')
      fprintf(pfid,'%s,%g,%g,%s,%d,%d,,,,NOT_EXECUTABLE,SOL_NOT_PERSISTED\n',cid,D,zf,suffix, ...
        S.evi.ntheta_lens,S.evi.nphi_lens);
    else
      fprintf(pfid,'%s,%g,%g,%s,%d,%d,%d,%d,%d,COMPLETED,\n',cid,D,zf,suffix, ...
        S.evi.ntheta_lens,S.evi.nphi_lens,S.evi.ntab,S.evi.subpixels,S.evi.far_directions);
    end
  end
end
fclose(pfid);

% ---------- comparisons ----------
pairDefs={'P_base-F_base','P_base','F_base'; 'P_base-P_common','P_base','P_common'; ...
  'P_common-F_base','P_common','F_base'; 'F_q7-F_base','F_q7','F_base'; ...
  'F_angle-F_base','F_angle','F_base'; 'F_bessel-F_base','F_bessel','F_base'};
computeComparisons(numDir,outRoot,'controlled_comparisons_v071.csv',conds,suffixes,pairDefs,ix,roiLen^2);

lf=fopen(fullfile(outRoot,'cost_ledger_v071.csv'),'w');
fprintf(lf,'case_id,suffix,mesh_vertices,ntab,subpixels,zf_nm,seconds,status\n');
for i=1:size(render_ledger,1), fprintf(lf,'%s,%s,%d,%d,%d,%g,%.2f,%s\n',render_ledger{i,:}); end
fclose(lf);
mf=fopen(fullfile(outRoot,'numeric_manifest_v071.csv'),'w');
fprintf(mf,'path,sha256,contrast_shape,has_contrast\n');
md=dir(fullfile(numDir,'*.mat'));
for i=1:numel(md)
  fp=fullfile(numDir,md(i).name); S=load(fp,'-mat');
  if isfield(S,'r') && isfield(S.r,'contrast'), shp=sprintf('%dx%d',size(S.r.contrast)); hc=1;
  else, shp=''; hc=0; end
  fprintf(mf,'%s,%s,%s,%d\n',md(i).name,sha256_file_next(fp),shp,hc);
end
fclose(mf);
fprintf('[071] mode=%s done\n',mode);
end

function computeComparisons(numDir,outRoot,fname,conds,suffixes,pairDefs,ix,Nroi)
cfid=fopen(fullfile(outRoot,fname),'w');
fprintf(cfid,'case_id,D_nm,zf_nm,comparison,A_side,B_side,status,num,den,rF,spectral_norm,eta,abs_dS,S_ref,identity_absdiff\n');
for ci=1:6
  cid=sprintf('K%02d',ci); D=conds(ci,1); zf=conds(ci,2);
  sidePath=containers.Map('KeyType','char','ValueType','char');
  for si=1:numel(suffixes)
    suffix=suffixes{si};
    cand=dir(fullfile(numDir,sprintf('side_%s_%s_*.mat',cid,suffix)));
    if isempty(cand), cand=dir(fullfile(numDir,sprintf('side_%s_%s.mat',cid,suffix))); end
    if isempty(cand), sidePath(suffix)=''; continue; end
    sidePath(suffix)=fullfile(cand(1).folder,cand(1).name);
  end
  diffs=struct();
  for k=1:size(pairDefs,1)
    nm=pairDefs{k,1}; A=pairDefs{k,2}; B=pairDefs{k,3};
    if isempty(sidePath(A)) || isempty(sidePath(B))
      fprintf(cfid,'%s,%g,%g,%s,%s,%s,MISSING,,,,,,,,\n',cid,D,zf,nm,A,B); continue;
    end
    SA=load(sidePath(A)); SB=load(sidePath(B));
    if isfield(SA,'evi') && strcmp(SA.evi.status,'NOT_EXECUTABLE') || ...
       isfield(SB,'evi') && strcmp(SB.evi.status,'NOT_EXECUTABLE')
      fprintf(cfid,'%s,%g,%g,%s,%s,%s,NOT_EXECUTABLE,,,,,,,,\n',cid,D,zf,nm,A,B); continue;
    end
    ca=SA.r.contrast(ix,ix); cb=SB.r.contrast(ix,ix);
    d=ca-cb; num=norm(d(:),2); den=norm(cb(:),2);
    rF=num/max(den,realmin); rS=norm(d,2)/max(norm(cb,2),realmin);
    eta=abs(sum(d(:)))/(sqrt(Nroi)*num);
    dS=sum(d(:)); SR=sum(cb(:));
    lhs=abs(dS)/max(abs(SR),realmin); K2R=sqrt(Nroi)*den/max(abs(SR),realmin); rhs=K2R*rF*eta;
    idiff=abs(lhs-rhs)/max(lhs,realmin);
    fprintf(cfid,'%s,%g,%g,%s,%s,%s,COMPLETED,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n', ...
      cid,D,zf,nm,A,B,num,den,rF,rS,eta,dS,SR,idiff);
    diffs.(strrep(nm,'-','_'))=d;
  end
  if ~isempty(fieldnames(diffs)) && strcmp(fname,'controlled_comparisons_v071.csv')
    save(fullfile(numDir,sprintf('diffs_%s.mat',cid)),'-struct','diffs','-v7.3');
  end
end
fclose(cfid);
end

function h=hashstr16(s)
  h=hashdata(uint8(s));
  if numel(h)>16, h=h(1:16); end
end
function h=hashdata(x)
  md=java.security.MessageDigest.getInstance('SHA-256');
  if ~isreal(x)
    md.update(uint8(typecast(double(real(x(:).')),'uint8')));
    md.update(uint8(typecast(double(imag(x(:).')),'uint8')));
  else
    md.update(uint8(typecast(double(x(:).'),'uint8')));
  end
  out=typecast(md.digest(),'uint8');
  h=lower(reshape(dec2hex(out,2).',1,[]));
end



