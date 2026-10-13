function run_v077_A_identity(outRoot)
% v077 A: source/cache identity verification with real SHA-256 and metadata.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v077_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
fid=fopen(fullfile(tabDir,'v077_source_and_cache_identity.csv'),'w');
fprintf(fid,'item,path,sha256,bytes,meta\n');
items={ ...
 'render_system',[projectRoot '\src\render_system.m'],'wrapper source'; ...
 'pixel_mean',[projectRoot '\src\pixel_mean.m'],'pixel aggregation source'; ...
 'extract_fft_v073',[projectRoot '\src\extract_fft_v073.m'],'frozen FFT extractor'; ...
 'position_key',[projectRoot '\src\position_key.m'],'signed key helper (v076 hardened)'; ...
 'run_v076_D_qr_center',[projectRoot '\src\run_v076_D_qr_center.m'],'v076 QR source (2/N defect)'; ...
 'v076_dynamic_C400_mat',[projectRoot '\v076_return\numeric\v076_dynamic_center_corrected.mat'],'24 corrected C400 maps'; ...
 'v076_harmonic_small_mat',[projectRoot '\v076_return\numeric\v076_center_roi_harmonic_small_examples.mat'],'24 centre series'; ...
 'v075_holdout_data_mat',[projectRoot '\v075_return\numeric\v075_holdout_data.mat'],'24 full-field holdout structs'; ...
 'anchor_cache_D60_zf450_x0',[projectRoot '\v074_return\numeric\render_cache\D60_zf450_x+0.mat'],'anchor example'; ...
 'holdout_cache_D60_zf450_x-5',[projectRoot '\v075_return\numeric\render_cache\D60_zf450_x-5.mat'],'holdout example'};
for i=1:size(items,1)
  p=items{i,2};
  if isfile(p)
    h=sha256_file_next(p); b=numel(fileread(p)); %#ok<NASGU>
    d=dir(p);
    % verify cached anchor/holdout metadata
    meta=items{i,3};
    if contains(p,'render_cache')
      S=load(p); a=S.a;
      meta=sprintf('%s; D=%g zf=%g dx=%g mesh=%d q=%d',meta,a.D,a.zf,a.dx,a.Es(1)*0+size(a.Es,1),5);
      if isfield(a,'render_source'), meta=[meta '; render_source_sha=' sha256_file_next(a.render_source)]; end
    end
    fprintf(fid,'%s,%s,%s,%d,%s\n',items{i,1},p,h,d.bytes,meta);
  else
    fprintf(fid,'%s,%s,MISSING,0,FILE_NOT_FOUND\n',items{i,1},p);
  end
end
fclose(fid);
fprintf('[077A] identity table written\n');
end
