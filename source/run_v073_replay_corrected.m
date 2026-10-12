function run_v073_replay_corrected(outRoot)
% v073 C: corrected single replay of the SAME 2001 frames (frames 1000-3000 of
% the 7.29 batch), 4-D layout exactly like the original scripts, dim-4 FFT.
% Primary observable: 400 Hz normalized complex modulation contrast (test_with_contrast.m).
% Control channel: 420 Hz (test.m semantics), same FFT pass. No BEM. No upload.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v073_return'; end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
folder='C:\Users\PC\Desktop\课题\7.29\7.29\BMP100053022-20260729-105610';
Fs=5000; startFrame=1000; endFrame=3000;
allFiles=dir(fullfile(folder,'*.bmp')); allFiles=sortBmp(allFiles);
total=numel(allFiles); assert(total>=3000,'batch too small');
files=allFiles(startFrame:endFrame); N=numel(files); assert(N==2001);
fprintf('[073C] batch=%d frames; using %d..%d (N=%d): %s .. %s\n',total,startFrame,endFrame,N,files(1).name,files(end).name);
% read into 4-D H x W x 1 x N single (source-script layout)
[img,map]=imread(fullfile(folder,files(1).name));
if ~isempty(map), img=ind2rgb(img,map); end
img=im2single(img);
if size(img,3)==3, img=0.2989*img(:,:,1)+0.5870*img(:,:,2)+0.1140*img(:,:,3); end
[H,W]=size(img);
stack=zeros(H,W,1,N,'single'); stack(:,:,1,1)=img;
t0=tic;
for n=2:N
  [im,m]=imread(fullfile(folder,files(n).name));
  if ~isempty(m), im=ind2rgb(im,m); end
  im=im2single(im);
  if size(im,3)==3, im=0.2989*im(:,:,1)+0.5870*im(:,:,2)+0.1140*im(:,:,3); end
  stack(:,:,1,n)=im;
  if mod(n,500)==0, fprintf('[073C] read %d/%d (%.1fs)\n',n,N,toc(t0)); end
end
fprintf('[073C] stack %.1fs  size=%dx%dx1x%d\n',toc(t0),H,W,N);
% primary + control from ONE correct time FFT
t1=tic;
P=extract_fft_v073(stack,4,Fs,400);   % 400 Hz normalized complex contrast (primary)
T=extract_fft_v073(stack,4,Fs,420);   % 420 Hz control (same pass, separate label)
fprintf('[073C] fft %.1fs; actualFreq400=%.6f actualFreq420=%.6f\n',toc(t1),P.actualFreq,T.actualFreq);
assert(abs(P.actualFreq-399.80009995002496)<1e-9);
assert(abs(T.actualFreq-419.79010494752623)<1e-9);
% full arrays workstation-only
meta=struct('folder',folder,'files_first',files(1).name,'files_last',files(end).name, ...
  'startFrame',startFrame,'endFrame',endFrame,'N',N,'Fs',Fs,'H',H,'W',W, ...
  'layout','HxWx1xN single, fft dim4','extractor','extract_fft_v073.m');
P.meta=meta; save(fullfile(numOut,'fft400_corrected_full.mat'),'-struct','P','-v7.3');
T.meta=meta; save(fullfile(numOut,'fft420_control_full.mat'),'-struct','T','-v7.3');
% 41x41 center ROI (small mat incl. frames for independent recheck)
r0=floor(H/2)-20; c0=floor(W/2)-20; ri=r0:(r0+40); ci=c0:(c0+40);
roiFrames=stack(ri,ci,:,:);
roi=struct('rows',ri(1),'cols',ci(1),'roiFrames',roiFrames, ...
  'X400',P.Xk(ri,ci),'C400',P.C_k(ri,ci),'absC400',P.absC(ri,ci),'phase400',P.phase(ri,ci), ...
  'Imean',P.Imean(ri,ci),'validMask',P.validMask(ri,ci),'meanFloor',P.meanFloor, ...
  'k',P.k,'actualFreq',P.actualFreq,'Fs',Fs,'N',N,'layout_tag','CORRECTED_FFT_TIME_DIM');
roi.meta=meta; save(fullfile(numOut,'fft400_corrected_small_roi.mat'),'-struct','roi','-v7.3');
roiT=struct('rows',ri(1),'cols',ci(1),'X420',T.Xk(ri,ci),'A420',T.A_k(ri,ci), ...
  'phase420',T.phase(ri,ci),'k',T.k,'actualFreq',T.actualFreq);
roiT.meta=meta; save(fullfile(numOut,'fft420_control_small_roi.mat'),'-struct','roiT','-v7.3');
% 12 predeclared pixels: 4 corners, center, ROI corners, highest/lowest valid Imean, highest |C400| valid
ImeanV=P.Imean; mv=ImeanV; mv(~P.validMask)=-Inf; [~,iHigh]=max(mv(:));
ml=P.Imean; ml(~P.validMask)=Inf;  [~,iLow]=min(ml(:));
ac=P.absC; ac(~P.validMask)=0; [~,iBright]=max(ac(:));
[ihr,ihc]=ind2sub([H,W],iHigh); [ilr,ilc]=ind2sub([H,W],iLow); [ibr,ibc]=ind2sub([H,W],iBright);
pix=[1 1;1 W;H 1;H W; r0+20 c0+20; ri(1) ci(1); ri(1) ci(41); ri(41) ci(1); ri(41) ci(41); ihr ihc; ilr ilc; ibr ibc];
% direct DFT (double, explicit sum) at the 12 pixels
Xref=zeros(12,1,'like',complex(0,0));
t2=tic;
for p2=1:12
  xpix=double(stack(pix(p2,1),pix(p2,2),1,:)); xpix=xpix-mean(xpix);
  Xref(p2)=sum(xpix(:).*exp(-2i*pi*P.k0*(0:N-1)'/N));
end
fprintf('[073C] direct DFT 12 px %.1fs\n',toc(t2));
[ImeanD,Xfft]=gatherPix(P,pix);
Cref=2*Xref./(N*ImeanD); Cfft=2*Xfft./(N*ImeanD);
cf=fopen(fullfile(tabDir,'fft_replay_direct_dft_checks.csv'),'w');
fprintf(cf,'pixel_id,row,col,kind,Xfft_real,Xfft_imag,Xdft_real,Xdft_imag,abs_diff,rel_err,phase_diff,status\n');
for p2=1:12
  if p2<=4, kd='corner'; elseif p2==5, kd='center'; elseif p2<=9, kd='roi_corner'; elseif p2==10, kd='high_Imean'; elseif p2==11, kd='low_Imean_valid'; else, kd='bright_absC_valid'; end
  ad=abs(Xfft(p2)-Xref(p2)); re=ad/max(abs(Xref(p2)),realmin);
  if abs(Cref(p2))>1e-6
    pd=abs(angle(exp(1i*(atan2(imag(Xfft(p2)),real(Xfft(p2)))-atan2(imag(Xref(p2)),real(Xref(p2))))))); pst='PHASE_CHECKED';
  else
    pd=NaN; pst='PHASE_UNDEFINED_NEAR_ZERO';
  end
  if re<1e-5 || ad<1e-7, st='PASS'; else, st='FAIL'; end
  fprintf(cf,'px%02d,%d,%d,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%s\n', ...
    p2,pix(p2,1),pix(p2,2),kd,real(Xfft(p2)),imag(Xfft(p2)),real(Xref(p2)),imag(Xref(p2)),ad,re,pd,st);
end
fclose(cf);
% spectral neighborhood (fixed bins k=158:164 plus 420 bin 169) on the ROI
Fr=fft(double(roiFrames)-double(mean(roiFrames,4)),[],4);
nb=158:164;
ampNB=squeeze(mean(abs(Fr(:,:,1,nb)),[1 2]));
amp169=squeeze(mean(abs(Fr(:,:,1,169)),[1 2]));
sf=fopen(fullfile(tabDir,'fft_spectral_neighborhood.csv'),'w');
fprintf(sf,'k_matlab,k0,actualFreq_Hz,roi_mean_absX,note\n');
for b=1:numel(nb)
  fprintf(sf,'%d,%d,%.6f,%.17g,%s\n',nb(b),nb(b)-1,(nb(b)-1)*Fs/N,ampNB(b),'fixed neighborhood of 400 Hz bin; ASSOCIATION_ONLY_NOT_CAUSAL_MAGNETIC_SIGNAL');
end
fprintf(sf,'169,168,%.6f,%.17g,%s\n',T.actualFreq,amp169,'420 control bin');
fclose(sf);
% mask / quality summary (valid-only statistics; invalid pixels are NaN, not zero)
mf=fopen(fullfile(tabDir,'fft_mask_and_quality.csv'),'w');
fprintf(mf,'metric,value,note\n');
fprintf(mf,'total_pixels,%d,%dx%d\n',H*W,H,W);
fprintf(mf,'valid_pixels,%d,validMask from meanFloor=0.01*median positive Imean\n',nnz(P.validMask));
fprintf(mf,'invalid_pixels,%d,complex NaN stored (NOT zero)\n',H*W-nnz(P.validMask));
fprintf(mf,'valid_fraction,%.6f,\n',nnz(P.validMask)/(H*W));
fprintf(mf,'meanFloor,%.17g,0.01 x median(Imean(Imean>0&finite))\n',P.meanFloor);
fprintf(mf,'Imean_valid_min,%.17g,\n',min(P.Imean(P.validMask)));
fprintf(mf,'Imean_valid_median,%.17g,\n',median(P.Imean(P.validMask)));
fprintf(mf,'Imean_valid_max,%.17g,\n',max(P.Imean(P.validMask)));
fprintf(mf,'absC400_valid_min,%.17g,\n',min(P.absC(P.validMask)));
fprintf(mf,'absC400_valid_median,%.17g,\n',median(P.absC(P.validMask)));
fprintf(mf,'absC400_valid_mean,%.17g,valid-only mean\n',mean(P.absC(P.validMask),'all'));
fprintf(mf,'absC400_valid_max,%.17g,\n',max(P.absC(P.validMask)));
fprintf(mf,'absC400_valid_ge_1e-3,%d,candidate-bright pixel count (diagnostic only)\n',nnz(P.absC(P.validMask)>=1e-3));
fprintf(mf,'actualFreq400,%.6f,bin %d\n',P.actualFreq,P.k);
fprintf(mf,'actualFreq420,%.6f,bin %d (control)\n',T.actualFreq,T.k);
fprintf(mf,'status,REAL_400_HZ_OBSERVABLE_COMPUTED,calibration_valid=false; experimental_validation=false\n');
fclose(mf);
fprintf('[073C] corrected replay done\n');
end
function [ImeanD,Xfft]=gatherPix(P,pix)
H=size(P.Imean,1);
for p2=1:size(pix,1)
  ImeanD(p2)=double(P.Imean(pix(p2,1),pix(p2,2)));
  Xfft(p2)=double(P.Xk(pix(p2,1),pix(p2,2)));
end
end
function sorted=sortBmp(files)
fn={files.name}; nums=nan(numel(fn),1);
for k=1:numel(fn)
  tok=regexp(fn{k},'\d+','match');
  if ~isempty(tok), nums(k)=str2double(tok{end}); end
end
if all(~isnan(nums)), [~,o]=sort(nums); else, [~,o]=sort(lower(fn)); end
sorted=files(o);
end





