function run_v060_r3_dense_ten(outRoot)
% v060 R3: ten-condition fixed-axis forward (2%) + noiseless dense-model fits.
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v042_handoff\iSCAT_v042_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
if nargin<1, outRoot=fullfile(projectRoot,'v060_return','r3'); end
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));
M=load(fullfile(projectRoot,'v058_return','dense_c','models_dense_full32.mat'),'models');
M=load(fullfile(projectRoot,'v058_return','dense_c','models_dense_full32.mat'),'models'); models=M.models;
ctx=iscat047.prepare_model(models.C);
truthT='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v056_return\s5_truth';
cx=33; ix=(cx-20):(cx+20);
opts=struct('D_bounds',[28,86],'z_bounds',[375,575],'mask_half',20,'center_bound_pixels',10);
res={};
for D=[35,45,55,65,85]
  for z=[450,550]
    tid=sprintf('D%d_z%d',D,z);
  end
end
for D=[35,45,55,65,85]
  for z=[450,550]
    tid=sprintf('D%d_z%d',D,z);
    L=load(fullfile(truthT,sprintf('D%d_z%d_truth',D,z),'truth_private.mat'),'truth');
    O=L.truth.C; Oroi=O(ix,ix);
    % fixed-axis forward at TRUE params
    Pt=iscat047.predict(ctx,[D,z,8.45,-24.05],L.truth.x_nm(ix),L.truth.y_nm(ix));
    num=norm(Pt(:)-Oroi(:)); den=norm(Oroi(:)); rel=num/den;
    % noiseless fit (no truth in init/bounds)
    f=iscat047.fit(models.C,O,opts);
    Derr=f.theta(1)-D; zerr=f.theta(2)-z;
    perr=hypot(f.theta(3)-8.45,f.theta(4)-(-24.05))/65;
    at_bound=(abs(f.theta(1)-28)<1e-9)||(abs(f.theta(1)-86)<1e-9)|| ...
      (abs(f.theta(2)-375)<1e-9)||(abs(f.theta(2)-575)<1e-9)|| ...
      (abs(abs(f.theta(3))-650)<1e-9)||(abs(abs(f.theta(4))-650)<1e-9);
    gate=(abs(Derr)<2)&&(perr<0.5)&&(rel<0.02);
    res{end+1}=struct('case',tid,'fwd_num',num,'fwd_den',den,'fwd_relL2',rel, ...
      'fwd_gate2pct',rel<0.02,'fit_D',f.theta(1),'fit_z',f.theta(2), ...
      'fit_x',f.theta(3),'fit_y',f.theta(4),'D_err',Derr,'z_err',zerr, ...
      'pos_err_px',perr,'status',f.status,'exitflag',f.best_exitflag, ...
      'at_bound',at_bound,'all_gates_pass',gate,'data_sse',f.data_sse, ...
      'null_sse',f.null_sse,'starts',numel(f.coarse_selected_rows), ...
      'total_evals',f.total_optimizer_evaluations,'elapsed_s',f.elapsed_s); %#ok<AGROW>
    fprintf('[060:r3] %s fwd=%.4f | fit D=%+.2f z=%+.1f pos=%.3f %s gate=%d\n', ...
      tid,rel,Derr,zerr,perr,f.status,gate);
  end
end
writetable(struct2table([res{:}]),fullfile(outRoot,'r3_ten_conditions.csv'));
end


