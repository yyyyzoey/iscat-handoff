function run_v070_controlled(outRoot)
% v070: 6 conditions x 4 numerical configurations (24 controlled renders, zero new BEM).
% P_common: prod 576 angles 100/151 Bessel 4001 q5
% F_q7: fine 1444 q7
% F_angle: fine 1444 angles 50/51 (prod angles)
% F_bessel: fine 1444 Bessel 2001
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
if nargin<1, outRoot=fullfile(projectRoot,'v070_return'); end
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));
od65='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v065_return';
od64='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v064_return\m3_60nm';
% 6 key conditions
conds=[60 512.5; 60 515; 100 425; 100 435; 100 437.5; 100 450];
cx=33; ix=(cx-20):(cx+20);
res={}; plan={};
% Build the 24-item plan
suffixes={'P_common','F_q7','F_angle','F_bessel'};
for ci=1:size(conds,1)
  D=conds(ci,1); zf=conds(ci,2);
  for si=1:4
    plan{end+1}={ci,sprintf('K%02d',ci),D,zf,suffixes{si}}; %#ok<AGROW>
  end
end
% Write plan CSV first
pfid=fopen(fullfile(outRoot,'controlled_plan24.csv'),'w');
fprintf(pfid,'case_idx,case_id,D_nm,zf_nm,suffix\n');
for i=1:numel(plan), fprintf(pfid,'%d,%s,%g,%g,%s\n',plan{i}{1},plan{i}{2},plan{i}{3},plan{i}{4},plan{i}{5}); end
fclose(pfid);
% Execute each item
for pi=1:numel(plan)
  ci=plan{pi}{1}; cid=plan{pi}{2}; D=plan{pi}{3}; zf=plan{pi}{4}; suffix=plan{pi}{5};
  sid=sprintf('D%d',D);
  status='NOT_RUN'; note='';
  try
    % Load the appropriate system
    switch suffix
      case 'P_common'
        f=fullfile(od65,sprintf('%s_s_576.mat',sid));
        L=load(f,'s'); sv=L.s;
        % Override angles/Bessel to fine settings
        c=sv.cfg; c.numerics.ntheta=100; c.numerics.nphi=151; c.numerics.bessel_table_points=4001;
        c.focus_nm=[0,0,zf]; c.sampling.subpixels=5;
        r=render_system(sv,c);
      case 'F_q7'
        f=fullfile(od65,sprintf('%s_s_1444.mat',sid));
        L=load(f,'s'); sv=L.s;
        c=sv.cfg; c.focus_nm=[0,0,zf]; c.sampling.subpixels=7;
        r=render_system(sv,c);
      case 'F_angle'
        f=fullfile(od65,sprintf('%s_s_1444.mat',sid));
        L=load(f,'s'); sv=L.s;
        c=sv.cfg; c.numerics.ntheta=50; c.numerics.nphi=51;
        c.focus_nm=[0,0,zf]; c.sampling.subpixels=5;
        r=render_system(sv,c);
      case 'F_bessel'
        f=fullfile(od65,sprintf('%s_s_1444.mat',sid));
        L=load(f,'s'); sv=L.s;
        c=sv.cfg; c.numerics.bessel_table_points=2001;
        c.focus_nm=[0,0,zf]; c.sampling.subpixels=5;
        r=render_system(sv,c);
    end
    C=r.contrast; status='COMPLETED';
    % Store the contrast for later comparison
    assignin('base',['C_' suffix '_' num2str(ci)],C);
  catch ME
    status='FAILED'; note=ME.message;
    fprintf('[070] %s %s FAILED: %s\n',cid,suffix,ME.message);
  end
  res{end+1}=struct('case_idx',pi,'case_id',cid,'D',D,'zf',zf,'suffix',suffix, ...
    'status',status,'note',note); %#ok<AGROW>
  fprintf('[070] %s %s: %s\n',cid,suffix,status);
end
% Now compute comparisons for pairs where both sides completed
cx=33; ix=(cx-20):(cx+20);
cmp_rows={};
for ci=1:6
  D=conds(ci,1); zf=conds(ci,2); cid=sprintf('K%02d',ci);
  vals=struct();
  ok=true;
  for si=1:4
    suffix=suffixes{si};
    match=find([res.case_idx]==(ci-1)*4+si & strcmp({res.suffix},suffix));
    if isempty(match) || ~strcmp(res(match(1)).status,'COMPLETED'), ok=false; break; end
  end
  if ~ok, continue; end
  % Get C arrays from base workspace
  for si=1:4
    suffix=suffixes{si};
    C=getappdata(0,['C_' suffix '_' num2str(ci)]);
    if si==1, C_P_common=C; end
    if si==2, C_F_q7=C; end
    if si==3, C_F_angle=C; end
    if si==4, C_F_bessel=C; end
  end
  % Get baselines
  sid=sprintf('D%d',D);
  sp=load(fullfile(od65,sprintf('%s_s_576.mat',sid)),'s'); sp=sp.s;
  sf=load(fullfile(od65,sprintf('%s_s_1444.mat',sid)),'s'); sf=sf.s;
  cp=sp.cfg; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
  rpb=render_system(sp,cp); C_P_base=rp.contrast; C_P_base=rpb.contrast;
  cf=sf.cfg; cf.focus_nm=[0,0,zf]; cf.sampling.subpixels=5;
  rfb=render_system(sf,cf); C_F_base=rfb.contrast;
  % Compute differences
  pairs={'P_base-F_base',C_P_base,C_F_base; 'P_base-P_common',C_P_base,C_P_common; ...
         'P_common-F_base',C_P_common,C_F_base; 'F_q7-F_base',C_F_q7,C_F_base; ...
         'F_angle-F_base',C_F_angle,C_F_base; 'F_bessel-F_base',C_F_bessel,C_F_base};
  for pi2=1:size(pairs,1)
    nm=pairs{pi2,1}; A=pairs{pi2,2}; B=pairs{pi2,3};
    rF=norm(A(:)-B(:),2)/max(norm(B(:)),realmin);
    rS=norm(A-B,2)/max(norm(B,2),realmin);
    cmp_rows{end+1}={cid,D,zf,nm,rF,rS,rF<0.02}; %#ok<AGROW>
    fprintf('[070:cmp] %s %s: rF=%.4f rSpec=%.4f\n',cid,nm,rF,rS);
  end
end
% Write comparison CSV
chdr={'case_id','D_nm','zf_nm','comparison','relL2_Frobenius','spectral_diagnostic','gate2pct'};
cfid=fopen(fullfile(outRoot,'controlled_results24.csv'),'w');
fprintf(cfid,'%s\n',strjoin(chdr,','));
for i=1:numel(cmp_rows), fprintf(cfid,'%s,%g,%g,%s,%.17g,%.17g,%d\n',cmp_rows{i}{:}); end
fclose(cfid);
fprintf('[070] controlled renders complete: %d comparisons\n',numel(cmp_rows));
end
