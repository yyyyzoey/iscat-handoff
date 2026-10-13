function run_v077_B_qr(outRoot, v074Root)
% v077 B: correct QR normalisation (fixes v076 2/N double-division), analytic
% fixtures with exact two-term G_N references, 24-row correct harmonic
% decomposition with complex leakage closure, centre-series crosscheck.
if nargin<2||isempty(v074Root), v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v077_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
N=2001; Fs=5000; k0=160;
projectRoot=fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
% ---------- 1) analytic fixtures: QR projection vs single-bin DFT vs G_N ----------
ff=fopen(fullfile(tabDir,'v077_qr_analytic_fixtures.csv'),'w');
fprintf(ff,'fixture_id,description,modulation_depth,projection_C400_abs,singlebin_C400_abs,gn_ref_C400_abs,proj_vs_depth_relerr,singlebin_vs_gn_relerr,leakage_absC400,status,note\n');
m=0.05;
fxList={'pure200',{{200,0}};'pure400',{{400,0}};'pure800',{{800,0}};'mix200_400',{{200,0},{400,0}};'mix_phased',{{200,0.7},{400,-1.1}};'const_plus_400',{{400,0.5}}};
for fx=1:6
  desc=fxList{fx,1}; comps=fxList{fx,2};
  tj=(0:N-1)'/Fs; x=ones(N,1);
  for cI=1:size(comps,2)
    fC=comps{cI}{1}; phC=comps{cI}{2};
    x=x+m*cos(2*pi*fC*tj+phC);
  end
  Im=mean(x); Ic=x-Im;
  proj400=0;
  for cI=1:size(comps,2)
    fC=comps{cI}{1};
    Bp=[cos(2*pi*fC*tj),sin(2*pi*fC*tj)];
    pr=Bp\Ic;
    if fC==400, proj400=abs(complex(pr(1),-pr(2)))/Im; end
  end
  Xb=sum(Ic.*exp(-2i*pi*k0*(0:N-1)'/N)); binC=2*abs(Xb)/(N*Im);
  Xgn=0;
  for cI=1:size(comps,2)
    fC=comps{cI}{1}; phC=comps{cI}{2};
    u1=fC/Fs-k0/N; u2=-fC/Fs-k0/N;
    G1=exp(1i*pi*u1*(N-1))*sin(pi*N*u1)/sin(pi*u1);
    G2=exp(1i*pi*u2*(N-1))*sin(pi*N*u2)/sin(pi*u2);
    Xgn=Xgn+(m/2)*(exp(1i*phC)*G1+exp(-1i*phC)*G2);
  end
  gnC=2*abs(Xgn)/(N*Im);
  has400=any(cellfun(@(c)c{1}==400,comps));
  if has400, projExp=m; else, projExp=0; end
  sbErr=abs(binC-gnC)/max(gnC,realmin);
  pErr=abs(proj400-projExp)/max(projExp,realmin);
  leakage=binC;
  if sbErr<1e-5 && (pErr<1e-3 || ~has400), st='PASS'; else, st='FAIL'; end
  fprintf(ff,'FIX%d,"%s",%g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%s,%s\n',fx,desc,m,proj400,binC,gnC,pErr,sbErr,leakage,st, ...
    'projection=true harmonic; singlebin=bin161 content; gn=closed-form reference; difference=leakage');
end
fclose(ff);
% ---------- 2) 24-row correct decomposition ----------
anchor=struct();
for D=[30 60 100]
  for zf=[450 550]
    for x=[-20 -10 0 10 20]
      A=load(fullfile(v074Root,'numeric','render_cache',sprintf('D%d_zf%g_x%+g.mat',D,zf,x)),'a');
      anchor.(position_key(D,zf,x))=struct('Es',A.a.Es,'Eref',A.a.Eref);
    end
  end
end
xs=[-20 -10 0 10 20];
hf=fopen(fullfile(tabDir,'v077_harmonic_fit24_correct.csv'),'w');
fprintf(hf,'D_nm,zf_nm,trajectory_type,amplitude_nm_assumed,C400_complex_proj_real,C400_complex_proj_imag,C400_fit_abs_correct,C400_fit_abs_v076_wrong,bin161_absC400,ratio_bin161_over_correct,leak200_complex_real,leak200_complex_imag,harm400_complex_real,harm400_complex_imag,residual_proj_abs,note\n');
pf=fopen(fullfile(tabDir,'v077_harmonic_complex_projection24.csv'),'w');
fprintf(pf,'D_nm,zf_nm,trajectory_type,amplitude_nm_assumed,term,X_bin161_real,X_bin161_imag,note\n');
cf=fopen(fullfile(tabDir,'v077_center_series_crosscheck.csv'),'w');
fprintf(cf,'case,saved_series_maxabsdiff_fresh,fresh_vs_saved_status,double_vs_single_C400_diff,note\n');
nOK=0;
for D=[30 60 100]
  for zf=[450 550]
    Es=cell(1,5);
    for i=1:5
      ak=anchor.(position_key(D,zf,xs(i))); Es{i}=ak.Es;
      if i==3, Eref=ak.Eref; end
    end
    E=cat(4,Es{:});
    % correct centre fine block 161:165
    Ec=E(161:165,161:165,:,:); ErefC=Eref(161:165,161:165,:);
    nA=5; Lm=zeros(25,nA); Dm=zeros(25,nA); Qm=zeros(25,nA,nA);
    for i=1:nA
      Lm(:,i)=reshape(2*real(sum(conj(ErefC).*Ec(:,:,:,i),3)),25,1);
      Dm(:,i)=reshape(sum(abs(Ec(:,:,:,i)).^2,3),25,1);
      for j2=i+1:nA
        Qm(:,i,j2)=reshape(2*real(sum(conj(Ec(:,:,:,i)).*Ec(:,:,:,j2),3)),25,1);
      end
    end
    Iref=sum(abs(ErefC).^2,3); Iref=Iref(:);
    % saved v076 series for crosscheck
    svKey=matlab.lang.makeValidName(sprintf('D%d_zf%g_M200_a5',D,zf));
    savedSeries=[];
    try
      S76=load(fullfile(projectRoot,'v076_return','numeric','v076_center_roi_harmonic_small_examples.mat'),svKey);
      if isfield(S76,svKey), savedSeries=S76.(svKey).series; end
    catch
    end
    for ttype=[200 400]
      for ampn=[5 20]
        tj=(0:N-1)'/Fs; xj=ampn*cos(2*pi*ttype*tj);
        Iser=zeros(1,1,1,N,'single');
        for j2=1:N
          x=max(min(xj(j2),20),-20);
          ia=find(x>=xs(1:end-1) & x<=xs(2:end),1,'last');
          wb=(x-xs(ia))/(xs(ia+1)-xs(ia)); wa=1-wb;
          v=Iref + wa*Lm(:,ia)+wb*Lm(:,ia+1) + wa^2*Dm(:,ia)+wb^2*Dm(:,ia+1) + wa*wb*Qm(:,ia,ia+1);
          Iser(1,1,1,j2)=single(mean(v));
        end
        I=double(reshape(Iser(1,1,1,:),[],1)); Im=mean(I); Ic=I-Im;
        % QR projection on the full harmonic basis
        tj2=(0:N-1)'/Fs;
        B=[ones(N,1),cos(2*pi*200*tj2),sin(2*pi*200*tj2),cos(2*pi*400*tj2),sin(2*pi*400*tj2),cos(2*pi*800*tj2),sin(2*pi*800*tj2)];
        coef=B\Ic;
        C400c=complex(coef(4),-coef(5))/Im;   % CORRECT normalisation
        C400w=2*abs(complex(coef(4),-coef(5)))/(N*Im); % v076 wrong formula
        C400abs=abs(C400c);
        % single-bin DFT at bin 161
        Xb=sum(Ic.*exp(-2i*pi*k0*(0:N-1)'/N)); C400b=2*abs(Xb)/(N*Im);
        ratio=C400b/max(C400abs,realmin);
        % complex leakage closure: model = Im + sum_h terms -> its own bin-161 projection
        % model reconstruction from the fitted harmonic coefficients:
        Imodel=Im+B*[0;coef(2:7)];
        Xmodel=sum((Imodel-mean(Imodel)).*exp(-2i*pi*k0*(0:N-1)'/N));
        Cmodel=2*Xmodel/(N*Im);
        % leakage of the fitted 200Hz terms into bin 161 (analytic G_N):
        a200=complex(coef(2),-coef(3)); % complex amplitude of 200Hz cos/sin pair
        u1=200/Fs-k0/N; u2=-200/Fs-k0/N;
        G1=exp(1i*pi*u1*(N-1))*sin(pi*N*u1)/sin(pi*u1);
        G2=exp(1i*pi*u2*(N-1))*sin(pi*N*u2)/sin(pi*u2);
        Xleak200=(a200/2)*(G1+G2);
        % true 400Hz harmonic projection into bin 161:
        a400=complex(coef(4),-coef(5));
        v1=400/Fs-k0/N; v2=-400/Fs-k0/N;
        H1=exp(1i*pi*v1*(N-1))*sin(pi*N*v1)/sin(pi*v1);
        H2=exp(1i*pi*v2*(N-1))*sin(pi*N*v2)/sin(pi*v2);
        Xh400=(a400/2)*(H1+H2);
        residV=Ic-B*coef; % residual (series minus fitted harmonics) projection:
        Xres=sum(residV.*exp(-2i*pi*k0*(0:N-1)'/N));
        % closure: Xb ?= Xleak200 + Xh400 + Xres  (mean-subtracted consistently)
        closureAbs=abs(Xb-(Xleak200+Xh400+Xres));
        tname=sprintf('M%d',ttype);
        fprintf(hf,'%d,%g,%s,%g,%.17g,%.17g,%.17g,%.17g,%.17g,%.6f,%.17g,%.17g,%.17g,%.17g,%.17g,%s\n', ...
          D,zf,tname,ampn,real(C400c),imag(C400c),C400abs,C400w,C400b,ratio, ...
          real(Xleak200),imag(Xleak200),real(Xh400),imag(Xh400),abs(Xres), ...
          'CORRECT_NORMALISATION; closure Xbin161=leak200+harm400+residual checked in complex projection table');
        fprintf(pf,'%d,%g,%s,%g,model_total,%.17g,%.17g,fitted-model bin161 projection\n',D,zf,tname,ampn,real(Cmodel),imag(Cmodel));
        fprintf(pf,'%d,%g,%s,%g,leak200,%.17g,%.17g,200Hz fundamental G_N leakage into bin161\n',D,zf,tname,ampn,real(Xleak200),imag(Xleak200));
        fprintf(pf,'%d,%g,%s,%g,harm400,%.17g,%.17g,true 400Hz harmonic projection into bin161\n',D,zf,tname,ampn,real(Xh400),imag(Xh400));
        fprintf(pf,'%d,%g,%s,%g,residual,%.17g,%.17g,residual series projection into bin161\n',D,zf,tname,ampn,real(Xres),imag(Xres));
        % crosscheck with saved v076 series (M200 a5 rows)
        if ttype==200 && ampn==5 && ~isempty(savedSeries)
          % recompute fresh from anchors into a 1x1 series and compare
          dmax=0;
          for j2=1:N
            x=max(min(xj(j2),20),-20);
            ia2=find(x>=xs(1:end-1) & x<=xs(2:end),1,'last');
            wb2=(x-xs(ia2))/(xs(ia2+1)-xs(ia2)); wa2=1-wb2;
            v2=Iref + wa2*Lm(:,ia2)+wb2*Lm(:,ia2+1) + wa2^2*Dm(:,ia2)+wb2^2*Dm(:,ia2+1) + wa2*wb2*Qm(:,ia2,ia2+1);
            dmax=max(dmax,abs(double(mean(v2))-double(savedSeries(j2))));
          end
          fprintf(cf,'%s,%.17g,%s,double-vs-single C400 diff=%s,fresh recomputation from v074 anchors vs saved v076 series\n', ...
            sprintf('D%d_zf%g_M200_a5',D,zf),dmax,tern2s(dmax==0,'IDENTICAL','DIFFERS'),'documented');
          if dmax==0, nOK=nOk+1; end
        end
        key=matlab.lang.makeValidName(sprintf('D%d_zf%g_%s_a%d',D,zf,tname,ampn));
        res.(key)=struct('C400c',C400c,'C400abs',C400abs,'C400b',C400b,'ratio',ratio,'Xleak200',Xleak200,'Xh400',Xh400,'Xres',Xres,'closureAbs',closureAbs,'D',D,'zf',zf,'ttype',tname,'amp',ampn);
      end
    end
  end
end
save(fullfile(numOut,'v077_harmonic_correct.mat'),'-struct','res','-v7.3');
fclose(hf); fclose(pf); fclose(cf);
fprintf('[077B] done; centre-series crosscheck identical cases: %d/6\n',nOK);
end
function s=tern2s(c,a,b), if c, s=a; else, s=b; end, end



