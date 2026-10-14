function run_v079_B_harmonics24(outRoot, v074Root, v076Root)
% v079 B: correct full-rank harmonic decomposition of 24 centre series.
if nargin<3||isempty(v076Root), v076Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
if nargin<2||isempty(v074Root), v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v079_return'; end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
N=2001; Fs=5000; k0=160; q=5;
% load anchors
anchor=struct();
for D=[30 60 100]
  for zf=[450 550]
    for x=[-20 -10 0 10 20]
      A=load(fullfile(v074Root,'numeric','render_cache',sprintf('D%d_zf%g_x%+g.mat',D,zf,x)),'a');
      anchor.(position_key(D,zf,x))=struct('Es',A.a.Es,'Eref',A.a.Eref);
    end
  end
end
R76=load(fullfile(v076Root,'numeric','v076_center_roi_harmonic_small_examples.mat'));
xs=[-20 -10 0 10 20];
hf=fopen(fullfile(outRoot,'tables','v079_harmonics24_correct.csv'),'w');
fprintf(hf,'case_id,D_nm,zf_nm,type,a_nm,mean_I,rank_B,cond_B,n_cols,freqs,k0,bin_freq,bin161_absC,bin161_re,bin161_im,C400_fit_abs,C400_fit_re,C400_fit_im,v076_abs,ratio,closure_abs,closure_rel,resid_rms,status\n');
lf=fopen(fullfile(outRoot,'tables','v079_harmonic_parts_long.csv'),'w');
fprintf(lf,'case_id,freq_Hz,X_re,X_im,units\n');
sf=fopen(fullfile(outRoot,'tables','v079_series_crosscheck.csv'),'w');
fprintf(sf,'case_id,maxdiff_fresh_vs_saved,status\n');
nPass=0; nTot=0;
for D=[30 60 100]
  for zf=[450 550]
    % load centre fine block from 5 anchors
    Ec=cell(1,5); ErefC=[];
    for iI=1:5
      ak=anchor.(position_key(D,zf,xs(iI)));
      Ec{iI}=ak.Es(161:165,161:165,:);
      if iI==3, ErefC=ak.Eref(161:165,161:165,:); end
    end
    Ec4=cat(4,Ec{:});
    % precompute per-anchor L/D/Q for centre pixel (25 subpixels)
    nA=5; Lm=zeros(25,nA); Dmm=zeros(25,nA); Qmm=zeros(25,nA,nA);
    for iI=1:nA
      Lm(:,iI)=reshape(2*real(sum(conj(ErefC).*Ec4(:,:,:,iI),3)),25,1);
      Dmm(:,iI)=reshape(sum(abs(Ec4(:,:,:,iI)).^2,3),25,1);
      for j2=iI+1:nA
        Qmm(:,iI,j2)=reshape(2*real(sum(conj(Ec4(:,:,:,iI)).*Ec4(:,:,:,j2),3)),25,1);
      end
    end
    Iref=sum(abs(ErefC).^2,3); Iref=Iref(:);
    for tt=[200 400]
      for ampn=[5 20]
        nTot=nTot+1;
        try
          if tt==200, freqs=[200 400 600 800]; else, freqs=[400 800 1200 1600]; end
          nH=numel(freqs);
          tj=(0:N-1)'/Fs; xj=ampn*cos(2*pi*tt*tj);
          Iser=zeros(1,1,1,N,'single');
          for j2=1:N
            x=max(min(xj(j2),20),-20);
            ia2=find(x>=xs(1:end-1) & x<=xs(2:end),1,'last');
            wb=(x-xs(ia2))/(xs(ia2+1)-xs(ia2)); wa=1-wb;
            v=Iref + wa*Lm(:,ia2)+wb*Lm(:,ia2+1) + wa^2*Dmm(:,ia2)+wb^2*Dmm(:,ia2+1) + wa*wb*Qmm(:,ia2,ia2+1);
            Iser(1,1,1,j2)=single(mean(v));
          end
          I=double(reshape(Iser(1,1,1,:),[],1)); Im=mean(I); Ic=I-Im;
          % correct full-rank design matrix
          nH=numel(freqs);
          B=zeros(N,1+2*nH); B(:,1)=1;
          for hI=1:nH
            B(:,2*hI)=cos(2*pi*freqs(hI)*tj);
            B(:,2*hI+1)=sin(2*pi*freqs(hI)*tj);
          end
          rB=rank(B); cB=cond(B);
          coef=B\Ic; residV=Ic-B*coef;
          Ah=zeros(1,nH);
          for hI=1:nH, Ah(hI)=complex(coef(2*hI),-coef(2*hI+1)); end
          Ch=Ah/Im;
          % DFT at bin 161
          Xbin=sum(Ic.*exp(-2i*pi*k0*(0:N-1)'/N));
          Cbin=2*abs(Xbin)/(N*Im);
          % per-harmonic DFT contributions + closure
          XmodelSum=complex(0,0);
          for hI=1:nH
            fh=freqs(hI); aH=Ah(hI);
            u1=fh/Fs-k0/N; u2=-fh/Fs-k0/N;
            G1v=exp(1i*pi*u1*(N-1))*sin(pi*N*u1)/sin(pi*u1);
            G2v=exp(1i*pi*u2*(N-1))*sin(pi*N*u2)/sin(pi*u2);
            Xh=(aH/2)*G1v+(conj(aH)/2)*G2v;
            XmodelSum=XmodelSum+Xh;
            fprintf(lf,'%s,%g,X_h%g,%.17g,%.17g,DFT_count\n',sprintf('D%d_zf%g_%s_a%d',D,zf,tt,ampn),fh,fh,real(Xh),imag(Xh));
          end
          Xres=sum(residV.*exp(-2i*pi*k0*(0:N-1)'/N));
          Xint=sum(Im*exp(-2i*pi*k0*(0:N-1)'/N));
          closureAbs=abs(Xbin-(XmodelSum+Xres+Xint));
          normY=sqrt(N)*norm(Ic);
          closureRel=closureAbs/max(normY,1e-14);
          rmsR=rms(residV);
          % crosscheck with v076 saved series
          svKey=matlab.lang.makeValidName(sprintf('D%d_zf%g_%s_a%d',D,zf,tt,ampn));
          savedDiff=NaN;
          if isfield(R76,svKey) && isfield(R76.(svKey),'series')
            savedI=double(R76.(svKey).series(:));
            freshI=double(reshape(Iser(1,1,1,:),[],1));
            savedDiff=max(abs(freshI-savedI));
          end
          if rB==1+2*nH && cB<1e8 && closureRel<1e-10, st='PASS'; nPass=nPass+1; else, st='FAIL'; end
          % find 400Hz index
          i400=find(freqs==400,1); if isempty(i400), i400=2; end
          C400fit=abs(Ch(i400));
          fStr='';
          for hI=1:nH, fStr=[fStr sprintf('%g ',freqs(hI))]; end
          caseId=sprintf('D%d_zf%g_%s_a%d',D,zf,tt,ampn);
          fprintf(hf,'%s,%d,%g,%s,%g,%.17g,%d,%.4f,%d,%s,%d,%.9f,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.6f,%.17g,%.17g,%.17g,%s\n', ...
            caseId,D,zf,tt,ampn,Im,rB,cB,1+2*nH,fStr,k0,399.80009995002496, ...
            abs(Xbin),real(Xbin),imag(Xbin),C400fit,real(Ch(i400)),imag(Ch(i400)), ...
            abs(R76.(svKey).C400(21,21)), abs(R76.(svKey).C400(21,21))/max(C400fit,realmin), ...
            closureAbs,closureRel,rmsR,st);
          if ~isnan(savedDiff)
            fprintf(sf,'%s,%.17g,%s\n',caseId,savedDiff,tern2s(savedDiff<1e-6,'SINGLE_PRECISION_CONSISTENT','INVESTIGATE'));
          end
        catch ME
          fprintf(hf,'D%d_zf%g_%s_a%d,%d,%g,%s,%g,ERROR,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,ERROR: %s\n', ...
            D,zf,tt,ampn,D,zf,tt,ampn,ME.message);
        end
      end
    end
  end
end
fclose(hf); fclose(lf); fclose(sf);
fprintf('[079B] done: %d/%d PASS\n',nPass,nTot);
end
function s=tern2s(c,a,b), if c, s=a; else, s=b; end, end
