function run_v062_hook_capture()
% P0: capture real duffy1 eval2 sizes on the 1444 rule7 path; stop before OOM.
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,fullfile(projectRoot,'third_party_candidates','nanobem-iscat056-diaghooks'));
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v051_handoff\iSCAT_v051_Codex_handoff\matlab');
outRoot=fullfile(projectRoot,'v062_return','p0_hook'); if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'hook_capture.log')); cl=onCleanup(@() diary('off'));
c=iscat_config('camera'); c.particle.diameter_nm=35.5; c.particle.xy_nm=[0,0];
c.numerics.mesh_request=1444; c.numerics.ntheta=100; c.numerics.nphi=151; c.numerics.bessel_table_points=4001;
[r7m,~]=iscat051.rules_limited(7,1200);
p=trisphere(1444,35.5); p.verts=p.verts+[0,0,5+35.5/2];
mats=[Material(1.5^2,1),Material(1.33^2,1),Material(epstable('gold.dat'),1)];
tau=BoundaryEdge(mats,p,[3,2]); layer=stratified.layerstructure(mats(1:2),0);
k0=2*pi/520;
try
  bem=stratified.bemsolver(tau,layer,'order',[],'rules',r7m,'memax',1e6);
  g=fill(b.green,k0);
  fprintf('[062:hook] fill completed (unexpected)\n');
catch ME
  fprintf('[062:hook] stopped as designed: %s @%s\n',ME.message,ME.stack(1).name);
  fid=fopen(fullfile(outRoot,'hook_capture_result.json'),'w');
  fwrite(fid,jsonencode(struct('message',ME.message,'stack_top',ME.stack(1).name)));
  fclose(fid);
end
end
