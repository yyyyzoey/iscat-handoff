function run_v072_replay(outRoot)
% v072 C: ONE real-data replay of 2001 frames (both extractor chains, shared FFT,
% independent output labels). No BEM. No images uploaded anywhere.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v072_return'; end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
folder='C:\Users\PC\Desktop\课题\7.29\7.29\BMP100053022-20260729-105610';
Fs=5000; startFrame=1000; endFrame=3000;
k420=169; k400=161;   % 1-based bins for 420/400 targets at N=2001
allFiles=dir(fullfile(folder,'*.bmp'));
allFiles=sortBmp(allFiles);
total=numel(allFiles);
fprintf('[072C] folder bmps=%d\n',total);
files=allFiles(startFrame:endFrame); N=numel(files);
fprintf('[072C] processing frames %d..%d (N=%d): %s .. %s\n',startFrame,endFrame,N,files(1).name,files(end).name);
[img,map]=imread(fullfile(folder,files(1).name));
if ~isempty(map), img=ind2rgb(img,map); end
img=im2single(img);
[H,W,C3]=size(img);
if C3==3, img=0.2989*img(:,:,1)+0.5870*img(:,:,2)+0.1140*img(:,:,3); end
stack=zeros(H,W,N,'single');
stack(:,:,1)=img;
t0=tic;
for n=2:N
  [im,m]=imread(fullfile(folder,files(n).name));
  if ~isempty(m), im=ind2rgb(im,m); end
  im=im2single(im);
  if size(im,3)==3
    im=0.2989*im(:,:,1)+0.5870*im(:,:,2)+0.1140*im(:,:,3);
  end
  stack(:,:,n)=im;
  stack(:,:,n)=im2single(im);
  if mod(n,500)==0, fprintf('[072C] read %d/%d (%.1fs)\n',n,N,toc(t0)); end
end
fprintf('[072C] stack read %.1fs\n',toc(t0));
t1=tic;
timeMean=mean(stack,3);            % temporal mean (3-D stack layout)
signal=stack-timeMean;
fftR=fft(signal,[],4);
fprintf('[072C] fft %.1fs\n',toc(t1));
% chain A: test.m (420, unnormalized single-sided amplitude/phase)
X420=fftR(:,:,k420);
amp420=2*abs(X420)/N; ph420=angle(X420);
% chain B: test_with_contrast.m (400, normalized complex modulation contrast)
X400=fftR(:,:,k400);
pos=timeMean(timeMean>0&isfinite(timeMean));
meanFloor=0.01*median(pos);
mask=isfinite(timeMean)&timeMean>meanFloor;
C400=complex(zeros(size(X400)));
C400(mask)=2*X400(mask)./(N*timeMean(mask));
ampC=abs(C400); phC=angle(C400);
df=Fs/N; act420=(k420-1)*df; act400=(k400-1)*df;
fprintf('[072C] actualFreq 420-chain=%.6f Hz, 400-chain=%.6f Hz, meanFloor=%.6g, valid mask=%.2f%%\n', ...
  act420,act400,meanFloor,100*nnz(mask)/numel(mask));
save(fullfile(numOut,'replay_729_frames1000_3000.mat'), ...
  'timeMean','X420','amp420','ph420','X400','C400','ampC','phC','mask','meanFloor', ...
  'act420','act400','Fs','N','startFrame','endFrame','-v7.3');
% summary CSV (no large arrays to GitHub)
cf=fopen(fullfile(tabDir,'fft_replay_one_case.csv'),'w');
fprintf(cf,'field,value,note\n');
fprintf(cf,'data_folder,%s,BMP100053022-20260729-105610\n',folder);
fprintf(cf,'total_bmps,%d,batch has %d frames >= 3000 required\n',total,total);
fprintf(cf,'frame_range,%d-%d,N=2001 per both source scripts\n',startFrame,endFrame);
fprintf(cf,'first_frame,%s,\n',files(1).name);
fprintf(cf,'last_frame,%s,\n',files(end).name);
fprintf(cf,'bmp_dims,%dx%d,8-bit grayscale (352x296)\n',W,H);
fprintf(cf,'frame_rate_source,5000 fps,timestamp deltas 200 us between consecutive frames\n');
fprintf(cf,'chainA,test.m 420 unnormalized,actualFreq=%.6f Hz\n',act420);
fprintf(cf,'chainA_amp420_min_max_mean,%.6g / %.6g / %.6g,single-sided 2|X|/N gray-level units\n',min(amp420(:)),max(amp420(:)),mean(amp420(:),'all'));
fprintf(cf,'chainB,test_with_contrast.m 400 normalized,actualFreq=%.6f Hz\n',act400);
fprintf(cf,'chainB_meanFloor,%.6g,0.01 x median positive timeMean\n',meanFloor);
fprintf(cf,'chainB_valid_mask_fraction,%.6f,fraction of pixels passing meanFloor mask\n',nnz(mask)/numel(mask));
fprintf(cf,'chainB_ampC_min_max_mean,%.6g / %.6g / %.6g,|C_f| normalized modulation contrast\n',min(ampC(:)),max(ampC(:)),mean(ampC(:),'all'));
fprintf(cf,'reconstruction,NOT_EXECUTED,display-only single-frequency BMP reconstruction skipped to avoid writing 2001 files; core observable (FFT amplitude/phase/contrast) computed\n');
fprintf(cf,'validation_status,ANALYTIC_EXTRACTOR_TEST_PASS__REPLAY_EXECUTED,calibration_valid=false; experimental_validation=false (units/instrument still unresolved)\n');
fclose(cf);
fprintf('[072C] replay done\n');
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


