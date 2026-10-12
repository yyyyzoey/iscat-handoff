function run_v067_d3_only()
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
od65='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v065_return';
outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v067_return';
cx=33; ix=(cx-20):(cx+20);
refine={};
% D60 C_center zero-crossing
for zf=500:2.5:525
  sp=load(fullfile(od65,'D60_s_576.mat'),'s'); sp=sp.s;
  sf=load(fullfile(od65,'D60_s_1444.mat'),'s'); sf=sf.s;
  cp=sp.cfg; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
  rp=render_system(sp,cp);
  cf=sf.cfg; cf.focus_nm=[0,0,zf]; cf.sampling.subpixels=5;
  rf=render_system(sf,cf);
  refine{end+1}=struct('D',60,'zf',zf,'C_center_prod',rp.contrast(33,33), ...
    'C_center_fine',rf.contrast(33,33),'scope','POST_HOC_LINEAR_INTERPOLATION_NOT_A_SIMULATED_ROOT'); %#ok<AGROW>
  fprintf('[067:d3] D60 zf=%.1f Cc_p=%.6f Cc_f=%.6f\n',zf,rp.contrast(33,33),rf.contrast(33,33));
end
% D100 S_area zero-crossing
for zf=427.5:2.5:447.5
  sp=load(fullfile(od65,'D100_s_576.mat'),'s'); sp=sp.s;
  sf=load(fullfile(od65,'D100_s_1444.mat'),'s'); sf=sf.s;
  cp=sp.cfg; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
  rp=render_system(sp,cp);
  cf=sf.cfg; cf.focus_nm=[0,0,zf]; cf.sampling.subpixels=5;
  rf=render_system(sf,cf);
  sA_p=65^2*sum(rp.contrast(ix,ix),'all'); sA_f=65^2*sum(rf.contrast(ix,ix),'all');
  refine{end+1}=struct('D',100,'zf',zf,'S_area_prod',sA_p,'S_area_fine',sA_f, ...
    'scope','POST_HOC_LINEAR_INTERPOLATION_NOT_A_SIMULATED_ROOT'); %#ok<AGROW>
  fprintf('[067:d3] D100 zf=%.1f S_area_prod=%.2f S_area_fine=%.2f\n',zf,sA_p,sA_f);
end
writetable(struct2table([refine{:}]),fullfile(outRoot,'d3_zero_crossing_refinement.csv'));
fprintf('[067:d3] done: %d refinement points\n',numel(refine));
end
