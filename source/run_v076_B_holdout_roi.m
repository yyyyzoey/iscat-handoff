function run_v076_B_holdout_roi(outRoot, v075Root)
% v076 B: correct 41x41 physical-pixel camera ROI (fine 61:265) postprocessing of the
% 24 cached holdout states. Zero renders. Legacy 64:268 values kept as history only.
if nargin<2||isempty(v075Root), v075Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
H=load(fullfile(v075Root,'numeric','v075_holdout_data.mat'));
fn=fieldnames(H);
% exact 24-key set guard (no empty-true gate)
assert(numel(fn)==24,'v076B: expected exactly 24 holdout records, got %d',numel(fn));
i0=61; i1=265; q=5;
hf=fopen(fullfile(tabDir,'v076_holdout_camera_roi.csv'),'w');
fprintf(hf,'D_nm,zf_nm,dx_nm,Itot_roi_relL2,center_Itot_absdiff,S_area_nm2_absdiff_direct,S_area_nm2_absdiff_interp,C33_direct,C33_interp,Esca_relL2_full_carry,note\n');
roiMaps=struct();
for k=1:numel(fn)
  rec=H.(fn{k});
  % parse D/zf/dx from the v075 key D<dn>_ZF<zf>_X<MP><pm>
  tok=regexp(fn{k},'D(\d+)_ZF(\d+)_X([MP])(\d+)','tokens','once');
  D=str2double(tok{1}); zf=str2double(tok{2}); dxpm=str2double(tok{4});
  dx=dxpm/1000; if strcmp(tok{3},'M'), dx=-dx; end
  Ed=rec.Es_direct; Ei=rec.Es_interp; Er=rec.Eref;
  ItD=sum(abs(Er+Ed).^2,3); ItI=sum(abs(Er+Ei).^2,3);
  IsD=sum(abs(Ed).^2,3); IsI=sum(abs(Ei).^2,3);
  IiD=2*real(sum(conj(Er).*Ed,3)); IiI=2*real(sum(conj(Er).*Ei,3));
  I0=sum(abs(Er).^2,3);
  % correct physical ROI (fine 61:265 -> pixels 13:53)
  ItDp=reshape(pixel_mean(ItD(i0:i1,i0:i1),q),41,41);
  ItIp=reshape(pixel_mean(ItI(i0:i1,i0:i1),q),41,41);
  I0p=reshape(pixel_mean(I0(i0:i1,i0:i1),q),41,41);
  IsDp=reshape(pixel_mean(IsD(i0:i1,i0:i1),q),41,41); IsIp=reshape(pixel_mean(IsI(i0:i1,i0:i1),q),41,41);
  IiDp=reshape(pixel_mean(IiD(i0:i1,i0:i1),q),41,41); IiIp=reshape(pixel_mean(IiI(i0:i1,i0:i1),q),41,41);
  CD=(ItDp-I0p)./I0p; CI=(ItIp-I0p)./I0p;
  relIt=norm(ItIp(:)-ItDp(:))/max(norm(ItDp(:)),realmin);
  cD=ItDp(21,21); cI=ItIp(21,21);
  sD=4225*sum(CD(:)); sI=4225*sum(CI(:));
  fprintf(hf,'%d,%g,%g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,CAMERA_ROI_41x41_correct_centre\n', ...
    D,zf,dx,relIt,abs(cD-cI),abs(sD-sI),abs(sD-sI),CD(21,21),CI(21,21),rec.relEs);
  roiMaps.(matlab.lang.makeValidName(fn{k}))=struct('CD',CD,'CI',CI,'IsDp',IsDp,'IiDp',IiDp,'I0p',I0p,'D',D,'zf',zf,'dx',dx);
end
fclose(hf);
save(fullfile(numOut,'v076_holdout_camera_roi_maps.mat'),'-struct','roiMaps','-v7.3');
fprintf('[076B] done: 24 holdout camera-ROI postprocessing (zero renders)\n');
end
