function run_v073_verify_recheck(outRoot)
% Independent-session recheck: small-ROI frames only, no full stack, no original run state.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v073_return'; end
tabDir=fullfile(outRoot,'tables'); numOut=fullfile(outRoot,'numeric');
S=load(fullfile(numOut,'fft400_corrected_small_roi.mat'));
rf=S.roiFrames; N=size(rf,4); Fs=S.Fs;
assert(N==2001);
% 3-D path on squeezed ROI
s3=reshape(rf,size(rf,1),size(rf,2),N);
o3=extract_fft_v073(s3,3,Fs,400);
% 4-D path (source-script layout)
o4=extract_fft_v073(rf,4,Fs,400);
d34=max(abs(double(o3.Xk(:))-double(o4.Xk(:))));
d34st=abs(double(o3.Xk(:))-double(S.X400(:)));
dStored=max(d34st(:));
% direct DFT at the 4 ROI corners (rows/cols 1 and 41)
corners=[1 1;1 41;41 1;41 41];
vf=fopen(fullfile(tabDir,'fft_replay_direct_dft_checks_recheck.csv'),'w');
fprintf(vf,'check,value,threshold,status\n');
ok=true;
fprintf(vf,'roi_3d_vs_4d_maxdiff,%.17g,0,%s\n',d34,tern(d34==0,'PASS','FAIL')); ok=ok&&d34==0;
fprintf(vf,'roi_vs_stored_fullfield_maxdiff,%.17g,1e-6,%s\n',dStored,tern(dStored<1e-6,'PASS','FAIL')); ok=ok&&dStored<1e-6;
for c=1:4
  xpix=double(s3(corners(c,1),corners(c,2),:)); xpix=xpix-mean(xpix);
  Xd=sum(xpix(:).*exp(-2i*pi*160*(0:N-1)'/N));
  Xf=double(o3.Xk(corners(c,1),corners(c,2)));
  rel=abs(Xf-Xd)/max(abs(Xd),realmin);
  fprintf(vf,'roi_corner_%d_directDFT_rel,%.17g,1e-5,%s\n',c,rel,tern(rel<1e-5,'PASS','FAIL')); ok=ok&&rel<1e-5;
end
% meanFloor: ROI-local median legitimately differs from the stored full-image median -> EXPECTED_DIFFERENCE
fprintf(vf,'meanFloor_roi_local_vs_fullfield,%.17g,%.17g,EXPECTED_DIFFERENCE\n',o3.meanFloor,S.meanFloor);
% C_k formula consistency against STORED full-image mask/meanFloor semantics
Cchk=complex(nan(size(o3.Imean),'single'),nan(size(o3.Imean),'single'));
Cchk(S.validMask)=2*o3.Xk(S.validMask)./(N*S.Imean(S.validMask));
cerr=max(abs(Cchk(:)-double(S.C400(:))));
fprintf(vf,'Ck_formula_vs_stored_maxdiff,%.17g,1e-6,%s\n',cerr,tern(cerr<1e-6,'PASS','FAIL')); ok=ok&&cerr<1e-6;
fclose(vf);
if ok, fprintf('[073V] RECHECK PASS (independent session)\n'); else, fprintf('[073V] RECHECK FAIL\n'); end
end
function out=tern(c,a,b), if c, out=a; else, out=b; end, end

