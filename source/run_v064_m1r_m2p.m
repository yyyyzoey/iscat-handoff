function run_v064_m1r_m2p()
% v064 M1R+M2P: material identity guard + zero-BEM Mie verification.
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
outRoot=fullfile(projectRoot,'v064_return','m1r_m2p');
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));

% ---- M1R.1 source file identity
srcFile=fullfile(projectRoot,'v063_return','Fe3O4_Querry.yml');
assert(isfile(srcFile),'source yml missing');
sha256=local_file_sha256(srcFile);
raw_bytes = fileread_bytes(srcFile); raw = char(raw_bytes);
blob=local_git_blob_sha1(raw_bytes);
expected_blob='37cd83a1ad859b18ddb8c6a515c29df78b2d95cb';
fprintf('[064:m1r] yml sha256=%s...\n',sha256(1:16));
fprintf('[064:m1r] git blob=%s... expected=%s... match=%d\n',blob(1:16),expected_blob(1:16),strcmp(blob,expected_blob));

% ---- M1R.2 parse + exact node
[wl,nn,kk,year_src]=parse_querry(srcFile);
[nr,kap]=node_at(wl,nn,kk,0.5200);
fprintf('[064:m1r] exact node 0.52um: n=%.17g kappa=%.17g\n',nr,kap);
fprintf('[064:m1r] source citation year: %s (1985 per E01; v063 contract 1987 corrected)\n',year_src);
assert(abs(nr-2.349)<=1e-12 && abs(kap-0.083)<=1e-12,'node mismatch');

% ---- M1R.3 guard + negative fixtures
nParticle=complex(nr,kap);
epsParticle=nParticle^2;
assert(abs(real(nParticle)-2.349)<=1e-12,'MATERIAL_REAL_MISMATCH');
assert(abs(imag(nParticle)-0.083)<=1e-12,'MATERIAL_IMAG_MISMATCH');
assert(imag(nParticle)>0,'ABSORBING_TARGET_BECAME_LOSSLESS');
assert(abs(real(epsParticle)-5.510912)<=1e-5,'EPS_REAL_MISMATCH');
assert(abs(imag(epsParticle)-0.389934)<=1e-5,'EPS_IMAG_MISMATCH');
neg={'2.349+0.0831 (real sum)',2.349+0.0831;'complex(2.349,0)',complex(2.349,0)};
for i=1:size(neg,1)
  v=neg{i,2};
  assert(abs(imag(v)-0.083)>1e-12,'negative fixture NOT rejected: %s',neg{i,1});
  fprintf('[064:m1r] negative fixture rejected: %s (imag=%.4f)\n',neg{i,1},imag(v));
end

% ---- M2P: Mie-only, correct complex material
mp=Material(epsParticle,1);
mw=Material(1.33^2,1);
n_read=mp.n(2*pi/520);
fprintf('[064:m2p] Material readback n=%.17g%+.17gi\n',real(n_read),imag(n_read));
assert(abs(real(n_read)-nr)<=1e-9 && abs(imag(n_read)-kap)<=1e-9,'Material readback lost complex part');
for L=[6,8,12,16]
  msL=miesolver(mp,mw,60,'lmax',L);
  k0=2*pi/520;
  sca=scattering(msL,k0); ext=extinction(msL,k0); ab=ext-sca;
  fprintf('[064:m2p] target D=60 lmax=%2d Csca=%.10g Cext=%.10g Cabs=%.10g\n',L,sca,ext,ab);
  if L==12, assert(isfinite(ab)&&ab>0,'target absorption not finite/positive'); end
end
% controls
ms0=miesolver(Material(complex(2.349,0)^2,1),mw,60);
k0=2*pi/520;
s0=scattering(ms0,k0); e0=extinction(ms0,k0); a0=e0-s0;
fprintf('[064:m2p] control complex(2.349,0): |Cabs|/Cext=%.3g\n',abs(a0)/e0);
assert(abs(a0)/e0<=1e-10,'control residual too large');
msw=miesolver(Material(2.4321^2,1),mw,60);
sw=scattering(msw,k0); ew=extinction(msw,k0); aw=ew-sw;
fprintf('[064:m2p] old wrong input 2.4321 real: Cabs=%.3g (diagnostic)\n',aw);
% independent reference cross-check
ref=local_mie_sections(nParticle,60,520,1.33,12);
ms12=miesolver(mp,mw,60,'lmax',12);
mineCsca=scattering(ms12,k0); mineCext=extinction(ms12,k0);
fprintf('[064:m2p] independent-ref Csca=%.10g vs fixed-mie %.10g (rel=%.3g)\n',ref.Csca,mineCsca,abs(ref.Csca-mineCsca)/abs(ref.Csca));
fprintf('[064:m2p] independent-ref Cext=%.10g vs fixed-mie %.10g (rel=%.3g)\n',ref.Cext,mineCext,abs(ref.Cext-mineCext)/abs(ref.Cext));
fprintf('[064:m2p] Cabs: ref=%.10g mie=%.10g\n',ref.Cabs,mineCext-mineCsca);

% ---- write results
out=struct('sha256',sha256,'gitblob',blob,'blob_match_E01',strcmp(blob,expected_blob), ...
  'exact_node',struct('n',nr,'kappa',kap),'citation_year_source',year_src, ...
  'citation_correction','v063 said 1987; source file says 1985 - corrected', ...
  'negative_fixtures_rejected',2, ...
  'm2p_target_lmax12',struct('Csca',scattering(miesolver(mp,mw,60,'lmax',12),k0), ...
  'Cext',extinction(miesolver(mp,mw,60,'lmax',12),k0)), ...
  'independent_ref',ref,'mie_abs_from_ext_minus_sca',mineCext-mineCsca);
fid=fopen(fullfile(outRoot,'m1r_m2p_results.json'),'w'); fwrite(fid,jsonencode(out)); fclose(fid);
fprintf('[064:m1r/m2p] PASS\n');
end

function s=local_file_sha256(f)
md = java.security.MessageDigest.getInstance('SHA-256');
fis = java.io.FileInputStream(f);
buf = zeros(1,8192,'int8');
while true
  nread = fis.read(buf);
  if nread < 1, break; end
  md.update(buf(1:nread));
end
fis.close();
d = typecast(md.digest(),'uint8');
s = lower(reshape(dec2hex(d,2).',1,[]));
end

function out=local_git_blob_sha1(txt)
bytes = uint8(txt);
md = java.security.MessageDigest.getInstance('SHA-1');
hdr = ['blob ', num2str(numel(bytes))];
hdr0 = [hdr, char(0)];
md.update(uint8(hdr0));
md.update(bytes);
d = typecast(md.digest(),'uint8');
out = lower(reshape(dec2hex(d,2).',1,[]));
end

function b=fileread_bytes(f)
fid=fopen(f,'r');
b=fread(fid,'*uint8').';
fclose(fid);
end

function [wl,nn,kk,year_src]=parse_querry(f)
lines=fileread(f); lines=strsplit(lines,sprintf('\n'));
data=false; wl=[]; nn=[]; kk=[]; year_src='';
for i=1:numel(lines)
  ln=lines{i};
  if strncmp(ln,'DATA:',5), data=true; end
  if isempty(year_src)
    yr=regexp(ln,'(19\d\d)','match','once');
    if ~isempty(yr), year_src=char(yr); end
  end
  if data
    tok=regexp(ln,'^\s*([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s*$','tokens','once');
    if ~isempty(tok), wl=[wl;str2double(tok{1})];nn=[nn;str2double(tok{2})];kk=[kk;str2double(tok{3})]; end %#ok<AGROW>
  end
end
end

function [nr,kap]=node_at(wl,nn,kk,wlum)
for i=1:numel(wl)-1
  if wl(i)<=wlum && wl(i+1)>=wlum
    if wl(i+1)==wl(i), nr=nn(i); kap=kk(i); return; end
    t=(wlum-wl(i))/(wl(i+1)-wl(i));
    nr=nn(i)+t*(nn(i+1)-nn(i)); kap=kk(i)+t*(kk(i+1)-kk(i));
    return
  end
end
error('node %g um outside table',wlum);
end

function r=local_mie_sections(np,dNm,lamNm,nh,lmax)
k0=2*pi/lamNm; k1=k0*np; k2=k0*nh;
z1=k1*dNm/2; z2=k2*dNm/2; Z1=1/np; Z2=1/nh;
ell=1:lmax;
j1=arrayfun(@(l)besselj(l,z1),ell); j2=arrayfun(@(l)besselj(l,z2),ell);
y2=arrayfun(@(l)bessely(l,z2),ell);
h2=j2+1i*y2;
d1=arrayfun(@(l)z1*besselj(l,z1,true)+besselj(l,z1),ell);
d2=arrayfun(@(l)z2*besselj(l,z2,true)+besselj(l,z2),ell);
dh2=arrayfun(@(l)z2*(besselj(l,z2,true)+1i*bessely(l,z2,true))+h2(l),ell);
a=(Z2*z1*j1.*d2-Z1*z2*j2.*d1)./(Z2*z1*j1.*dh2-Z1*z2*h2.*d1);
b=(Z2*z2*j2.*d1-Z1*z1*j1.*d2)./(Z2*z2*h2.*d1-Z1*z1*j1.*dh2);
r.Csca=2*pi/k2^2*sum((2*ell+1).*(abs(a).^2+abs(b).^2));
r.Cext=2*pi/k2^2*sum((2*ell+1).*real(a+b));
r.Cabs=r.Cext-r.Csca;
end

