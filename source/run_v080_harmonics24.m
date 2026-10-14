function run_v080_harmonics24(outRoot, v076Root)
% v080: correct 24-trajectory full-rank harmonic decomposition from saved series.
if nargin<2||isempty(v076Root), v076Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v080_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
N=2001; Fs=5000; k0=160;
R76=load(fullfile(v076Root,'numeric','v076_center_roi_harmonic_small_examples.mat'));
RMap=load(fullfile(v076Root,'numeric','v076_dynamic_center_corrected.mat'));
allCases={};
for D=[30 60 100]
  for zf=[450 550]
    for tt=[200 400]
      for aa=[5 20]
        ttype=sprintf('M%d',tt);
        caseId=sprintf('D%d_zf%g_%s_a%d',D,zf,ttype,aa);
        freqs=sort([tt 2*tt 3*tt 4*tt]);
        allCases(end+1,:)={caseId,D,zf,ttype,aa,freqs}; %#ok<AGROW>
      end
    end
  end
end
fprintf('[080] %d cases\n',size(allCases,1));
hf=fopen(fullfile(tabDir,'v080_harmonics24_validated.csv'),'w');
fprintf(hf,'case_id,D_nm,zf_nm,type,a_nm,mean_I,rank_B,cond_B,freqs,bin161_absC,bin161_re,bin161_im,C400_fit_abs,C400_fit_re,C400_fit_im,v076_binAbs,v076_map_C400_21_21,ratio_bin161_over_fit,closure_abs,closure_rel,residual_RMS,validation_status\n');
lf=fopen(fullfile(tabDir,'v080_harmonic_parts_long.csv'),'w');
fprintf(lf,'case_id,freq_Hz,X_re_DFT_count,X_im_DFT_count\n');
rf=fopen(fullfile(tabDir,'v080_harmonic_residual24.csv'),'w');
fprintf(rf,'case_id,Xres_re,Xres_im,residual_RMS\n');
tf=fopen(fullfile(tabDir,'v080_time_series_identity24.csv'),'w');
fprintf(tf,'case_id,saved_len,mean_I,std_I\n');
nPass=0; nTot=0;
for ic=1:size(allCases,1)
  caseId=allCases{ic,1}; D=allCases{ic,2}; zf=allCases{ic,3};
  ttype=allCases{ic,4}; aa=allCases{ic,5}; freqs=allCases{ic,6};
  nTot=nTot+1;
  try
    f76=R76.(caseId);
    savedI=double(f76.series(:));
    assert(numel(savedI)==N,'BAD_LEN');
    nH=numel(freqs);
    tj=(0:N-1)'/Fs;
    % correct full-rank design matrix
    B=zeros(N,1+2*nH); B(:,1)=1;
    for h=1:nH
      B(:,2*h)=cos(2*pi*freqs(h)*tj);
      B(:,2*h+1)=sin(2*pi*freqs(h)*tj);
    end
    rB=rank(B); cB=cond(B);
    % QR fit on mean-subtracted series
    Im=mean(savedI); Ic=savedI-Im;
    coef=B\Ic; residV=Ic-B*coef;
    % complex amplitudes
    Ah=zeros(1,nH);
    for h=1:nH, Ah(h)=complex(coef(2*h),-coef(2*h+1)); end
    Ch=Ah/Im;
    % direct DFT at bin 161
    Xbin=sum(Ic.*exp(-2i*pi*k0*(0:N-1)'/N));
    Cbin=2*abs(Xbin)/(N*Im);
    % per-harmonic DFT contributions
    Xparts=zeros(1,nH);
    for h=1:nH
      fh=freqs(h); aH=Ah(h);
      u1=fh/Fs-k0/N; u2=-fh/Fs-k0/N;
      G1=exp(1i*pi*u1*(N-1))*sin(pi*N*u1)/sin(pi*u1);
      G2=exp(1i*pi*u2*(N-1))*sin(pi*N*u2)/sin(pi*u2);
      Xparts(h)=(Ah(h)/2)*G1+(conj(Ah(h))/2)*G2;
      fprintf(lf,'%s,%g,%.17g,%.17g\n',caseId,fh,real(Xparts(h)),imag(Xparts(h)));
    end
    Xres=sum(residV.*exp(-2i*pi*k0*(0:N-1)'/N));
    closureAbs=abs(Xbin-sum(Xparts)-Xres);
    normY=sqrt(N)*norm(Ic);
    closureRel=closureAbs/max(normY,1e-14);
    rmsR=rms(residV);
    % crosscheck
    binAbs76=f76.binAbs;
    if isfield(RMap,caseId), mapC21=abs(RMap.(caseId).C400(21,21)); else, mapC21=NaN; end
    i400=find(freqs==400,1);
    C400fit=abs(Ch(i400));
    if rB==1+2*nH && cB<1e8 && closureRel<1e-10 && abs(Cbin-binAbs76)/max(binAbs76,realmin)<0.02
      st='PASS'; nPass=nPass+1;
    else
      st='FAIL';
    end
    fprintf(hf,'%s,%d,%g,%s,%g,%.17g,%d,%.4f,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.6f,%.17g,%.17g,%.17g,%s\n', ...
      caseId,D,zf,ttype,aa,Im,rB,cB,mat2str(freqs), ...
      abs(Xbin),real(Xbin),imag(Xbin),C400fit,real(Ch(i400)),imag(Ch(i400)), ...
      binAbs76,mapC21,Cbin/max(C400fit,realmin),closureAbs,closureRel,rmsR,st);
    fprintf(tf,'%s,%d,%.17g,%.17g\n',caseId,numel(savedI),Im,std(savedI));
    fprintf('[080] %s: %s (closureRel=%.2e)\n',caseId,st,closureRel);
  catch ME
    fprintf(hf,'%s,%d,%g,%s,%g,ERROR,0,0,ERROR,0,0,0,0,0,0,0,NaN,NaN,0,0,0,ERROR: %s\n', ...
      caseId,D,zf,ttype,aa,ME.message);
    fprintf(tf,'%s,ERROR,ERROR,ERROR\n',caseId);
    fprintf('[080] %s: ERROR %s\n',caseId,ME.message);
  end
end
fclose(hf); fclose(lf); fclose(rf); fclose(tf);
fprintf('[080] done: %d/%d PASS\n',nPass,nTot);
end
