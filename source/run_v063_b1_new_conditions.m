function run_v063_b1_new_conditions(outRoot)
% v063 B1: true-param forward (2%) + noiseless fits for B01-B10 (zero new BEM).
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v042_handoff\iSCAT_v042_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
if nargin<1, outRoot=fullfile(projectRoot,'v063_return','b1'); end
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));
M=load(fullfile(projectRoot,'v058_return','dense_c','models_dense_full32.mat'),'models'); models=M.models;
ctx=iscat047.prepare_model(models.C);
refs=fullfile(projectRoot,'v061_return','r6_refs');
B=[28.9 381.7 -617.1 593.7; 33.2 559.3 611.3 -601.9; 39.1 421.7 -333.7 287.9;
   43.3 573.1 271.3 -419.7; 49.1 468.3 12.3 -27.9; 57.3 394.7 -451.1 -137.3;
   63.1 539.1 145.7 503.1; 71.3 445.9 437.9 -299.3; 79.1 506.3 -205.7 167.9;
   85.1 484.7 581.3 621.7];
opts=struct('D_bounds',[28,86],'z_bounds',[375,575],'mask_half',20,'center_bound_pixels',10);
cx=33; ix=(cx-20):(cx+20);
res={};
for i=1:size(B,1)
  D=B(i,1); zf=B(i,2); xy=B(i,3:4); sid=sprintf('B%02d_D%.1f',i,D);
  % forward: dense model at true params vs fine truth render
  tdir=fullfile(refs,sprintf('%s_z%d_truth',sid,round(zf)),'truth_private.mat');
  L=load(tdir,'truth'); O=L.truth.C; Oroi=O(ix,ix);
  Pt=iscat047.predict(ctx,[D,zf,xy(1),xy(2)],L.truth.x_nm(ix),L.truth.y_nm(ix));
  num=norm(Pt(:)-Oroi(:)); den=norm(Oroi(:)); rel=num/den;
  % noiseless fit
  f=iscat047.fit(models.C,O,opts);
  Derr=f.theta(1)-D; zerr=f.theta(2)-zf;
  perr=hypot(f.theta(3)-xy(1),f.theta(4)-xy(2))/65;
  atb=(abs(f.theta(1)-28)<1e-9)||(abs(f.theta(1)-86)<1e-9)|| ...
    (abs(f.theta(2)-375)<1e-9)||(abs(f.theta(2)-575)<1e-9)|| ...
    (abs(abs(f.theta(3))-650)<1e-9)||(abs(abs(f.theta(4))-650)<1e-9);
  gate=(abs(Derr)<2)&&(perr<0.5)&&(rel<0.02);
  res{end+1}=struct('cond',sid,'D',D,'zf',zf,'x',xy(1),'y',xy(2), ...
    'fwd_num',num,'fwd_den',den,'fwd_relL2',rel,'fwd_gate2pct',rel<0.02, ...
    'fit_D',f.theta(1),'D_err',Derr,'z_err',zerr,'pos_err_px',perr, ...
    'fit_status',f.status,'at_bound',atb,'all_gates',gate, ...
    'data_sse',f.data_sse,'null_sse',f.null_sse); %#ok<AGROW>
  fprintf('[063:b1] %s fwd=%.4f | D=%+.2f z=%+.1f pos=%.3f atb=%d gates=%d\n', ...
    sid,rel,Derr,zerr,perr,atb,gate);
end
writetable(struct2table([res{:}]),fullfile(outRoot,'r6_new_conditions_forward.csv'));
writetable(struct2table([res{:}]),fullfile(outRoot,'r6_new_conditions_noiseless.csv'));
end
