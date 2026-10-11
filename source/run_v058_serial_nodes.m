function run_v058_serial_nodes()
% v058: serial completion of the remaining 30 D nodes (solve + BUILD_SLICE047).
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v042_handoff\iSCAT_v042_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
outRoot=fullfile(projectRoot,'v058_return','dense_c');
if ~isfolder(fullfile(outRoot,'slices')), mkdir(fullfile(outRoot,'slices')); end
D=(28:1.5:42); D=[D,48:2:86]; % all 32 original nodes minus 44/46 handled below
allNodes=[28 29.5 31 32.5 34 35.5 37 38.5 40 41.5 44 46 48 50 52 54 56 58 60 62 64 66 68 70 72 74 76 78 80 82 84 86];
Z=(350:25:600);
c=iscat_config('camera');
c.numerics.mesh_request=576; c.numerics.ntheta=50; c.numerics.nphi=51;
c.numerics.bessel_table_points=2001;
for id=1:numel(allNodes)
  D=allNodes(id); sid=sprintf('D%d',D);
  sFile=fullfile(outRoot,sprintf('%s_s_prod576.mat',sid));
  if ~isfile(sFile)
    ci=c; ci.particle.diameter_nm=D; ci.particle.xy_nm=[0,0]; ci.focus_nm=[0,0,450];
    t0=tic; s=build_system(ci); s.solve_seconds=toc(t0);
    save(sFile,'s','-v7.3');
    fid=fopen(fullfile(outRoot,[sid '_solve_record.json']),'w');
    fwrite(fid,jsonencode(struct('D',D,'solve_seconds',s.solve_seconds,'mesh_vertices',s.mesh_vertices))); fclose(fid);
    fprintf('[058:serial] %s solve %.1fs\n',sid,s.solve_seconds);
  else
    L=load(sFile,'s'); fprintf('[058:serial] %s cache hit\n',sid);
  end
  for j=1:numel(Z)
    z=Z(j);
    sliceFile=fullfile(outRoot,'slices',sprintf('slice_%s_z%d.mat',sid,z));
    if isfile(sliceFile), continue; end
    BUILD_SLICE047(sFile,z,sliceFile);
  end
  fprintf('[058:serial] %s slices done %s\n',sid,datestr(now,'HH:MM:SS'));
end
fprintf('[058:serial] ALL 32 NODES COMPLETE %s\n',datestr(now,'HH:MM:SS'));
end
