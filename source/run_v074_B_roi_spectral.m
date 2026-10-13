function run_v074_B_roi_spectral(outRoot, v073Root)
% v074 B: predeclared ROI selection from v073 full-field |C400|/Imean ONLY, then ONE
% read-only 2001-frame scan; per-ROI multi-bin contrast (k=158:164,169) with the
% SAME full-image meanFloor/validMask and 2/(N*Imean) normalization.
if nargin<2||isempty(v073Root), v073Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v073_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
F=load(fullfile(v073Root,'numeric','fft400_corrected_full.mat'));
H=296; W=352; L=41;
folder='C:\Users\PC\Desktop\课题\7.29\7.29\BMP100053022-20260729-105610';
% ---------- B0: predeclared ROI selection (uses only |C400|, Imean, mask) ----------
roiList={};  % {name, r0, c0, kind}
roiList(end+1,:)={'CENTER',128,156,'CENTER_REUSED'}; %#ok<AGROW>
% hotspots: top |C400| valid local maxima, separated >=L in both dims, excluding center box
A=F.absC; A(~F.validMask)=-Inf;
Ablk=A; Ablk(118:178,146:206)=-Inf;  % exclude center neighborhood
sel=[];
for k=1:3
  [~,idx]=max(Ablk(:)); [r,c]=ind2sub([H,W],idx);
  if Ablk(idx)<0, break; end
  roiList(end+1,:)={sprintf('HOTSPOT%d',k),max(1,min(H-L+1,r-20)),max(1,min(W-L+1,c-20)),'C400_HOTSPOT'}; %#ok<AGROW>
  Ablk(max(1,r-L+1):min(H,r+L-1),max(1,c-L+1):min(W,c+L-1))=-Inf;
end
% background candidates: Imean near hotspot-median level, lowest mean |C400| in window, separated
hv=[]; for k2=2:size(roiList,1)
  r0=roiList{k2,2}; c0=roiList{k2,3};
  hv(end+1)=median(F.Imean(max(1,r0):min(H,r0+L-1),max(1,c0):min(W,c0+L-1)),'all'); %#ok<AGROW>
end
ImTgt=median(hv);
score=F.Imean; w=F.validMask & abs(F.Imean-ImTgt)<0.2*ImTgt & F.Imean>0;
candScore=Inf(H,W); candScore(w)=F.absC(w);
candScore(118:178,146:206)=Inf; % exclude center
% exclude existing hotspot boxes
for k2=2:size(roiList,1)
  r0=roiList{k2,2}; c0=roiList{k2,3}; candScore(max(1,r0-L+1):min(H,r0+L-1),max(1,c0-L+1):min(W,c0+L-1))=Inf;
end
for k=1:3
  [~,idx]=min(candScore(:)); [r,c]=ind2sub([H,W],idx);
  if ~isfinite(candScore(idx)), break; end
  roiList(end+1,:)={sprintf('BACKGROUND%d',k),max(1,min(H-L+1,r-20)),max(1,min(W-L+1,c-20)),'BACKGROUND_CANDIDATE'}; %#ok<AGROW>
  candScore(max(1,r-L+1):min(H,r+L-1),max(1,c-L+1):min(W,c+L-1))=Inf;
end
% edge artifact ROI: lowest-Imean border corner region (bottom-left)
edgeScore=F.Imean; edgeScore(1:H-60,1:W-60)=Inf; [~,idx]=min(edgeScore(:)); [r,c]=ind2sub([H,W],idx);
roiList(end+1,:)={'EDGE_LOWLIGHT',max(1,min(H-L+1,r-20)),max(1,min(W-L+1,c-20)),'EDGE_ARTIFACT_DIAG'}; %#ok<AGROW>
fprintf('[074B] selected %d ROIs\n',size(roiList,1));
% selection log (before any neighbor-bin computation)
sl=fopen(fullfile(tabDir,'v074_roi_selection_log.csv'),'w');
fprintf(sl,'roi_name,row0,col0,kind,roi_size,valid_fraction,median_Imean,median_absC_valid,selection_rule\n');
for k=1:size(roiList,1)
  r0=roiList{k,2}; c0=roiList{k,3}; ri=r0:(r0+L-1); ci=c0:(c0+L-1);
  vm=F.validMask(ri,ci); mi=median(F.Imean(ri,ci),'all'); ma=median(F.absC(ri,ci),'all');
  fprintf(sl,'%s,%d,%d,%s,%dx%d,%.6f,%.17g,%.17g,%s\n',roiList{k,1},r0,c0,roiList{k,4},L,L,nnz(vm)/(L*L),mi,ma, ...
    'predeclared from v073 full-field |C400|/Imean/validMask only; no neighbor-bin data used');
end
fclose(sl);
% ---------- one 2001-frame scan for the 7 non-center ROIs ----------
nonCenter=roiList(2:end,:);
nR=size(nonCenter,1); N=2001; Fs=5000;
stacks=cell(1,nR); for k=1:nR, stacks{k}=zeros(L,L,1,N,'single'); end
allFiles=dir(fullfile(folder,'*.bmp')); allFiles=sortBmp(allFiles);
files=allFiles(1000:3000);
t0=tic;
for n=1:N
  [im,m]=imread(fullfile(folder,files(n).name));
  if ~isempty(m), im=ind2rgb(im,m); end
  im=im2single(im);
  if size(im,3)==3, im=0.2989*im(:,:,1)+0.5870*im(:,:,2)+0.1140*im(:,:,3); end
  for k=1:nR
    r0=nonCenter{k,2}; c0=nonCenter{k,3};
    stacks{k}(:,:,1,n)=im(r0:(r0+L-1),c0:(c0+L-1));
  end
  if mod(n,500)==0, fprintf('[074B] scan %d/%d (%.1fs)\n',n,N,toc(t0)); end
end
fprintf('[074B] scan done %.1fs\n',toc(t0));
% ---------- multi-bin contrast per ROI (same full-image mask/meanFloor/normalization) ----------
kb=158:169; % MATLAB bins incl. 420 control at 169; neighborhood median uses 158:164 excluding 161
sf=fopen(fullfile(tabDir,'v074_roi_spectral.csv'),'w');
fprintf(sf,'roi_name,row0,col0,kind,k_matlab,k0,actualFreq_Hz,A_k_median_valid,A_k_mean_valid,Rlocal_median_valid,Rlocal_mean_valid,frac_Rlocal_gt_1p2,frac_Rlocal_gt_1p5,frac_Rlocal_gt_2,compact_pixels_gt3x_roi_median,phase_circstd_deg_strong,near_sat_Imean_frac,note\n');
roiMaps=struct();
for k=1:size(roiList,1)
  name=roiList{k,1}; r0=roiList{k,2}; c0=roiList{k,3};
  if k==1
    R=load(fullfile(v073Root,'numeric','fft400_corrected_small_roi.mat'));
    X=zeros(L,L,numel(kb),'single');
    Im=R.Imean; vm=R.validMask;
    % recompute neighborhood bins from cached ROI frames (no new BMP read)
    Fc=fft(double(R.roiFrames)-double(mean(R.roiFrames,4)),[],4);
  else
    idx=find(strcmp(roiList(2:end,1),name));
    Sk=stacks{idx};
    Fc=fft(double(Sk)-double(mean(Sk,4)),[],4);
    Im=mean(Sk,4); Im=squeeze(Im); vm=F.validMask(r0:(r0+L-1),c0:(c0+L-1)) & isfinite(Im) & Im>F.meanFloor;
  end
  Ak=zeros(L,L,numel(kb));
  for b=1:numel(kb)
    idxc=cell(1,ndims(Fc)); for dd=1:ndims(Fc), idxc{dd}=':'; end
    idxc{4}=kb(b); Xb=squeeze(Fc(idxc{:}));
    Ak(:,:,b)=abs(2*double(Xb)./(N*double(Im)));
  end
  i161=find(kb==161); nb=setdiff(1:numel(kb),i161);
  A161=Ak(:,:,i161); nbMed=median(Ak(:,:,nb),3);
  Rl=A161./nbMed; Rl(~vm)=NaN;
  Rlm=Rl(vm); Rlm=Rlm(isfinite(Rlm));
  strong=A161>3*median(A161(vm)); ph=angle(2*Fc(:,:,1,161)); % placeholder replaced below
  % phase coherence among strong valid pixels
  phm=angle(2*squeeze(Fc(:,:,1,161)));
  phv=phm(vm & strong & (abs(phm)>0 | true));
  phv=phv(isfinite(phv));
  if numel(phv)>1
    Rv=mean(cos(phv)); Iv=mean(sin(phv)); circstd=sqrt(max(0,1-hypot(Rv,Iv)))*180/pi;
  else
    circstd=NaN;
  end
  satFrac=mean(F.Imean(ri,ci)>0.99 | F.Imean(ri,ci)<0.0001,'all');
  fprintf(sf,'%s,%d,%d,%s,161,160,%.6f,%.17g,%.17g,%.17g,%.17g,%.6f,%.6f,%.6f,%d,%.3f,%.6f,%s\n', ...
    name,r0,c0,roiList{k,4},median(A161(vm)),mean(A161(vm),'all'), ...
    median(Rlm,'omitnan'),mean(Rlm,'omitnan'), ...
    nnz(Rlm>1.2)/numel(Rlm),nnz(Rlm>1.5)/numel(Rlm),nnz(Rlm>2)/numel(Rlm), ...
    nnz(strong & vm),circstd,satFrac,'ASSOCIATION_ONLY_NOT_CAUSAL_MAGNETIC_SIGNAL');
  roiMaps.(matlab.lang.makeValidName(name))=struct('A161',A161,'Ak',Ak,'Rlocal',Rl,'vm',vm,'Im',Im,'r0',r0,'c0',c0,'kind',roiList{k,4});
end
fclose(sf);
save(fullfile(numOut,'v074_roi_spectral_maps.mat'),'-struct','roiMaps','-v7.3');
% ---------- B1 sub-window demodulation diagnostics (2, center ROI) ----------
R=load(fullfile(v073Root,'numeric','fft400_corrected_small_roi.mat'));
sw=fopen(fullfile(tabDir,'v074_subwindow_diagnostics.csv'),'w');
fprintf(sw,'window,frame_start,frame_end,nframes,f_star_Hz,demod_amp_median,demod_amp_mean,rect_window_len_s,note\n');
fstar=399.80009995002496;
tj=(0:N-1)'/Fs;
tj=tj+999/Fs; % absolute time origin at frame 1000 (documented)
win={1000,1999;2000,3000};
for wI=1:2
  i1=win{wI,1}-999; i2=win{wI,2}-999;
  seg=double(R.roiFrames(:,:,:,i1:i2)); tt=tj(i1:i2);
  Imw=mean(seg,4);
  D=2*sum((seg-Imw).*reshape(exp(-2i*pi*fstar*tt),1,1,1,[]),4)/size(seg,4);
  am=abs(D)./max(Imw,realmin);
  vmw=R.validMask & isfinite(Imw) & Imw>R.meanFloor;
  fprintf(sw,'%s,%d,%d,%d,%.6f,%.17g,%.17g,%g,%s\n',sprintf('SUBWIN%d',wI),win{wI,1},win{wI,2},i2-i1+1,fstar, ...
    median(am(vmw)),mean(am(vmw),'all'),(i2-i1+1)/Fs,'DEVELOPMENT_DIAGNOSTIC explicit demodulation at fixed f*; same physical frequency both windows; not two independent experiments');
end
fclose(sw);
fprintf('[074B] done\n');
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




