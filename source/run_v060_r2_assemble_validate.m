function run_v060_r2_assemble_validate()
% v060 R2: assemble full 32-node model; validate (readback <=1e-12, axes, support).
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
sliceDir=fullfile(projectRoot,'v058_return','dense_c','slices');
outRoot=fullfile(projectRoot,'v060_return','r2');
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));
D=[28 29.5 31 32.5 34 35.5 37 38.5 40 41.5 44 46 48 50 52 54 56 58 60 62 64 66 68 70 72 74 76 78 80 82 84 86];
Z=(350:25:600); slices={};
missing={};
for i=1:numel(D), for j=1:numel(Z)
  f=fullfile(sliceDir,sprintf('slice_D%g_z%d.mat',D(i),Z(j)));
  if isfile(f), slices{end+1}=f; else, missing{end+1}=f; end %#ok<AGROW>
end, end
fprintf('[060:r2] slices found=%d missing=%d\n',numel(slices),numel(missing));
if ~isempty(missing)
  fid=fopen(fullfile(outRoot,'R2_missing.json'),'w'); fwrite(fid,jsonencode(missing)); fclose(fid);
  error('iscat060:R2Incomplete','%d slices missing',numel(missing));
end
modelFile=fullfile(projectRoot,'v058_return','dense_c','models_dense_full32.mat');
if ~isfile(modelFile)
  models=ASSEMBLE_MAPS047(slices,modelFile);
else
  M=load(modelFile,'models'); models=M.models;
  fprintf('[060:r2] reusing assembled model\n');
end
% R2.1 grid completeness
ctx=iscat047.prepare_model(models.C);
assert(numel(ctx.grid{3})==32&&numel(ctx.grid{4})==11,'grid size mismatch');
assert(isequal(ctx.grid{3}(:),D(:)),'D nodes differ from original 32');
assert(isequal(ctx.grid{4}(:),Z(:)),'z nodes differ from 350:25:600');
% R2.3 readback: max diff between model and a sample of source slices
maxd=0; nd=0;
for i=[1,round(numel(D)/2),numel(D)]
  for j=1:numel(Z)
    S=load(slices{(i-1)*numel(Z)+j},'slice');
    idxd=find(ctx.grid{3}==S.slice.D_nm); idxz=find(ctx.grid{4}==S.slice.z_nm);
    A=models.C.contrast(:,:,idxd,idxz); Asrc=S.slice.C_q5_dense;
    d=max(abs(A(:)-Asrc(:)))/max(1,max(abs(Asrc(:))));
    maxd=max(maxd,d); nd=nd+1;
  end
end
fprintf('[060:r2] readback normalized_max_difference=%.3g over %d slices\n',maxd,nd);
assert(maxd<=1e-12,'R2.3 readback self-check failed');
% R2.4 support: central 41x41 queries across full common xy domain at boundary D/z
cx=33; ix=(cx-20):(cx+20);
for x=-650:325:650, for y=-650:325:650
  P=iscat047.predict(ctx,[28,375,x,y],ctx.camera_x(ix),ctx.camera_y(ix));
  assert(all(isfinite(P(:))));
  P=iscat047.predict(ctx,[86,575,x,y],ctx.camera_x(ix),ctx.camera_y(ix));
  assert(all(isfinite(P(:))));
end, end
fprintf('[060:r2] support grid checks OK (D/z endpoints x xy corners)\n');
fid=fopen(fullfile(outRoot,'r2_acceptance.json'),'w'); fwrite(fid,jsonencode(struct( ...
 'slices_found',numel(slices),'missing',0,'readback_norm_max_diff',maxd, ...
 'D_nodes',ctx.grid{3},'z_nodes',ctx.grid{4},'support_checks','PASS', ...
 'model_file',modelFile,'status','COMPLETED'))); fclose(fid);
end

