function run_v078_A_identity(outRoot)
% v078 A: preflight identity with correct paths and real SHA-256.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v078_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
fid=fopen(fullfile(tabDir,'v078_source_cache_identity.csv'),'w');
fprintf(fid,'item,path,exists,sha256,bytes,meta\n');
items={
 'render_system',[projectRoot '\src\render_system.m'],'wrapper';
 'pixel_mean',[projectRoot '\src\pixel_mean.m'],'aggregation';
 'extract_fft_v073',[projectRoot '\src\extract_fft_v073.m'],'frozen FFT';
 'position_key',[projectRoot '\src\position_key.m'],'signed key';
 'v076_dynamic_C400',[projectRoot '\v076_return\numeric\v076_dynamic_center_corrected.mat'],'24 corrected C400 maps';
 'v076_harmonic_series',[projectRoot '\v076_return\numeric\v076_center_roi_harmonic_small_examples.mat'],'24 centre series';
 'v075_holdout_data',[projectRoot '\v075_return\numeric\v075_holdout_data.mat'],'24 full-field holdout structs';
 'anchor_D60_zf450_x0',[projectRoot '\v074_return\numeric\render_cache\D60_zf450_x+0.mat'],'anchor example';
 'holdout_D60_ZF450_XM0005000',[projectRoot '\v075_return\numeric\render_cache\D60_ZF450_XM0005000.mat'],'holdout example position_key format';
};
for i=1:size(items,1)
  p=items{i,2};
  if isfile(p)
    h=sha256_file_next(p); d=dir(p);
    meta=items{i,3};
    if contains(p,'render_cache')
      S=load(p); fn=fieldnames(S); a=S.(fn{1});
      if isfield(a,'D'), meta=[meta sprintf('; D=%g zf=%g dx=%g',a.D,a.zf,a.dx)]; end
      if isfield(a,'Es'), meta=[meta sprintf('; Es=%dx%dx%dx%d',size(a.Es,1),size(a.Es,2),size(a.Es,3),size(a.Es,4))]; end
    end
    fprintf(fid,'%s,%s,true,%s,%d,%s\n',items{i,1},p,h,d.bytes,meta);
  else
    fprintf(fid,'%s,%s,false,MISSING,0,%s\n',items{i,1},p,items{i,3});
  end
end
fclose(fid);
fprintf('[078A] identity done\n');
end
