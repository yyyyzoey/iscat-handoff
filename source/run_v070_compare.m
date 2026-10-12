function run_v070_compare()
% v070: compare the 24 controlled renders stored in base workspace.
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v070_return';
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'compare.log')); cl=onCleanup(@() diary('off'));
od65='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v065_return';
conds=[60 512.5; 60 515; 100 425; 100 435; 100 437.5; 100 450];
suffixes={'P_common','F_q7','F_angle','F_bessel'};
cx=33; ix=(cx-20):(cx+20);
cmp_rows={};
for ci=1:6
  D=conds(ci,1); zf=conds(ci,2); cid=sprintf('K%02d',ci);
  sid=sprintf('D%d',D);
  % load baselines
  sp=load(fullfile(od65,sprintf('%s_s_576.mat',sid)),'s'); sp=sp.s;
  sf=load(fullfile(od65,sprintf('%s_s_1444.mat',sid)),'s'); sf=sf.s;
  cp=sp.cfg; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
  rpb=render_system(sp,cp); C_P_base=rpb.contrast;
  cf2=sf.cfg; cf2.focus_nm=[0,0,zf]; cf2.sampling.subpixels=5;
  rfb=render_system(sf,cf2); C_F_base=rfb.contrast;
  % get controlled renders from base workspace
  C_P_common=evalin('base',['C_P_common_' num2str(ci)]);
  C_F_q7=evalin('base',['C_F_q7_' num2str(ci)]);
  C_F_angle=evalin('base',['C_F_angle_' num2str(ci)]);
  C_F_bessel=evalin('base',['C_F_bessel_' num2str(ci)]);
  % compute all pairwise comparisons
  pairs={'P_base-F_base',C_P_base,C_F_base; 'P_base-P_common',C_P_base,C_P_common; ...
         'P_common-F_base',C_P_common,C_F_base; 'F_q7-F_base',C_F_q7,C_F_base; ...
         'F_angle-F_base',C_F_angle,C_F_base; 'F_bessel-F_base',C_F_bessel,C_F_base};
  for pi2=1:size(pairs,1)
    nm=pairs{pi2,1}; A=pairs{pi2,2}; B0=pairs{pi2,3};
    rF=norm(A(:)-B0(:),2)/max(norm(B0(:)),realmin);
    rS=norm(A-B0,2)/max(norm(B0,2),realmin);
    cmp_rows{end+1}={cid,D,zf,nm,rF,rS,rF<0.02}; %#ok<AGROW>
    fprintf('[070:cmp] %s %s: rF=%.4f rSpec=%.4f\n',cid,nm,rF,rS);
  end
end
chdr={'case_id','D_nm','zf_nm','comparison','relL2_Frobenius','spectral_diagnostic','gate2pct'};
fid=fopen(fullfile(outRoot,'controlled_results24.csv'),'w');
fprintf(fid,'%s\n',strjoin(chdr,','));
for i=1:numel(cmp_rows)
  r0=cmp_rows{i};
  fprintf(fid,'%s,%g,%g,%s,%.17g,%.17g,%d\n',r0{1},r0{2},r0{3},r0{4},r0{5},r0{6},r0{7});
end
fclose(fid);
fprintf('[070:cmp] done: %d comparisons\n',numel(cmp_rows));
end
