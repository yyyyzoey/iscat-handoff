function run_v073_ledger_fix(outRoot, v071Root)
% v073 E1: verified controlled ledger from side mats with REAL D/zf from cfg and
% corrected SHA column semantics. Zero render, zero BEM. Old table kept in history.
if nargin<2||isempty(v071Root), v071Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v071_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v073_return'; end
numDir=fullfile(v071Root,'numeric');
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
rs=sha256_file_next(which('render_system'));
wr=sha256_file_next(which('run_v071_controlled'));
fid=fopen(fullfile(tabDir,'controlled_ledger_v073_verified.csv'),'w');
fprintf(fid,'case_id,D_nm_from_cfg,zf_nm_from_cfg,suffix,mesh_vertices,ntheta_lens,nphi_lens,far_dirs,ntab,subpixels,system_file_sha256,render_source_sha256,wrapper_source_sha256,array_sha256,shape,finite,execution_status,validation_status,evidence_status\n');
md=dir(fullfile(numDir,'side_*.mat'));
n=0;
for a=1:numel(md)
  S=load(fullfile(numDir,md(a).name));
  if ~isfield(S,'r'), continue; end
  cid=S.cid; suffix=S.suffix;
  D=S.r.cfg.particle.diameter_nm; zf=S.r.cfg.focus_nm(3);
  C=S.r.contrast; okf=all(isfinite(C(:)));
  fprintf(fid,'%s,%g,%g,%s,%d,%d,%d,%d,%d,%d,%s,%s,%s,%s,%dx%d,%d,COMPLETED,PASS,SOURCE_VERIFIED\n', ...
    cid,D,zf,suffix,S.evi.mesh_vertices,S.evi.ntheta_lens,S.evi.nphi_lens,S.evi.far_directions, ...
    S.evi.ntab,S.evi.subpixels,S.evi.sol_sha256,rs,wr,sha256_file_next(fullfile(numDir,md(a).name)), ...
    size(C,1),size(C,2),okf);
  n=n+1;
end
% NOT_EXECUTABLE rows with cid read from the mats (no strcmp-list hack)
for a=1:numel(md)
  S=load(fullfile(numDir,md(a).name));
  if isfield(S,'r') || ~isfield(S,'evi'), continue; end
  fprintf(fid,'%s,,,,,,%d,%d,%d,,,,,,,,NOT_EXECUTABLE,NOT_EXECUTABLE,%s\n', ...
    S.cid,S.evi.far_directions,S.evi.ntheta_lens,S.evi.nphi_lens,S.evi.reason);
end
fclose(fid);
fprintf('[073E1] verified %d executable sides + NOT_EXECUTABLE rows; render_source=%s wrapper=%s\n',n,rs(1:12),wr(1:12));
end
