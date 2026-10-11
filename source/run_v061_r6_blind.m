function run_v061_r6_blind(outRoot, nPerCond)
% v061 R6: blind acquisitions + fits on the 10 pre-registered conditions.
% Estimator reads anonymous observations; truth joined only at evaluation.
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v042_handoff\iSCAT_v042_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v048_handoff\iSCAT_v048_Codex_handoff\matlab');
if nargin<1, outRoot=fullfile(projectRoot,'v061_return','r6_blind'); end
if nargin<2, nPerCond=100; end
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));
recipeFile='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v048_handoff\iSCAT_v048_Codex_handoff\config\camera_development048.json';
M=load(fullfile(projectRoot,'v058_return','dense_c','models_dense_full32.mat'),'models'); models=M.models;
refs=fullfile(projectRoot,'v061_return','r6_refs');
B=[28.9 381.7 -617.1 593.7; 33.2 559.3 611.3 -601.9; 39.1 421.7 -333.7 287.9;
   43.3 573.1 271.3 -419.7; 49.1 468.3 12.3 -27.9; 57.3 394.7 -451.1 -137.3;
   63.1 539.1 145.7 503.1; 71.3 445.9 437.9 -299.3; 79.1 506.3 -205.7 167.9;
   85.1 484.7 581.3 621.7];
opts=struct('D_bounds',[28,86],'z_bounds',[375,575],'mask_half',20,'center_bound_pixels',10);
res={};
for i=1:size(B,1)
  D=B(i,1); zf=B(i,2); xy=B(i,3:4); sid=sprintf('B%02d_D%.1f',i,D);
  truthFile=fullfile(refs,[sid '_z' num2str(round(zf)) '_truth'],'truth_private.mat');
  if ~isfile(truthFile)
    % render truth once from the fine system (post-processing reuse, no BEM)
    sFile=fullfile(refs,[sid '_s_fine1444.mat']); L=load(sFile,'s'); s=L.s;
    d=fullfile(refs,sprintf('%s_z%d_truth',sid,round(zf)));
    RENDER_TRUTH048(sFile,'s',zf,xy,d);
  end
  for k=1:nPerCond
    trial=600+(i-1)*nPerCond+k; % RNG namespace 60480601..60481600
    acqDir=fullfile(outRoot,sprintf('acq_%s_%03d',sid,trial));
    recFile=fullfile(acqDir,'fit_record.json');
    if isfile(recFile), continue; end
    if isfile(fullfile(acqDir,'observation.mat'))
      L=load(fullfile(acqDir,'observation.mat'),'observation'); obs=L.observation;
    else
      paths=MAKE_CAMERA048(truthFile,recipeFile,trial,acqDir);
      L=load(paths.observation,'observation'); obs=L.observation;
    end
    f=iscat047.fit(models.C,obs.C,opts);
    % estimation-side record: NO truth fields (blind); truth joined at evaluation
    rec=struct('cond_id',sid,'trial',trial,'D_fit',f.theta(1),'z_fit',f.theta(2), ...
      'x_fit',f.theta(3),'y_fit',f.theta(4),'status',f.status,'data_sse',f.data_sse, ...
      'null_sse',f.null_sse,'T',f.null_sse-f.data_sse,'exitflag',f.best_exitflag);
    fid=fopen(recFile,'w'); fwrite(fid,jsonencode(rec)); fclose(fid);
    % evaluation joins truth
    thr=load(fullfile(refs,sprintf('%s_z%d_truth',sid,round(zf)),'truth_private.mat'),'truth');
    Derr=rec.D_fit-thr.truth.theta_nm(1); zerr=rec.z_fit-thr.truth.theta_nm(2);
    perr=hypot(rec.x_fit-thr.truth.theta_nm(3),rec.y_fit-thr.truth.theta_nm(4))/65;
    res{end+1}=struct('cond_id',sid,'trial',trial,'D_true',D,'D_fit',f.theta(1), ...
      'D_err',Derr,'z_err',zerr,'pos_err_px',perr,'status',f.status,'T',rec.T, ...
      'at_boundary',any(abs([f.theta(1)-28,f.theta(1)-86,f.theta(2)-375,f.theta(2)-575])<1e-9)|| ...
      any(abs([f.theta(3),f.theta(4)])==650)); %#ok<AGROW>
  end
  C=res(max(1,end-nPerCond+1):end);
  de=cellfun(@(r)r.D_err,C); pe=cellfun(@(r)r.pos_err_px,C);
  fprintf('[061:r6] %s n=%d Bias=%+.3f RMSE=%.3f posMax=%.3f\n',sid,numel(de),mean(de),sqrt(mean(de.^2)),max(pe));
  writetable(struct2table([res{:}]),fullfile(outRoot,'r6_blind_per_trial.csv'));
end
writetable(struct2table([res{:}]),fullfile(outRoot,'r6_blind_per_trial.csv'));
fprintf('[061:r6] blind complete: %d records\n',numel(res));
end

