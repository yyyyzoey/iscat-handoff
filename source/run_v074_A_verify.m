function run_v074_A_verify(outRoot, v073Root)
% v074 A: replay identity closeout - read saved v073 FFT artifacts, re-verify
% table numbers from stored arrays, rejection tests. No 2001-frame recompute, no BEM.
if nargin<2||isempty(v073Root), v073Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v073_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
F=load(fullfile(v073Root,'numeric','fft400_corrected_full.mat'));
fprintf('[074A] loaded full-field C400 artifact: absC %dx%d\n',size(F.absC,1),size(F.absC,2));
fid=fopen(fullfile(tabDir,'v074_replay_identity_verification.csv'),'w');
fprintf(fid,'check,expected,recomputed,status,note\n');
nValid=nnz(F.validMask); nTot=numel(F.validMask); nInv=nTot-nValid;
fprintf(fid,'valid_pixels,93179,%d,%s,recomputed from stored validMask\n',nValid,tern(nValid==93179,'PASS','FAIL'));
fprintf(fid,'invalid_pixels,11013,%d,%s,complex NaN preserved in stored C_k\n',nInv,tern(nInv==11013,'PASS','FAIL'));
fprintf(fid,'total_pixels,104192,%d,%s,\n',nTot,tern(nTot==104192,'PASS','FAIL'));
nanOK=nnz(isnan(real(F.C_k(~F.validMask))))==nInv && nnz(isnan(imag(F.C_k(~F.validMask))))==nInv;
fprintf(fid,'invalid_stored_as_nan,true,%d,%s,not zero-filled\n',nanOK,tern(nanOK,'PASS','FAIL'));
br=nnz(F.absC(F.validMask)>=1e-3);
fprintf(fid,'BRIGHT_PIXELS_DIAGNOSTIC,82749,%d,%s,|C400|>=1e-3 valid pixels; NOT particle detections\n',br,tern(br==82749,'PASS','FAIL'));
medA=median(F.absC(F.validMask)); meanA=mean(F.absC(F.validMask),'all'); maxA=max(F.absC(F.validMask));
fprintf(fid,'absC400_median,0.00659665...,%.17g,%s,\n',medA,tern(abs(medA-0.0065966537222266197)<1e-12,'PASS','FAIL'));
fprintf(fid,'absC400_mean,0.0239810...,%.17g,%s,\n',meanA,tern(abs(meanA-0.023981023579835892)<1e-12,'PASS','FAIL'));
fprintf(fid,'absC400_max,0.9018655...,%.17g,%s,\n',maxA,tern(abs(maxA-0.90186554193496704)<1e-9,'PASS','FAIL'));
fprintf(fid,'meanFloor,1.1761607311200351e-4,%.17g,%s,\n',F.meanFloor,tern(F.meanFloor==0.00011761607311200351,'PASS','FAIL'));
fprintf(fid,'actualFreq400,399.80009995002496,%.17g,%s,\n',F.actualFreq,tern(abs(F.actualFreq-399.80009995002496)<1e-9,'PASS','FAIL'));
fclose(fid);
% ROI neighborhood ratio re-check from full field (center ROI rows 128:168 cols 156:196)
R=load(fullfile(v073Root,'numeric','fft400_corrected_small_roi.mat'));
fprintf('[074A] small ROI loaded: %dx%d frames=%d\n',size(R.roiFrames,1),size(R.roiFrames,2),size(R.roiFrames,4));
% rejection tests (no original frames needed)
rf=fopen(fullfile(tabDir,'v074_reject_tests.csv'),'w');
fprintf(rf,'reject_id,scheme,expected,observed,status\n');
% R1 wrong time dim guard on 3-D ROI frames
caught='';
try
  extract_fft_v073(R.roiFrames,4,5000,400); % roiFrames is 4-D H*W*1*N -> this one is VALID; use squeezed for negative
  r1='NO_ERROR'; st1='FAIL';
catch ME
  r1=ME.identifier; st1='FAIL';
end
% proper negative: squeeze to 3-D then ask dim4 -> must throw
s3=reshape(R.roiFrames,size(R.roiFrames,1),size(R.roiFrames,2),[]);
try
  extract_fft_v073(s3,4,5000,400); r1='NO_ERROR'; st1='FAIL';
catch ME
  r1=ME.identifier; st1='PASS';
end
fprintf(rf,'R1_wrong_time_dim,extract(squeezed3D,timeDim=4),error BAD_TIME_DIM,%s,%s\n',r1,st1);
% R2 wrong bin (169 as 400)
oWrong=extract_fft_v073(s3,3,5000,420);
oRight=R;
% recompute correct X from stored frames at bin 161 and compare with stored X400
Xchk=extract_fft_v073(s3,3,5000,400);
b2=double(squeeze(R.X400)); dX=max(abs(double(Xchk.Xk(:))-b2(:)));
fprintf(rf,'R2_recompute_matches_stored,dim3 bin161 vs stored X400,maxdiff<1e-6,%.17g,%s\n',dX,tern(dX<1e-6,'PASS','FAIL'));
fprintf(rf,'R2b_wrong_bin_not_used,bin169 vs stored X400,maxdiff large,%s,%s\n', ...
  sprintf('%.3g',max(abs(double(oWrong.Xk(:))-b2(:)))),tern(max(abs(double(oWrong.Xk(:))-b2(:)))>1e-6,'PASS','FAIL'));
% R3 zero-filling invalid pixels must change results
Cz=F.C_k; Cz(~F.validMask)=0;
zdiff=double(~isequaln(Cz,F.C_k));
fprintf(rf,'R3_zero_fill_detected,zero-fill invalid pixels,stored array changes (NaN!=0),%d,%s\n',zdiff,tern(zdiff==1,'PASS','FAIL'));
% R4 ROI-local threshold differs from full-field (must not be substituted)
oRoiLocal=extract_fft_v073(s3,3,5000,400);
fprintf(rf,'R4_roi_local_floor_differs,ROI-local median vs full-field meanFloor,different values preserved,%.17g vs %.17g,%s\n', ...
  oRoiLocal.meanFloor,F.meanFloor,tern(oRoiLocal.meanFloor~=F.meanFloor,'PASS','FAIL'));
% R5 row/col swap detection: transposed ROI frames vs stored
oT=extract_fft_v073(permute(s3,[2 1 3]),3,5000,400);
dT=max(abs(double(oT.Xk(:))-b2(:)));
fprintf(rf,'R5_transpose_detected,transposed ROI frames vs stored X400,maxdiff>0,%s,%s\n',sprintf('%.3g',dT),tern(dT>0,'PASS','FAIL'));
fclose(rf);
% small numeric: keep verified ROI recompute for later stages
save(fullfile(numOut,'v074_roi_recheck.mat'),'Xchk','oWrong','oRoiLocal','-v7.3');
fprintf('[074A] done\n');
end
function out=tern(c,a,b), if c, out=a; else, out=b; end, end




