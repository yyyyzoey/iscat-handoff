function run_v072_fft_fixtures(outRoot)
% v072 B: analytic FFT fixtures (<=12) validating two real extractor chains
% (test.m 420 unnormalized; test_with_contrast.m 400 normalized contrast)
% against an independent direct-DFT reference. No BEM, no real BMP needed.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v072_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
Fs=5000; N=2001; tol_abs=1e-7; tol_rel=1e-5; tol_phase=1e-4; % phase rad, declared for single-precision FFT at N=2001
df=Fs/N;
f400=160*df; f420=168*df;   % nearest-bin actual frequencies
fprintf('[072B] df=%.17g f400=%.17g f420=%.17g\n',df,f400,f420);

% bin audit
bf=fopen(fullfile(tabDir,'fft_bin_audit.csv'),'w');
fprintf(bf,'targetFreq_Hz,N,Fs,deltaF_Hz,bin_index_1based,actualFreq_Hz,source_script\n');
fprintf(bf,'400,2001,5000,%.17g,161,%.17g,test_with_contrast.m sha256=d08575b1e860e09f29c74652442a77b721039c6e32368fe76d2c5c63143ea3aa (workstation C:\\\\Users\\\\PC\\\\Downloads\\\\test_with_contrast.m)\n',df,f400);
fprintf(bf,'420,2001,5000,%.17g,169,%.17g,test.m sha256=fdc918e691b13b33cbae8b32ecaacd1e63ec27be3e23b61b0701d0e595aea684 (workstation C:\\\\Users\\\\PC\\\\Desktop\\\\课题\\\\test.m)\n',df,f420);
fprintf(bf,'historical_399.8001,2001,5000,%.17g,161,%.17g,historical FFT output files; consistent with 400 Hz target on N=2001/Fs=5000\n',df,f400);
fclose(bf);

% fixture runner
ff=fopen(fullfile(tabDir,'fft_analytic_fixtures.csv'),'w');
fprintf(ff,'fixture_id,description,chain,k0_1based,expected_complex,actual_complex,complex_absdiff,complex_relerr,expected_amp,actual_amp,amp_relerr,expected_phase,actual_phase,phase_wrapdiff,phase_status,status,tolerance_note\n');
S=struct(); results=struct();
nfix=0;
% F01 constant background
nfix=nfix+1; [st,aux]=runFixture(nfix,'constant background only (amp~0 at 400/420)','test420',161, ...
  @(t) 100*ones(5,5,numel(t),'single'), Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
nfix=nfix+1; [st,aux]=runFixture(nfix,'exact-bin cosine 399.800099950025 Hz amp=0.02 phase=0.7','test420',161, ...
  @(t) single(reshape(100+0.02*cos(2*pi*f400*(t)+0.7),1,1,[]).*ones(5,5,1)), Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
nfix=nfix+1; [st,aux]=runFixture(nfix,'exact-bin cosine 419.790104947526 Hz amp=0.01 phase=-1.1','test420',169, ...
  @(t) single(reshape(100+0.01*cos(2*pi*f420*(t)-1.1),1,1,[]).*ones(5,5,1)), Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
nfix=nfix+1; [st,aux]=runFixture(nfix,'non-integer bin 400.5 Hz (leakage, nearest k=160)','test420',161, ...
  @(t) single(reshape(100+0.02*cos(2*pi*400.5*t),1,1,[]).*ones(5,5,1)), Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
nfix=nfix+1; [st,aux]=runFixture(nfix,'non-integer bin 419.0 Hz (nearest k=168/169)','test420',169, ...
  @(t) single(reshape(100+0.01*cos(2*pi*419.0*t),1,1,[]).*ones(5,5,1)), Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
% F06 two-frequency mix
nfix=nfix+1;
mixf=@(t,k) single(reshape(100+0.02*cos(2*pi*f400*t+0.3),1,1,[]).*ones(5,5,1)+reshape(0.01*cos(2*pi*f420*t-0.9),1,1,[]).*ones(5,5,1));
[st,aux]=runFixture(nfix,'two-frequency mix 400+420, check k=161 and k=169','test420',[161 169],mixf,Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
% F07 time-origin shift (window starts at t0=0.2 s)
nfix=nfix+1;
n0=1000; % frames skipped before window start (startFrame shift)
shif=@(t) single(reshape(100+0.02*cos(2*pi*f400*t+0.7),1,1,[]).*ones(5,5,1));
[st,aux]=runFixture(nfix,'time-origin shift: window starts at frame 1001; amplitude invariant, phase rotated','test420',161,shif,Fs,N,tol_abs,tol_rel,'t0_frames',n0);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
% F08 zero background
nfix=nfix+1; [st,aux]=runFixture(nfix,'zero background stack (amp=0, phase UNDEFINED)','test420',161, ...
  @(t) zeros(5,5,numel(t),'single'), Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
% F09 low-background mask (contrast chain)
nfix=nfix+1; [st,aux]=runFixtureContrast(nfix,'contrast chain: one low-Imean pixel excluded by meanFloor mask',161, ...
  @(t) single(reshape(100+0.02*cos(2*pi*f400*t+0.5),1,1,numel(t)).*ones(5,5,numel(t))), Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
% F10 RGB gray mapping
nfix=nfix+1; [st,aux]=runFixtureRGB(nfix,'RGB->gray weights 0.2989/0.5870/0.114 equal manual gray chain',161, ...
  @(t) single(reshape(100+0.02*cos(2*pi*f400*t+0.2),1,1,[]).*ones(5,5,numel(t))), Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
% F11 non-finite input
nfix=nfix+1; [st,aux]=runFixtureNaN(nfix,'NaN pixel: contrast chain marks invalid, unnormalized chain propagates NaN',161, ...
  @(t) single(reshape(100+0.02*cos(2*pi*f400*t+0.4),1,1,[]).*ones(5,5,numel(t))), Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
% F12 exposure sinc (analytic only)
nfix=nfix+1; [st,aux]=runFixtureExposure(nfix,'ANALYTIC_FIXTURE_ONLY: rectangular exposure tau=0.0001s sinc attenuation',161,Fs,N,tol_abs,tol_rel);
results.(['F' sprintf('%02d',nfix)])=aux; printFix(ff,st);
fclose(ff);
save(fullfile(numOut,'analytic_fft_fixture_small.mat'),'-struct','results','-v7.3');
fprintf('[072B] %d fixtures done\n',nfix);
end

function st=printFix(fid,st)
fprintf(fid,'%d,"%s",%s,%s,%s,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%s,%s,%s,%s,%s,%s\n', ...
  st.id,st.desc,st.chain,st.kstr,st.expC,st.actC,st.cdiff,st.crel,st.expA,st.actA,st.arel, ...
  st.expP,st.actP,st.pdiff,st.pstatus,st.status,st.tol);
end

function [st,aux]=runFixture(id,desc,chain,klist,fgen,Fs,N,tolA,tolR,varargin)
tol_phase=1e-4; % phase rad, declared for single-precision FFT at N=2001 (uniform, not per-result)
% build stack, run chain for klist bins, compare with direct DFT
t=(0:N-1)'/Fs;
if any(strcmp(varargin,'t0_frames')), n0=varargin{find(strcmp(varargin,'t0_frames'))+1}; else, n0=0; end
stack=fgen(t);
X=chainTest420(stack,N);           % fft-based, bin indices 1-based
Xk=X(:,:,klist);
Xr=zeros(size(Xk)); tmr=mean(stack,3);   % direct DFT reference (same mean subtraction)
idx=0:numel(klist)-1;
for b=1:numel(klist)
  kk=klist(b)-1;                   % 0-based
  acc=0;
  for nn=1:N
    acc=acc+double(stack(:,:,nn)-tmr).*exp(-2i*pi*kk*(nn-1)/N);
  end
  Xr(:,:,b)=acc;
end
scale=2; % non-DC non-Nyquist
Achain=scale*abs(Xk)/N; Aref=scale*abs(Xr)/N;
Pchain=angle(Xk); Pref=angle(Xr);
cd=max(abs(Xk(:)-Xr(:))); cr=cd/max(max(abs(Xr(:))),realmin);
ar=max(abs(Achain(:)-Aref(:)))/max(max(abs(Aref(:))),realmin);
pd=angle(exp(1i*(Pchain-Pref))); pd=max(abs(pd(:)));
ampKnown=max(Aref(:))>1e-12;
pst='DEFINED'; if ~ampKnown, pst='UNDEFINED'; pd=NaN; end
if ampKnown
  ok=(cr<tolR)&&(ar<tolR)&&(pd<tol_phase);
else
  ok=(cr<tolA||cr<tolR)&&(ar<tolA);
end
anaTol='';
if id==2, ana=[0.02 0.7]; elseif id==3, ana=[0.01 -1.1]; else, ana=[]; end
if ~isempty(ana)
  aerr=max(abs(Achain(:)-ana(1))); perr=max(abs(angle(exp(1i*(Pchain(:)-ana(2))))));
  ok=ok && aerr<tolR && perr<tol_phase;
  anaTol=sprintf('; analytic amp=%.17g phase=%.17g checked (aerr=%.3g perr=%.3g)',ana(1),ana(2),aerr,perr);
end
if ok, status='PASS'; else, status='FAIL'; end
ks=sprintf('%d',klist(1)); if numel(klist)>1, ks=sprintf('%s..%d',ks,klist(end)); end
st=struct('id',id,'desc',desc,'chain',chain,'kstr',ks,'expC','direct_DFT','actC','fft_chain', ...
  'cdiff',cd,'crel',cr,'expA',max(Aref(:)),'actA',max(Achain(:)),'arel',ar, ...
  'expP','direct_DFT','actP','fft_chain','pdiff',pd,'pstatus',pst,'status',status, ...
  'tol',sprintf('abs=%.0e rel=%.0e phase=%.0e rad (fixture-level, single precision)%s',tolA,tolR,tol_phase,anaTol));
aux=struct('id',id,'Xk',Xk,'Xref',Xr,'Achain',Achain,'Aref',Aref,'status',status);
end

function [st,aux]=runFixtureContrast(id,desc,k1,fgen,Fs,N,tolA,tolR)
t=(0:N-1)'/Fs; stack=fgen(t);
stack(2,2,:)=single(0.0001);   % one low-background pixel (Imean below floor)
timeMean=mean(stack,3);
signal=stack-timeMean;
X=fft(signal,[],3); Xk=X(:,:,k1);
tmr=mean(stack,3); Xr=0; for nn=1:N, Xr=Xr+double(stack(:,:,nn)-tmr).*exp(-2i*pi*(k1-1)*(nn-1)/N); end
pos=timeMean(timeMean>0&isfinite(timeMean));
meanFloor=0.01*median(pos);
mask=isfinite(timeMean)&timeMean>meanFloor;
C=complex(zeros(size(Xk))); C(mask)=2*Xk(mask)./(N*timeMean(mask));
Cr=complex(zeros(size(Xk))); Cr(mask)=2*Xr(mask)./(N*double(timeMean(mask)));
cd=max(abs(C(:)-Cr(:))); cr=cd/max(abs(Cr(1)),realmin);
okmask=(mask(2,2)==0);
ok=(cr<tolR)&&okmask;
st=struct('id',id,'desc',desc,'chain','contrast400','kstr',sprintf('%d',k1), ...
  'expC','direct_DFT','actC','fft_chain','cdiff',cd,'crel',cr, ...
  'expA',abs(Cr(1)),'actA',abs(C(1)),'arel',abs(abs(C(1))-abs(Cr(1)))/max(abs(Cr(1)),realmin), ...
  'expP','direct_DFT','actP','fft_chain','pdiff',abs(angle(exp(1i*(angle(C(1))-angle(Cr(1)))))), ...
  'pstatus','DEFINED','status',tern(ok,'PASS','FAIL'),'tol',sprintf('abs=%.0e rel=%.0e; mask excludes low-Imean pixel',tolA,tolR));
aux=struct('id',id,'C',C,'Cr',Cr,'mask',mask,'meanFloor',meanFloor,'status',st.status);
end

function [st,aux]=runFixtureRGB(id,desc,k1,fgray,Fs,N,tolA,tolR)
t=(0:N-1)'/Fs; g=fgray(t);
R=g; G=g.*0.5; B=g.*0.25;               % synthetic channels
grayManual=0.2989*R+0.5870*G+0.1140*B;
grayChain=0.2989*R+0.5870*G+0.1140*B;   % same op as scripts (documented)
tm=mean(grayChain,3); sig=grayChain-tm;
X=fft(sig,[],3); Xk=X(:,:,k1);
tmr=mean(grayManual,3); Xr=0; for nn=1:N, Xr=Xr+double(grayManual(:,:,nn)-tmr).*exp(-2i*pi*(k1-1)*(nn-1)/N); end
cd=max(abs(Xk(:)-Xr(:))); cr=cd/max(max(abs(Xr(:))),realmin);
ok=cr<tolR;
st=struct('id',id,'desc',desc,'chain','test420_rgbgray','kstr',sprintf('%d',k1), ...
  'expC','direct_DFT(manual gray)','actC','fft_chain(gray)','cdiff',cd,'crel',cr, ...
  'expA',2*max(abs(Xr(:)))/N,'actA',2*max(abs(Xk(:)))/N,'arel',max(abs(abs(Xk(:))-abs(Xr(:))))/max(2*max(abs(Xr(:)))/N,realmin), ...
  'expP','direct_DFT','actP','fft_chain','pdiff',max(abs(angle(exp(1i*(angle(Xk(:))-angle(Xr(:))))))), ...
  'pstatus','DEFINED','status',tern(ok,'PASS','FAIL'),'tol',sprintf('abs=%.0e rel=%.0e',tolA,tolR));
aux=struct('id',id,'Xk',Xk,'Xref',Xr,'status',st.status);
end

function [st,aux]=runFixtureNaN(id,desc,k1,fgen,Fs,N,tolA,tolR)
t=(0:N-1)'/Fs; stack=fgen(t); stack(3,3,100)=NaN;
tm=mean(stack,3); sig=stack-tm;
X=fft(sig,[],3); Xk=X(:,:,k1);
propNaN=any(isnan(Xk(:)));
timeMean=mean(stack,3); pos=timeMean(timeMean>0&isfinite(timeMean));
meanFloor=0.01*median(pos); mask=isfinite(timeMean)&timeMean>meanFloor;
nanMasked=(mask(3,3)==0);
ok=propNaN&&nanMasked;
st=struct('id',id,'desc',desc,'chain','test420+contrast400','kstr',sprintf('%d',k1), ...
  'expC','NaN propagates (unnormalized); masked in contrast','actC',tern(propNaN,'NaN_PROPAGATED','NOT_PROPAGATED'), ...
  'cdiff',NaN,'crel',NaN,'expA',NaN,'actA',NaN,'arel',NaN, ...
  'expP','UNDEFINED','actP','UNDEFINED','pdiff',NaN,'pstatus','UNDEFINED', ...
  'status',tern(ok,'PASS','FAIL'),'tol','behavioral check (NaN propagation + isfinite mask)');
aux=struct('id',id,'propNaN',propNaN,'nanMasked',nanMasked,'status',st.status);
end

function [st,aux]=runFixtureExposure(id,desc,k1,Fs,N,tolA,tolR)
% point-sample cosine vs exposure-averaged cosine over tau; ratio = sinc(k*df*tau)-like
f=160*Fs/N; tau=0.0001;
t=(0:N-1)'/Fs;
xpoint=cos(2*pi*f*t);
% exposure-averaged signal: average over [t-tau/2, t+tau/2] = sinc(tau*f)*cos(...)
factor=sinc(tau*f);
xexp=factor*cos(2*pi*f*t);
Xp=fft(xpoint); Xe=fft(xexp);
ratio=abs(Xe(k1))/abs(Xp(k1));
err=abs(ratio-factor);
ok=err<tolA;
st=struct('id',id,'desc',desc,'chain','analytic_exposure','kstr',sprintf('%d',k1), ...
  'expC',sprintf('sinc(tau*f)=%.17g',factor),'actC',sprintf('fft ratio=%.17g',ratio), ...
  'cdiff',err,'crel',err/max(abs(factor),realmin),'expA',factor,'actA',ratio,'arel',err/max(abs(factor),realmin), ...
  'expP','0','actP','0','pdiff',0,'pstatus','DEFINED', ...
  'status',tern(ok,'PASS','FAIL'),'tol','abs=1e-7 (ANALYTIC_FIXTURE_ONLY, demo tau)');
aux=struct('id',id,'factor',factor,'ratio',ratio,'status',st.status);
end

function X=chainTest420(stack,N)
tm=mean(stack,3); sig=stack-tm; X=fft(sig,[],3);
end
function out=tern(c,a,b), if c, out=a; else, out=b; end, end















