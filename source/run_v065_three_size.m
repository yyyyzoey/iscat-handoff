function run_v065_three_size(outRoot)
% v065: 30/100nm homogeneous + layered, fixed Mie reference, signed response table.
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v042_handoff\iSCAT_v042_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
if nargin<1, outRoot=fullfile(projectRoot,'v065_return'); end
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));
nr=2.349; kap=0.083; nP=complex(nr,kap);
Z=(350:25:600); sizes=[30,60,100];
% Material guard
assert(abs(nr-2.349)<=1e-12 && abs(kap-0.083)<=1e-12);
nParticle=complex(nr,kap); epsP=nParticle^2;
assert(imag(nParticle)>0,'ABSORBING_BECAME_LOSSLESS');
% Mie reference (correct spherical Bessel via half-integer recurrence)
for D=sizes
  r=mie_ref(nP,D,520,1.33,12);
  fprintf('[065:mie] D=%g Csca=%.8g Cext=%.8g Cabs=%.8g\n',D,r.Csca,r.Cext,r.Cabs);
end
% BEM: homogeneous 1444/rule3 per size (M2) + layered 576/1444 per size (M3)
for D=sizes
  sid=sprintf('D%d',D);
  for mesh=[1444]
    tag='homog';
    f1=fullfile(outRoot,sprintf('%s_homog_%d.mat',sid,mesh));
    if isfile(f1), fprintf('[065] %s %s mesh=%d cache hit\n',sid,tag,mesh); continue; end
    c=iscat_config('camera');
    c.particle.diameter_nm=D; c.particle.xy_nm=[0,0];
    c.particle.material='constant_index'; c.particle.n_complex=nP;
    c.numerics.mesh_request=mesh;
    if mesh==576, c.numerics.ntheta=50; c.numerics.nphi=51; c.numerics.bessel_table_points=2001;
    else, c.numerics.ntheta=100; c.numerics.nphi=151; c.numerics.bessel_table_points=4001; end
    fprintf('[065] %s %s mesh=%d BEM start\n',sid,tag,mesh);
    t0=tic; s=build_system(c); s.solve_seconds=toc(t0);
    save(f1,'s','-v7.3');
    fprintf('[065] %s %s mesh=%d solve %.1fs\n',sid,tag,mesh,s.solve_seconds);
  end
  % layered: prod 576 + fine 1444
  for mesh=[576,1444]
    tag='layered';
    f2=fullfile(outRoot,sprintf('%s_s_%d.mat',sid,mesh));
    if isfile(f2), fprintf('[065] %s %s mesh=%d cache hit\n',sid,tag,mesh); continue; end
    c=iscat_config('camera');
    c.particle.diameter_nm=D; c.particle.xy_nm=[0,0];
    c.particle.material='constant_index'; c.particle.n_complex=nP;
    c.numerics.mesh_request=mesh;
    if mesh==576, c.numerics.ntheta=50; c.numerics.nphi=51; c.numerics.bessel_table_points=2001;
    else, c.numerics.ntheta=100; c.numerics.nphi=151; c.numerics.bessel_table_points=4001; end
    fprintf('[065] %s layered mesh=%d BEM start\n',sid,mesh);
    t0=tic; s=build_system(c); s.solve_seconds=toc(t0);
    save(f2,'s','-v7.3');
    fprintf('[065] %s layered mesh=%d solve %.1fs\n',sid,mesh,s.solve_seconds);
  end
end
% Render all sizes, all z, both prod and fine
cx=33; ix=(cx-20):(cx+20);
fwd={};
for D=sizes
  sid=sprintf('D%d',D);
  for zf=[450,550]
    % prod 576
    sp=load(fullfile(outRoot,sprintf('%s_s_576.mat',sid)),'s'); sp=sp.s;
    cp=sp.cfg; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
    rp=render_system(sp,cp); Cp=rp.contrast;
    % fine 1444
    sf=load(fullfile(outRoot,sprintf('%s_s_1444.mat',sid)),'s'); sf=sf.s;
    cf=sf.cfg; cf.focus_nm=[0,0,zf]; cf.sampling.subpixels=5;
    rf=render_system(sf,cf); Cf=rf.contrast;
    % compare
    rel=norm(Cp(ix,ix)-Cf(ix,ix))/norm(Cf(ix,ix));
    fwd{end+1}=struct('D',D,'zf',zf,'relL2_prod_vs_fine',rel,'gate2pct',rel<0.02); %#ok<AGROW>
    fprintf('[065:fwd] D=%g zf=%d prod-vs-fine relL2=%.4f gate=%d\n',D,zf,rel,rel<0.02);
  end
end
writetable(struct2table([fwd{:}]),fullfile(outRoot,'three_size_forward.csv'));
fprintf('[065] all forward comparisons done\n');
end
function r=mie_ref(np_,D,lam,nh,lmax)
k0=2*pi/lam; k1=k0*np_; k2=k0*nh;
z1=k1*D/2; z2=k2*D/2; Z1=1/np_; Z2=1/nh;
ell=1:lmax;
j1=arrayfun(@(l)sqrt(pi/(2*z1))*besselj(l+0.5,z1),ell);
j2=arrayfun(@(l)sqrt(pi/(2*z2))*besselj(l+0.5,z2),ell);
y2=arrayfun(@(l)sqrt(pi/(2*z2))*bessely(l+0.5,z2),ell);
h2=j2+1i*y2;
d1=arrayfun(@(l)z1*sqrt(pi/(2*z1))*besselj(l-0.5,z1)-l*j1(l),ell);
d2=arrayfun(@(l)z2*sqrt(pi/(2*z2))*besselj(l-0.5,z2)-l*j2(l),ell);
dh2=arrayfun(@(l)z2*sqrt(pi/(2*z2))*besselj(l-0.5,z2)+z2*1i*sqrt(pi/(2*z2))*bessely(l-0.5,z2)-l*h2(l),ell);
a=(Z2*z1*j1.*d2-Z1*z2*j2.*d1)./(Z2*z1*j1.*dh2-Z1*z2*h2.*d1);
b=(Z2*z2*j2.*d1-Z1*z1*j1.*d2)./(Z2*z2*h2.*d1-Z1*z1*j1.*dh2);
r.Csca=2*pi/k2^2*sum((2*ell+1).*(abs(a).^2+abs(b).^2));
r.Cext=2*pi/k2^2*sum((2*ell+1).*real(a+b));
r.Cabs=r.Cext-r.Csca;
end
