function run_v061_r5_detection(outRoot, stage)
% v061 R5: blank generation + H0/H1 scoring + tau freeze + 300 independent validation.
% H0: no particle -> contrast mu0 = 0 (exact for contrast maps); J0 = ||W^.5 Y||^2 = nullSSE.
% J1: dense-model fit (same frozen search) -> J1 = data_sse. T = J0 - J1.
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v042_handoff\iSCAT_v042_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v048_handoff\iSCAT_v048_Codex_handoff\matlab');
if nargin<1, outRoot=fullfile(projectRoot,'v061_return','r5_detection'); end
if nargin<2, stage='dev'; end
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,['r5_' stage '.log'])); cl=onCleanup(@() diary('off'));
a=jsondecode(fileread('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v048_handoff\iSCAT_v048_Codex_handoff\config\camera_development048.json'));
M=load(fullfile(projectRoot,'v058_return','dense_c','models_dense_full32.mat'),'models'); models=M.models;
opts=struct('D_bounds',[28,86],'z_bounds',[375,575],'mask_half',20,'center_bound_pixels',10);
switch stage
  case 'dev', N=100; seedOff=1000000; tag='dev';
  case 'val', N=300; seedOff=2000000; tag='val';
end
% background reference field from the D45 z450 truth (uniform Iref)
L=load(fullfile(projectRoot,'v056_return','s5_truth','D45_z450_truth','truth_private.mat'),'truth');
Iref=L.truth.Iref;
pre=iscat048.preflight(Iref,Iref,a); scale=pre.scale_e_per_optical_unit;
fprintf('[061:r5] stage=%s N=%d scale=%.1f\n',stage,N,scale);
resFile=fullfile(outRoot,['blank_' tag '_results.mat']);
res={};
if isfile(resFile), R=load(resFile,'res'); res=R.res; end
for k=1:N
  idx=k; % within-stage index
  if any(cellfun(@(r)double(r.idx),res)==double(k)), continue; end
  seed=a.seed_base+seedOff+idx;
  rng(seed,'twister');
  signal=iscat048.capture(scale*Iref,a.n_signal_frames,a);       % foreground: background only
  reference=iscat048.capture(scale*Iref,a.n_reference_frames,a); % 8 reference frames
  obs=iscat048.observation_from_raw(signal,reference,L.truth.x_nm,L.truth.y_nm,a);
  f=iscat047.fit(models.C,obs.C,opts);
  T=f.null_sse-f.data_sse;
  valid=~any(strcmp(f.status,{'SATURATED_SUPPORT','NO_SIGNAL_EXACT_ZERO'})) && isfinite(T);
  res{end+1}=struct('idx',idx,'seed',seed,'J0',f.null_sse,'J1',f.data_sse, ...
    'T',T,'status',f.status,'valid',valid,'D_fit',f.theta(1),'z_fit',f.theta(2), ...
    'x_fit',f.theta(3),'y_fit',f.theta(4)); %#ok<AGROW>
  if mod(k,25)==0 || k<=10
    fprintf('[061:r5] %s %d/%d T=%.4g valid=%d\n',stage,k,N,T,valid);
  end
end
T=cellfun(@(r)r.T,res(:).'); V=cellfun(@(r)r.valid,res(:).');
Tv=T(V);
if strcmp(stage,'dev')
  tau=max(Tv);
  fprintf('[061:r5] TAU=%.17g (max over %d valid dev blanks)\n',tau,numel(Tv));
  fz=struct('schema','iscat061.threshold_freeze.1','frozen_at',datestr(now,'yyyy-mm-dd HH:MM:SS'), ...
    'tau_unrounded',tau,'comparison','T > tau (strict)','dev_n',numel(Tv), ...
    'dev_valid_ids',(V.* (1:N)),'model','models_dense_full32.mat','D_bounds',[28,86], ...
    'z_bounds',[375,575],'mask_half',20,'center_bound_pixels',10, ...
    'max_starts',8,'recipe','camera_development048.json (1506e)','H0','mu0=0 contrast (exact for empty background)','J1_source','frozen multi-start refine4 best');
  fid=fopen(fullfile(outRoot,'threshold_freeze.json'),'w'); fwrite(fid,jsonencode(fz)); fclose(fid);
else
  fz=jsondecode(fileread(fullfile(outRoot,'threshold_freeze.json')));
  tau=fz.tau_unrounded;
end
k=sum(Tv>tau); n=numel(Tv);
if k<n, U95=betaincinv(0.95,k+1,n-k); else, U95=1; end
fprintf('[061:r5] %s: detections=%d/%d CP_U95=%.6f (8/300=0.0476 9/300=0.0518) FPR_PASS=%d\n',stage,k,n,U95,U95<=0.05);
writetable(struct2table([res{:}]),fullfile(outRoot,['blank_' tag '_per_trial.csv']));
save(fullfile(outRoot,['blank_' tag '_results.mat']),'res');
fid=fopen(fullfile(outRoot,['r5_' stage '_summary.json']),'w');
fwrite(fid,jsonencode(struct('stage',stage,'n',n,'valid',numel(Tv),'detections',k, ...
  'CP_U95',U95,'tau',tau,'FPR_pass_5pct',U95<=0.05))); fclose(fid);
end



