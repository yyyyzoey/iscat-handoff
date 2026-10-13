function run_v077_CCD(outRoot, v075Root, v074Root)
% v077 C: proper odd/even derivatives (3-state), holdout semantics fix, T10 fix.
% v077 D: 276-pair identifiability from v076 corrected C400 maps.
if nargin<3||isempty(v074Root), v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<2||isempty(v075Root), v075Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v077_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'));
% ---------- C: proper odd/even (3 distinct states) ----------
of=fopen(fullfile(tabDir,'v077_even_odd_derivatives.csv'),'w');
fprintf(of,'D_nm,zf_nm,pixel_row,pixel_col,a_nm,I_minus_a,I_0,I_plus_a,odd_half,even_increment,Iprime_central,Isecond_central,recon_err,note\n');
a=5;
for D=[30 60 100]
  for zf=450
    v75c=fullfile(projectRoot,'v075_return','numeric','render_cache');
    pk=position_key(D,zf,-a);
    AmT=load(fullfile(v75c,[pk '.mat'])); Am=AmT.rh;
    A0=load(fullfile(projectRoot,'v074_return','numeric','render_cache',sprintf('D%d_zf%g_x%+g.mat',D,zf,0)),'a');
    pkp=position_key(D,zf,a);
    ApT=load(fullfile(v75c,[pkp '.mat'])); Ap=ApT.rh;
    q=5; i0=61;
    Itm=reshape(sum(abs(Am.Eref+Am.Es).^2,3),325,325);
    It0=reshape(sum(abs(A0.a.Eref+A0.a.Es).^2,3),325,325);
    Itp=reshape(sum(abs(Ap.Eref+Ap.Es).^2,3),325,325);
    Im=pixel_mean(Itm(i0:i0+204,i0:i0+204),q); I0p=pixel_mean(It0(i0:i0+204,i0:i0+204),q); Ip=pixel_mean(Itp(i0:i0+204,i0:i0+204),q);
    for pr=[21 19 23 18 24]
      for pc=[21 26 16]
        Imv=Im(pr,pc); I0v=I0p(pr,pc); Ipv=Ip(pr,pc);
        odd_half=(Ipv-Imv)/2; even_inc=(Ipv+Imv)/2-I0v;
        Iprim=(Ipv-Imv)/(2*a); Isec=(Ipv-2*I0v+Imv)/(a^2);
        recon=I0v+odd_half+even_inc;
        rerr=abs(recon-I0v)/max(abs(I0v),realmin);
        fprintf(of,'%d,%g,%d,%d,%g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%s\n', ...
          D,zf,pr,pc,a,Imv,I0v,Ipv,odd_half,even_inc,Iprim,Isec,rerr, ...
          'three distinct physical states; recon=I0+odd+even');
      end
    end
  end
end
fclose(of);
% ---------- T10 fix: proper 39nm offset negative test ----------
A0=load(fullfile(v074Root,'numeric','render_cache','D60_zf450_x+0.mat'),'a');
q=5; i0c=61; i0leg=64;
It0=reshape(sum(abs(A0.a.Eref+A0.a.Es).^2,3),325,325);
C0=pixel_mean(It0(i0c:i0c+204,i0c:i0c+204),q);
Cleg=pixel_mean(It0(i0leg:i0leg+204,i0leg:i0leg+204),q);
d39=max(abs(C0(:)-Cleg(:)));
tf=fopen(fullfile(tabDir,'v077_holdout_camera_roi_semantics_fixed.csv'),'w');
fprintf(tf,'D_nm,zf_nm,dx_nm,Itot_roi_relL2,contrast_roi_relL2,Ccenter_direct,Ccenter_interp,Sarea_nm2_direct,Sarea_nm2_interp,Sarea_signedDelta_nm2,Sarea_absDelta_nm2,legacy39nm_maxdiff,note\n');
% holdout camera ROI with proper semantics
H=load(fullfile(v075Root,'numeric','v075_holdout_data.mat'));
fn=fieldnames(H);
for k=1:numel(fn)
  rec=H.(fn{k});
  tok=regexp(fn{k},'D(\d+)_ZF(\d+)_X([MP])(\d+)','tokens','once');
  D=str2double(tok{1}); zf=str2double(tok{2}); dxpm=str2double(tok{4});
  dx=dxpm/1000; if strcmp(tok{3},'M'), dx=-dx; end
  Ed=rec.Es_direct; Ei=rec.Es_interp; Er=rec.Eref;
  ItD=sum(abs(Er+Ed).^2,3); ItI=sum(abs(Er+Ei).^2,3);
  I0=sum(abs(Er).^2,3);
  IsD=sum(abs(Ed).^2,3); IsI=sum(abs(Ei).^2,3);
  IiD=2*real(sum(conj(Er).*Ed,3)); IiI=2*real(sum(conj(Er).*Ei,3));
  CD=(pixel_mean(ItD(i0c:i0c+204,i0c:i0c+204),q)-pixel_mean(I0(i0c:i0c+204,i0c:i0c+204),q))./pixel_mean(I0(i0c:i0c+204,i0c:i0c+204),q);
  CI=(pixel_mean(ItI(i0c:i0c+204,i0c:i0c+204),q)-pixel_mean(I0(i0c:i0c+204,i0c:i0c+204),q))./pixel_mean(I0(i0c:i0c+204,i0c:i0c+204),q);
  relIt=norm(ItI(i0c:i0c+204,i0c:i0c+204)-ItD(i0c:i0c+204,i0c:i0c+204),'fro')/max(norm(ItD(i0c:i0c+204,i0c:i0c+204),'fro'),realmin);
  relC=norm(CI(:)-CD(:))/max(norm(CD(:)),realmin);
  cD=CD(21,21); cI=CI(21,21);
  sD=4225*sum(CD(:)); sI=4225*sum(CI(:));
  fprintf(tf,'%d,%g,%g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,CAMERA_ROI_41x41_correct_centre; Sarea=4225*sum(C)\n', ...
    D,zf,dx,relIt,relC,cD,cI,sD,sI,sI-sD,abs(sI-sD),d39);
end
fprintf(tf,'0,0,0,0,0,0,0,0,0,0,0,%.17g,T10_proper_39nm_negative_test_from_fine_64:268_vs_61:265\n',d39);
fclose(tf);
% ---------- D: 276-pair identifiability ----------
R=load(fullfile(projectRoot,'v076_return','numeric','v076_dynamic_center_corrected.mat'));
fn=fieldnames(R);
states=struct();
for i=1:numel(fn)
  f=R.(fn{i});
  if ~isfield(f,'D'), continue; end
  key=matlab.lang.makeValidName(fn{i});
  states.(key)=struct('C400',f.C400,'D',f.D,'zf',f.zf,'amp',f.amp,'ttype',f.ttype,'name',fn{i});
end
sn=fieldnames(states); nS=numel(sn);
idf=fopen(fullfile(tabDir,'v077_identifiability_276pairs.csv'),'w');
fprintf(idf,'pair_id,state_i,state_j,D_i,zf_i,a_i,type_i,D_j,zf_j,a_j,type_j,changed,complex_symmetric_relL2,abs_symmetric_relL2,note\n');
pid=0;
for i=1:nS
  for j2=i+1:nS
    si=states.(sn{i}); sj=states.(sn{j2});
    chg='';
    if si.D~=sj.D, chg=[chg '+D']; end
    if si.zf~=sj.zf, chg=[chg '+zf']; end
    if si.amp~=sj.amp, chg=[chg '+a']; end
    if ~strcmp(si.ttype,sj.ttype), chg=[chg '+type']; end
    nC=norm(double(si.C400(:))-double(sj.C400(:)));
    dC=(norm(double(si.C400(:)))+norm(double(sj.C400(:))))/2;
    symC=nC/max(dC,realmin);
    ai=abs(si.C400(:)); aj=abs(sj.C400(:));
    nA=norm(ai-aj); dA=(norm(ai)+norm(aj))/2;
    symA=nA/max(dA,realmin);
    pid=pid+1;
    fprintf(idf,'%d,%s,%s,%d,%g,%g,%s,%d,%g,%g,%s,%s,%.17g,%.17g,%s\n', ...
      pid,sn{i},sn{j2},si.D,si.zf,si.amp,si.ttype,sj.D,sj.zf,sj.amp,sj.ttype,chg,symC,symA, ...
      'symmetric normalisation; no arbitrary fitting; PRESCRIBED trajectories');
  end
end
fclose(idf);
fprintf('[077CCD] done: odd/even + T10 + holdout semantics + %d identifiability pairs\n',pid);
end




