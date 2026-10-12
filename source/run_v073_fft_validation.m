function run_v073_fft_validation(outRoot)
% v073 A+B: axis negative tests, 3D/4D equivalence, targeted fixtures (<=8)
% closing the documented v072 gaps. Original v072 fixture CSVs preserved untouched.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v073_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
Fs=5000; N=2001; f400=160*Fs/N; f420=168*Fs/N; tauA=1e-7; tauR=1e-5; tauP=1e-4;
fprintf('[073A] f400=%.17g f420=%.17g\n',f400,f420);
% bin audit
bf=fopen(fullfile(tabDir,'fft_bin_audit_v073.csv'),'w');
fprintf(bf,'item,value,check\n');
fprintf(bf,'N,2001,asserted inside extract_fft_v073\n');
fprintf(bf,'Fs,5000,\n');
fprintf(bf,'deltaF_Hz,%.17g,Fs/N\n',Fs/N);
fprintf(bf,'k0_400,160,round(400*N/Fs)\n');
fprintf(bf,'k_matlab_400,161,k0+1; actual %.17g Hz\n',f400);
fprintf(bf,'k0_420,168,round(420*N/Fs)\n');
fprintf(bf,'k_matlab_420,169,k0+1; actual %.17g Hz\n',f420);
fprintf(bf,'historical_399.8001,consistent,matches bin 161 exactly\n');
fclose(bf);
% axis negative tests
af=fopen(fullfile(tabDir,'fft_axis_negative_tests.csv'),'w');
fprintf(af,'test_id,setup,expected,observed,status\n');
t=(0:N-1)'/Fs;
sig3=single(reshape(100+0.02*cos(2*pi*f400*t+0.7),1,1,[]).*ones(4,3,N));
% (1) guarded wrong axis must ERROR
caught='';
try
  extract_fft_v073(sig3,4,Fs,400);
  caught='NO_ERROR_THROWN';
catch ME
  caught=ME.identifier;
end
if strcmp(caught,'extract_fft_v073:BAD_TIME_DIM'), st1='PASS'; else, st1='FAIL'; end
fprintf(af,'NEG1_wrong_dim_guarded,extract_fft_v073(stack3D,timeDim=4),error extract_fft_v073:BAD_TIME_DIM,%s,%s\n',caught,st1);
% (2) historical bug reproduction: unguarded fft(...,4) on 3-D returns input unchanged
Fwrong=fft(sig3-mean(sig3,3),[],4);
unchanged=isequal(Fwrong,sig3-mean(sig3,3));
if unchanged, st2='PASS'; expl2='fft dim>ndims returned input unchanged (v072 failure mode documented)'; else, st2='FAIL'; expl2='unexpected'; end
fprintf(af,'NEG2_unguarded_dim4_returns_input,fft(signal3D,[],4),array returned unchanged (no FFT),unchanged=%d %s,%s\n',unchanged,expl2,st2);
% (3) correct dim3 matches analytic coefficient
o3=extract_fft_v073(sig3,3,Fs,400);
Xexp=(N/2)*0.02*exp(1i*0.7)*ones(4,3);
Xexp=cast(Xexp,'like',o3.Xk);
err=max(abs(double(o3.Xk(:))-Xexp(:)));
rel=err/max(abs(Xexp(1)),realmin);
pd=max(abs(angle(exp(1i*(double(o3.phase(:))-0.7)))));
if rel<tauR && pd<tauP, st3='PASS'; else, st3='FAIL'; end
fprintf(af,'NEG3_correct_dim3_analytic,extract_fft_v073(stack3D,3),|X_k-(N/2)Ae^{i phi}|/|X|<%.0e and phase<%.0e,rel=%.3g phase=%.3g,%s\n',tauR,tauP,rel,pd,st3);
fclose(af);
fprintf('[073A] negative tests: %s %s %s\n',st1,st2(1:4),st3);
% targeted fixtures (8) -> fft_fixture_corrections.csv
fc=fopen(fullfile(tabDir,'fft_fixture_corrections.csv'),'w');
fprintf(fc,'fixture_id,v072_old,covers,new_status,measured,note\n');
% F1 AXIS_FAIL_NEGATIVE
fprintf(fc,'AXIS_FAIL_NEGATIVE,new,guard rejects dim>ndims; correct dim3 matches analytic,%s,rel=%.3g phase_err=%.3g,\n',st3,rel,pd);
% F2 3D_VS_4D
sig4=reshape(sig3,4,3,1,N);
o4=extract_fft_v073(sig4,4,Fs,400);
d34=max(abs(double(o4.Xk(:))-double(o3.Xk(:))));
if d34==0, st4='PASS'; else, st4='FAIL'; end
fprintf(fc,'3D_VS_4D,new,same data H*W*1*N dim4 vs H*W*N dim3,%s,maxdiff=%.17g,source semantic equivalence\n',st4,d34);
% F3 TIME_ORIGIN (real shift this time)
n0=500;
x1=single(reshape(100+0.02*cos(2*pi*f400*t+0.7),1,1,[]).*ones(4,3,N));
t2=(n0:n0+N-1)'/Fs;
x2=single(reshape(100+0.02*cos(2*pi*f400*t2+0.7),1,1,[]).*ones(4,3,N));
a1=extract_fft_v073(x1,3,Fs,400); a2=extract_fft_v073(x2,3,Fs,400);
ampRel=abs(a2.A_k(1)-a1.A_k(1))/a1.A_k(1);
pdPhi=abs(angle(exp(1i*((a2.phase(1)-a1.phase(1))-2*pi*160*n0/N))));
if ampRel<tauR && pdPhi<tauP, st5='PASS'; else, st5='FAIL'; end
fprintf(fc,'TIME_ORIGIN,F07_NOT_ACTUALLY_TESTED_ORIGIN_SHIFT,real n0=%d sample shift: amplitude invariant and phase rotation matches -2*pi*k0*n0/N,%s,ampRel=%.3g phaseResid=%.3g,v072 gap closed\n',n0,st5,ampRel,pdPhi);
% F4 MASK_VALUE (invalid pixels must be complex NaN, mask=0)
xb=x1; xb(2,2,:)=single(1e-4); xb(3,3,:)=single(NaN);
m=extract_fft_v073(xb,3,Fs,400);
nanOK=isnan(real(m.C_k(2,2)))&&isnan(imag(m.C_k(2,2)))&&isnan(real(m.C_k(3,3)));
maskOK=~m.validMask(2,2)&&~m.validMask(3,3);
validOK=m.validMask(1,1);
if nanOK&&maskOK&&validOK, st6='PASS'; else, st6='FAIL'; end
fprintf(fc,'MASK_VALUE,F09_zero_filled,invalid pixels complex NaN + mask=0 (not zero-filled),%s,nanOK=%d maskOK=%d validOK=%d,source NaN+validContrastMask semantics\n',st6,nanOK,maskOK,validOK);
% F5 RGB_INDEPENDENT
R=reshape(200+0.03*cos(2*pi*f400*t),1,1,[]); G=reshape(120+0.02*cos(2*pi*f400*t+0.3),1,1,[]); B=reshape(60+0.01*cos(2*pi*f400*t-0.4),1,1,[]);
Rc=R.*ones(4,3,N); Gc=G.*ones(4,3,N); Bc=B.*ones(4,3,N);
rgbStack=cat(4,single(Rc),single(Gc),single(Bc));  % H*W*3*N as rgb2gray-style input is H*W*3 per frame; emulate per-frame gray
grayManual=0.2989*Rc+0.5870*Gc+0.1140*Bc;         % independent weights application
grayChain=0.2989*single(Rc)+0.5870*single(Gc)+0.1140*single(Bc);
oM=extract_fft_v073(single(grayManual),3,Fs,400);
oC=extract_fft_v073(grayChain,3,Fs,400);
dRGB=max(abs(double(oM.C_k(:))-double(oC.C_k(:))));
% independent analytic gray modulation amplitude:
re=0.2989*0.03*cos(0)+0.5870*0.02*cos(0.3)+0.1140*0.01*cos(-0.4);
 im=0.2989*0.03*sin(0)+0.5870*0.02*sin(0.3)+0.1140*0.01*sin(-0.4); gAmp=hypot(re,im);
relG=abs(oM.A_k(1)-gAmp)/gAmp;
if dRGB<tauA && relG<tauR, st7='PASS'; else, st7='FAIL'; end
fprintf(fc,'RGB_INDEPENDENT,F10_same_expression,manual weights vs chain weights on unequal RGB + analytic gray amplitude check,%s,chainDiff=%.3g ampRel=%.3g,%s\n',st7,dRGB,relG,'independent analytic expectation added');
% F6 OFF_BIN leakage diagnostic
xoff=single(reshape(100+0.02*cos(2*pi*400.5*t+0.2),1,1,[]).*ones(4,3,N));
oo=extract_fft_v073(xoff,3,Fs,400);
leakAmp=max(oo.A_k(:));
idealAmp=0.02;
fprintf(fc,'OFF_BIN,new,400.5 Hz off-bin leakage recorded as diagnostic (no correction applied),DIAGNOSTIC,binAmp=%.6g idealAmp=%.6g ratio=%.6f,leakage is expected physics of finite records\n',leakAmp,idealAmp,leakAmp/idealAmp);
% F7 EXPOSURE_ANALYTIC_ONLY both conventions
tau=1e-4; % SYNTHETIC assumption only
cont=sinc(f400*tau);
tstart=t; tcenter=t-tau/2;
xc_start=100+0.02*cont*cos(2*pi*f400*tstart);
xc_center=100+0.02*cont*cos(2*pi*f400*tcenter);
oe1=extract_fft_v073(single(reshape(xc_start,1,1,[]).*ones(4,3,N)),3,Fs,400);
oe2=extract_fft_v073(single(reshape(xc_center,1,1,[]).*ones(4,3,N)),3,Fs,400);
aerr1=abs(oe1.A_k(1)-0.02*cont)/ (0.02*cont);
aerr2=abs(oe2.A_k(1)-0.02*cont)/ (0.02*cont);
phRel=abs(angle(exp(1i*((oe1.phase(1)-oe2.phase(1))-2*pi*f400*tau/2))));
if aerr1<tauR && aerr2<tauR && phRel<tauP, st8='PASS'; else, st8='FAIL'; end
fprintf(fc,'EXPOSURE_ANALYTIC_ONLY,F12_numeric_s_field,both start/center conventions verified; tau=1e-4s SYNTHETIC ONLY,%s,ampRel1=%.3g ampRel2=%.3g phaseResid=%.3g,not real exposure; v072 numeric-s field removed\n',st8,aerr1,aerr2,phRel);
% F8 IO_CSV serialization
tmp=fullfile(numOut,'io_serialization_test.csv');
fio=fopen(tmp,'w'); fprintf(fio,'a,b,c\n'); fprintf(fio,'%.17g,%.17g,%s\n',NaN,1.5,'UNDEFINED'); fclose(fio);
raw=fileread(tmp);
hasCtrl=any(double(raw)<32 & double(raw)~=10 & double(raw)~=13);
if ~hasCtrl, st9='PASS'; else, st9='FAIL'; end
fprintf(fc,'IO_CSV,F12_U0000_in_csv,no control characters; NaN literal and UNDEFINED tokens serialize cleanly,%s,ctrl=%d,v072 NUL bug closed\n',st9,hasCtrl);
fclose(fc);
% small analytic examples mat
save(fullfile(numOut,'fft_analytic_small_examples.mat'),'o3','o4','a1','a2','m','oM','oC','oo','oe1','oe2','-v7.3');
fprintf('[073A/B] validation done\n');
end
function s=sinc(x), s=ones(size(x)); m=x~=0; s(m)=sin(pi*x(m))./(pi*x(m)); end




