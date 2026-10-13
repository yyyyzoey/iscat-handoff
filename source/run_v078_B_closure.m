function run_v078_B_closure(outRoot, v074Root, v076Root)
% v078 B: complex harmonic closure with correct conjugate mirror terms.
% Fix: X_h->k = (A_h/2)*G_N(f_h/Fs - k0/N) + (conj(A_h)/2)*G_N(-f_h/Fs - k0/N)
% Old v077 bug: used (A_h/2) for BOTH terms (missing conjugate on mirror).
if nargin<3||isempty(v076Root), v076Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
if nargin<2||isempty(v074Root), v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v078_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
N=2001; Fs=5000; k0=160;

% ---- G_N function (simple direct formula) ----
GN=@(u) exp(1i*pi*u*(N-1))*sin(pi*N*u)/sin(pi*u);

% closure tolerance
tolClosure=1e-10;

% ================= 1) SIX ANALYTIC FIXTURES =================
ff=fopen(fullfile(tabDir,'v078_complex_projection_fixtures.csv'),'w');
fprintf(ff,'fixture_id,description,freqs,depths,phases,bin161_dft_abs,bin161_model_abs_correct,bin161_model_abs_old_wrong,leak200_C,leak400_C,leak800_C,harm400_fit_C,residual_C,closure_abs_dft_units,closure_rel,old_formula_fail,new_formula_status\n');
m=0.05;
fixtures={
 'F1_200Hz_phase0.7', 200, 0.7;
 'F2_400Hz_phase0',   400, 0;
 'F3_200Hz_phase0',   200, 0;
 'F4_200p400_phases', 0,   0;
 'F5_200p400p800',    0,   0;
 'F6_zero_modulation',0,   0;
};
for fx=1:6
  if fx==4, freqs=[200 400]; phis=[0.7 -1.1]; depths=[m m]; desc='200+400Hz both nonzero phase';
  elseif fx==5, freqs=[200 400 800]; phis=[0.3 -1.1 0.5]; depths=[m m m*0.5]; desc='200+400+800Hz nonzero phase';
  elseif fx==6, freqs=[]; phis=[]; depths=[]; desc='zero modulation';
  else
    f0=fixtures{fx,2}; p0=fixtures{fx,3};
    freqs=f0; phis=p0; depths=m; desc=sprintf('pure %gHz phase=%g',f0,p0);
  end
  % build signal
  tj=(0:N-1)'/Fs; x=ones(N,1);
  for cI=1:numel(freqs), x=x+depths(cI)*cos(2*pi*freqs(cI)*tj+phis(cI)); end
  Im=mean(x); Ic=x-Im;
  % direct DFT at bin 161
  Xbin=sum(Ic.*exp(-2i*pi*k0*(0:N-1)'/N));
  Cbin_dft=2*abs(Xbin)/(N*Im);
  % joint QR with all component frequencies + 800Hz
  allFreqs=union(freqs,800); allFreqs=sort(allFreqs(:)');
  nH=max(numel(allFreqs),1);
  Bm=zeros(N,1+2*nH); Bm(:,1)=1;
  for hI=1:nH, Bm(:,2+2*(hI-1)-1)=cos(2*pi*allFreqs(hI)*tj); Bm(:,2+2*(hI-1))=sin(2*pi*allFreqs(hI)*tj); end
  coefAll=Bm\Ic; residV=Ic-Bm*coefAll;
  b0=coefAll(1);
  % extract A_h (complex amplitudes)
  Ah=zeros(1,nH);
  for hI=1:nH, Ah(hI)=complex(coefAll(2+2*(hI-1)-1),-coefAll(2+2*(hI-1))); end
  % model contributions: CORRECT (conj) vs OLD (no conj)
  XmodelNew=0; XmodelOld=0;
  leak200=0; leak400=0; leak800=0; harm400fit=0;
  for hI=1:nH
    fh=allFreqs(hI); aH=Ah(hI);
    u1=fh/Fs-k0/N; u2=-fh/Fs-k0/N;
    G1v=GN(u1); G2v=GN(u2);
    XhNew=(aH/2)*G1v+(conj(aH)/2)*G2v; % CORRECT
    XhOld=(aH/2)*G1v+(aH/2)*G2v; % OLD WRONG
    XmodelNew=XmodelNew+XhNew; XmodelOld=XmodelOld+XhOld;
    Ctmp=2*abs(XhNew)/(N*Im);
    if fh==200, leak200=Ctmp; end
    if fh==400, leak400=Ctmp; harm400fit=abs(aH)/Im; end
    if fh==800, leak800=Ctmp; end
  end
  Xres=sum(residV.*exp(-2i*pi*k0*(0:N-1)'/N));
  Xint=b0*sum(exp(-2i*pi*k0*(0:N-1)'/N)); % ~0 for k0>0
  Cres=2*abs(Xres)/(N*Im);
  % closure: complex sum
  totalNew=XmodelNew+Xres+Xint;
  closureAbs=abs(Xbin-totalNew);
  normY=sqrt(N)*norm(Ic);
  closureRel=closureAbs/max(normY,1e-14);
  % old formula test: does old fail on nonzero-phase?
  Cold=2*abs(XmodelOld)/(N*Im);
  oldFail=abs(Cbin_dft-Cold)>1e-10 && any(phis~=0);
  newOK=closureRel<tolClosure;
  % freq/depth/phase strings
  fS=''; dS=''; pS='';
  for cI=1:numel(freqs), fS=[fS sprintf('%g ',freqs(cI))]; dS=[dS sprintf('%g ',depths(cI))]; pS=[pS sprintf('%g ',phis(cI))]; end
  fprintf(ff,'FIX%d,%s,%s,%s,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%d,%s\n', ...
    fx,desc,fS,dS,pS,abs(Xbin),abs(XmodelNew),abs(XmodelOld),leak200,leak400,leak800,harm400fit,Cres,closureAbs,closureRel,oldFail,tern2s(newOK,'NEW_PASS','NEW_FAIL'));
end
fclose(ff);
fprintf('[078B] 6 fixtures done\n');

% ================= 2) 24 TRAJECTORY CLOSURE =================
R=load(fullfile(v076Root,'numeric','v076_center_roi_harmonic_small_examples.mat'));
fn=fieldnames(R);
hf=fopen(fullfile(tabDir,'v078_harmonics24_complex_closed.csv'),'w');
fprintf(hf,'D_nm,zf_nm,trajectory_type,amplitude_nm,freqs_fitted,bin161_dft_abs,bin161_model_correct_abs,bin161_model_old_abs,leak200_C,leak400_C,leak800_C,harm400_fit_C,residual_C,closure_abs,closure_rel,closure_status,old_formula_ratio\n');
pf=fopen(fullfile(tabDir,'v078_harmonic_parts_long.csv'),'w');
fprintf(pf,'D_nm,zf_nm,trajectory_type,amplitude_nm,term,X_bin161_real,X_bin161_imag,units\n');
nPass=0; nTot=0;
for iI=1:numel(fn)
  f=R.(fn{iI});
  if ~isfield(f,'series'), continue; end
  I=double(f.series(:)); Im=mean(I); Ic=I-Im;
  toks=regexp(fn{iI},'D(\d+)_zf(\d+)_(M\d+)_a(\d+)','tokens','once');
  D=str2double(toks{1}); zf=str2double(toks{2}); tt=toks{3}; aa=str2double(toks{4});
  if strcmp(tt,'M200'), allFreqs=[200 400 600 800]; else, allFreqs=[400 800 1200 1600]; end
  nH=numel(allFreqs);
  tj=(0:N-1)'/Fs;
  Bm=zeros(N,1+2*nH); Bm(:,1)=1;
  for hI=1:nH, Bm(:,2+2*(hI-1)-1)=cos(2*pi*allFreqs(hI)*tj); Bm(:,2+2*(hI-1))=sin(2*pi*allFreqs(hI)*tj); end
  coefAll=Bm\Ic; residV=Ic-Bm*coefAll;
  b0=coefAll(1);
  Ah=zeros(1,nH);
  for hI=1:nH, Ah(hI)=complex(coefAll(2+2*(hI-1)-1),-coefAll(2+2*(hI-1))); end
  Xbin=sum(Ic.*exp(-2i*pi*k0*(0:N-1)'/N));
  Cbin=2*abs(Xbin)/(N*Im);
  XmodelNew=0; XmodelOld=0;
  leak200=0; leak400=0; leak800=0; harm400fit=0;
  for hI=1:nH
    fh=allFreqs(hI); aH=Ah(hI);
    u1=fh/Fs-k0/N; u2=-fh/Fs-k0/N;
    G1v=GN(u1); G2v=GN(u2);
    XhNew=(aH/2)*G1v+(conj(aH)/2)*G2v;
    XhOld=(aH/2)*G1v+(aH/2)*G2v;
    XmodelNew=XmodelNew+XhNew; XmodelOld=XmodelOld+XhOld;
    Ctmp=2*abs(XhNew)/(N*Im);
    if fh==200, leak200=Ctmp; end
    if fh==400, leak400=Ctmp; harm400fit=abs(aH)/Im; end
    if fh==800, leak800=Ctmp; end
  end
  Xres=sum(residV.*exp(-2i*pi*k0*(0:N-1)'/N));
  Xint=b0*sum(exp(-2i*pi*k0*(0:N-1)'/N));
  totalNew=XmodelNew+Xres+Xint;
  closureAbs=abs(Xbin-totalNew);
  normY=sqrt(N)*norm(Ic);
  closureRel=closureAbs/max(normY,1e-14);
  newOK=closureRel<tolClosure;
  if newOK, nPass=nPass+1; end
  nTot=nTot+1;
  Cold=2*abs(XmodelOld)/(N*Im);
  fprintf(hf,'%d,%g,%s,%g,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%s,%.6f\n', ...
    D,zf,tt,aa,mat2str(allFreqs),abs(Xbin),abs(XmodelNew),abs(XmodelOld),leak200,leak400,leak800,harm400fit, ...
    2*abs(Xres)/(N*Im),closureAbs,closureRel,tern2s(newOK,'CLOSURE_PASS','CLOSURE_FAIL'),Cold/max(Cbin,realmin));
  fprintf(pf,'%d,%g,%s,%g,bin161_dft,%.17g,%.17g,DFT_count\n',D,zf,tt,aa,real(Xbin),imag(Xbin));
  fprintf(pf,'%d,%g,%s,%g,model_correct,%.17g,%.17g,DFT_count\n',D,zf,tt,aa,real(totalNew),imag(totalNew));
  fprintf(pf,'%d,%g,%s,%g,residual,%.17g,%.17g,DFT_count\n',D,zf,tt,aa,real(Xres),imag(Xres));
  fprintf(pf,'%d,%g,%s,%g,intercept,%.17g,%.17g,DFT_count\n',D,zf,tt,aa,real(Xint),imag(Xint));
end
fclose(hf); fclose(pf);
fprintf('[078B] trajectory closure: %d/%d PASS\n',nPass,nTot);
end

function s=tern2s(c,a,b), if c, s=a; else, s=b; end, end

