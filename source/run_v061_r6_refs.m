function run_v061_r6_refs(outRoot)
% v061 R6: 10 fine 1444/rule3 references for the pre-registered blind conditions.
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v042_handoff\iSCAT_v042_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
if nargin<1, outRoot=fullfile(projectRoot,'v061_return','r6_refs'); end
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));
% pre-registered conditions [D zf x y] from 00_Codex_v061 contract
B=[28.9 381.7 -617.1 593.7; 33.2 559.3 611.3 -601.9; 39.1 421.7 -333.7 287.9;
   43.3 573.1 271.3 -419.7; 49.1 468.3 12.3 -27.9; 57.3 394.7 -451.1 -137.3;
   63.1 539.1 145.7 503.1; 71.3 445.9 437.9 -299.3; 79.1 506.3 -205.7 167.9;
   85.1 484.7 581.3 621.7];
c=iscat_config('camera');
c.numerics.mesh_request=1444; c.numerics.ntheta=100; c.numerics.nphi=151;
c.numerics.bessel_table_points=4001;
for i=1:size(B,1)
  D=B(i,1); zf=B(i,2); xy=B(i,3:4); sid=sprintf('B%02d_D%.1f',i,D);
  sFile=fullfile(outRoot,[sid '_s_fine1444.mat']);
  if isfile(sFile), fprintf('[061:r6] %s cache hit\n',sid); continue; end
  ci=c; ci.particle.diameter_nm=D; ci.particle.xy_nm=xy; ci.focus_nm=[0,0,zf];
  t0=tic; s=build_system(ci); s.solve_seconds=toc(t0);
  save(sFile,'s','-v7.3');
  % truth renders at the registered zf (particle at registered xy)
  d=fullfile(outRoot,sprintf('%s_z%d_truth',sid,round(zf))); %#ok<NASGU>
  fid=fopen(fullfile(outRoot,[sid '_solve_record.json']),'w');
  fwrite(fid,jsonencode(struct('D',D,'zf',zf,'xy',xy,'solve_seconds',s.solve_seconds, ...
    'mesh_vertices',s.mesh_vertices))); fclose(fid);
  fprintf('[061:r6] %s solve %.1fs mesh=%d\n',sid,s.solve_seconds,s.mesh_vertices);
end
fprintf('[061:r6] all 10 references done %s\n',datestr(now,'HH:MM:SS'));
end
