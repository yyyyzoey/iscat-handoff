function run_v060_r4_camera(outRoot, nPerCond)
% v060 R4: camera pilot with frozen 1506e recipe on the ten fine truths.
% Stage A: first acquisition per condition + dense-C fit; Stage B: accumulate to nPerCond.
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v042_handoff\iSCAT_v042_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v048_handoff\iSCAT_v048_Codex_handoff\matlab');
if nargin<1, outRoot=fullfile(projectRoot,'v060_return','r4_camera'); end
if nargin<2, nPerCond=20; end
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));
recipeFile='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v048_handoff\iSCAT_v048_Codex_handoff\config\camera_development048.json';
M=load(fullfile(projectRoot,'v058_return','dense_c','models_dense_full32.mat'),'models'); models=M.models;
truthT='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v056_return\s5_truth';
opts=struct('D_bounds',[28,86],'z_bounds',[375,575],'mask_half',20,'center_bound_pixels',10);
res={}; ci=0;
for D=[35,45,55,65,85]
  for z=[450,550]
    ci=ci+1;
    tid=sprintf('D%d_z%d',D,z);
    truthFile=fullfile(truthT,sprintf('D%d_z%d_truth',D,z),'truth_private.mat');
    for k=1:nPerCond
      trial=(ci-1)*nPerCond+k; % global unique index, condition-major
      acqDir=fullfile(outRoot,sprintf('acq_%s_%03d',tid,trial));
      if isfile(fullfile(acqDir,'acq_record.json'))
        rec=jsondecode(fileread(fullfile(acqDir,'acq_record.json')));
      elseif isfile(fullfile(acqDir,'observation.mat'))
        % interrupted first pass: observation exists, finish fit+record only
        L=load(fullfile(acqDir,'observation.mat'),'observation'); obs=L.observation;
        f=iscat047.fit(models.C,obs.C,opts);
        rec=struct('D',D,'z',z,'trial',trial,'D_fit',f.theta(1),'z_fit',f.theta(2), ...
          'x_fit',f.theta(3),'y_fit',f.theta(4),'status',f.status, ...
          'raw_sha256',fullfile(acqDir,'raw_acquisition.mat'), ...
          'recipe_sha256',iscat047.file_sha256(recipeFile));
        fid=fopen(fullfile(acqDir,'acq_record.json'),'w'); fwrite(fid,jsonencode(rec)); fclose(fid);
      else
        paths=MAKE_CAMERA048(truthFile,recipeFile,trial,acqDir);
        L=load(paths.observation,'observation'); obs=L.observation;
        f=iscat047.fit(models.C,obs.C,opts);
        rec=struct('D',D,'z',z,'trial',trial,'D_fit',f.theta(1),'z_fit',f.theta(2), ...
          'x_fit',f.theta(3),'y_fit',f.theta(4),'status',f.status, ...
          'raw_sha256',paths.observation,'recipe_sha256',iscat047.file_sha256(recipeFile));
        fid=fopen(fullfile(acqDir,'acq_record.json'),'w'); fwrite(fid,jsonencode(rec)); fclose(fid);
      end
      Derr=rec.D_fit-D; perr=hypot(rec.x_fit-8.45,rec.y_fit+24.05)/65;
      res{end+1}=struct('case',tid,'trial',trial,'D_fit',rec.D_fit,'D_err',Derr, ...
        'z_fit',rec.z_fit,'z_err',rec.z_fit-z,'pos_err_px',perr,'status',rec.status, ...
        'at_boundary',any(abs([rec.D_fit-D,rec.z_fit-z])<1e-9)||any(abs([rec.x_fit,rec.y_fit])==650)); %#ok<AGROW>
    end
    C=[res{end-nPerCond+1:end}];
    de=[C.D_err]; pe=[C.pos_err_px];
    fprintf('[060:r4] %s: n=%d Bias=%+.3f RMSE=%.3f Std=%.3f posMax=%.3f bad=%d\n', ...
      tid,numel(de),mean(de),sqrt(mean(de.^2)),std(de,1),max(pe),nnz(~strcmp({C.status},'CONVERGED')));
    writetable(struct2table([res{:}]),fullfile(outRoot,'r4_camera_per_trial.csv'));
  end
end
writetable(struct2table([res{:}]),fullfile(outRoot,'r4_camera_per_trial.csv'));
fprintf('[060:r4] complete: %d acquisitions\n',numel(res));
end




