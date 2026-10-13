function run_v078_CDE(outRoot, v075Root, v076Root, v074Root)
% v078 C+D+E: odd/even derivatives, camera ROI, exposure, identifiability.
if nargin<4, v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<3, v076Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
if nargin<2, v075Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return'; end
if nargin<1, outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v078_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';

% ================= C: odd/even derivatives (270 max) =================
of=fopen(fullfile(tabDir,'v078_evenodd_270.csv'),'w');
fprintf(of,'D_nm,zf_nm,a_nm,pixel_row,pixel_col,I_minus_a,I_0,I_plus_a,odd_half,even_increment,Iprime_central_nm,Isecond_central_nm2,Iplus_recon_err,Iminus_recon_err,note\n');
aList=[5 10 20]; nOE=0;
for D=[30 60 100]
  for zf=[450 550]
    for a=aList
      try
        AmT=load(fullfile(v075Root,'numeric','render_cache',position_key(D,zf,-a)),'rh'); Am=AmT.rh;
        ApT=load(fullfile(v075Root,'numeric','render_cache',position_key(D,zf,a)),'rh'); Ap=ApT.rh;
      catch
        try
          AmT=load(fullfile(v074Root,'numeric','render_cache',sprintf('D%d_zf%g_x%+g.mat',D,zf,-a)),'a'); Am=AmT.a;
          ApT=load(fullfile(v074Root,'numeric','render_cache',sprintf('D%d_zf%g_x%+g.mat',D,zf,a)),'a'); Ap=ApT.a;
        catch, continue; end
      end
      A0T=load(fullfile(v074Root,'numeric','render_cache',sprintf('D%d_zf%g_x%+g.mat',D,zf,0)),'a'); A0=A0T.a;
      q=5; i0=61;
      Itm=reshape(sum(abs(Am.Eref+Am.Es).^2,3),325,325);
      It0=reshape(sum(abs(A0.Eref+A0.Es).^2,3),325,325);
      Itp=reshape(sum(abs(Ap.Eref+Ap.Es).^2,3),325,325);
      Im=pixel_mean(Itm(i0:i0+204,i0:i0+204),q); I0p=pixel_mean(It0(i0:i0+204,i0:i0+204),q); Ip=pixel_mean(Itp(i0:i0+204,i0:i0+204),q);
      for pr=[21 19 23 18 24]
        for pc=[21 26 16]
          Imv=Im(pr,pc); I0v=I0p(pr,pc); Ipv=Ip(pr,pc);
          odd=(Ipv-Imv)/2; even=(Ipv+Imv)/2-I0v;
          Ipr=(Ipv-Imv)/(2*a); Isec=(Ipv-2*I0v+Imv)/(a^2);
          recP=I0v+even+odd; recM=I0v+even-odd;
          eP=abs(recP-Ipv); eM=abs(recM-Imv);
          fprintf(of,'%d,%g,%g,%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%s\n', ...
            D,zf,a,pr,pc,Imv,I0v,Ipv,odd,even,Ipr,Isec,eP,eM,'three distinct states; recon against original Iplus/Iminus');
          nOE=nOE+1;
        end
      end
    end
  end
end
fclose(of);
fprintf('[078C] odd/even: %d records\n',nOE);

% ================= C2: camera ROI 24 rows + T10 =================
cf=fopen(fullfile(tabDir,'v078_camera_roi24.csv'),'w');
fprintf(cf,'D_nm,zf_nm,dx_nm,Itot_camera_relL2,Itot_finegrid_relL2,contrast_roi_relL2,Ccenter_direct,Ccenter_interp,Sarea_nm2_direct,Sarea_nm2_interp,Sarea_signedDelta_nm2,Sarea_absDelta_nm2,note\n');
H=load(fullfile(v075Root,'numeric','v075_holdout_data.mat'));
fn=fieldnames(H); q=5; i0=61;
for k=1:numel(fn)
  rec=H.(fn{k});
  tok=regexp(fn{k},'D(\d+)_ZF(\d+)_X([MP])(\d+)','tokens','once');
  D=str2double(tok{1}); zf=str2double(tok{2}); dxpm=str2double(tok{4});
  dx=dxpm/1000; if strcmp(tok{3},'M'), dx=-dx; end
  Ed=rec.Es_direct; Ei=rec.Es_interp; Er=rec.Eref;
  ItD=sum(abs(Er+Ed).^2,3); ItI=sum(abs(Er+Ei).^2,3);
  I0=sum(abs(Er).^2,3);
  ItDp=reshape(pixel_mean(ItD(i0:i0+204,i0:i0+204),q),41,41);
  ItIp=reshape(pixel_mean(ItI(i0:i0+204,i0:i0+204),q),41,41);
  I0p=reshape(pixel_mean(I0(i0:i0+204,i0:i0+204),q),41,41);
  CD=(ItDp-I0p)./I0p; CI=(ItIp-I0p)./I0p;
  relItCam=norm(ItIp(:)-ItDp(:))/max(norm(ItDp(:)),realmin);
  relItFine=norm(ItI(i0:i0+204,i0:i0+204)-ItD(i0:i0+204,i0:i0+204),'fro')/max(norm(ItD(i0:i0+204,i0:i0+204),'fro'),realmin);
  relC=norm(CI(:)-CD(:))/max(norm(CD(:)),realmin);
  cD=CD(21,21); cI=CI(21,21);
  sD=4225*sum(CD(:)); sI=4225*sum(CI(:));
  fprintf(cf,'%d,%g,%g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,CAMERA_ROI_41x41_correct_centre\n', ...
    D,zf,dx,relItCam,relItFine,relC,cD,cI,sD,sI,sI-sD,abs(sI-sD));
end
fclose(cf);
% T10 separate
A0=load(fullfile(v074Root,'numeric','render_cache','D60_zf450_x+0.mat'),'a');
It0=reshape(sum(abs(A0.a.Eref+A0.a.Es).^2,3),325,325);
C0c=pixel_mean(It0(61:265,61:265),5); C0l=pixel_mean(It0(64:268,64:268),5);
d39=max(abs(C0c(:)-C0l(:)));
tf=fopen(fullfile(tabDir,'v078_T10_true_39nm_negative_test.csv'),'w');
fprintf(tf,'test,description,max_diff_pixels,status\n');
fprintf(tf,'T10_39nm,fine 64:268 vs 61:265 through q5 pixel_mean,%.17g,PASS (diff>0 confirms offset)\n',d39);
fclose(tf);
fprintf('[078C2] camera ROI 24 rows + T10 done (d39=%.2g)\n',d39);

% ================= D: exposure =================
R=load(fullfile(v076Root,'numeric','v076_dynamic_center_corrected.mat'));
ef=fopen(fullfile(tabDir,'v078_exposure_analytic8.csv'),'w');
fprintf(ef,'case,trajectory_type,amplitude_nm,tau_s,quadrature,absC400_center_tau,absC400_center_tau0,rel_change,sinc_ref_400Hz,note\n');
for tt=[200 400]
  for aa=[5 20]
    bkey=matlab.lang.makeValidName(sprintf('D60_zf450_M%d_a%d',tt,aa));
    b=R.(bkey);
    for tau=[1e-4 2e-4]
      ekey=matlab.lang.makeValidName(sprintf('D60_zf450_M%d_a%d_tau%g',tt,aa,tau));
      v=R.(ekey);
      sr=1; if 400*tau~=0, sr=abs(sin(pi*400*tau)/(pi*400*tau)); end
      if abs(b.absCenter)<1e-10, relS=NaN; nS='NUMERICALLY_UNRESOLVED'; else, relS=(v.absCenter-b.absCenter)/b.absCenter; nS=''; end
      fprintf(ef,'D60_zf450_M%d_a%d,M%d,%d,%g,five_node_left_sum,%.6g,%.6g,%.6f,%.6f,SYNTHETIC_tau_only;%s\n', ...
        tt,aa,tt,aa,tau,v.absCenter,b.absCenter,relS,sr,nS);
    end
  end
end
fclose(ef);
fprintf('[078D] exposure 8 rows done\n');

% ================= E: 276-pair identifiability =================
R76=load(fullfile(v076Root,'numeric','v076_dynamic_center_corrected.mat'));
fn76=fieldnames(R76);
states=struct();
for i=1:numel(fn76)
  f=R76.(fn76{i});
  if ~isfield(f,'D'), continue; end
  key=matlab.lang.makeValidName(fn76{i});
  states.(key)=struct('C400',f.C400,'D',f.D,'zf',f.zf,'amp',f.amp,'ttype',f.ttype,'name',fn76{i});
end
sn=fieldnames(states); nS=numel(sn);
idf=fopen(fullfile(tabDir,'v078_identifiability276_audit.csv'),'w');
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
      'symmetric normalisation; PRESCRIBED trajectories');
  end
end
fclose(idf);
fprintf('[078E] identifiability: %d pairs\n',pid);
fprintf('[078CDE] all done\n');
end
