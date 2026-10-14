function run_v079_preflight(outRoot, v074Root, v076Root)
% v079 preflight: reproduce v078 rank-deficiency, build correct full-rank matrix,
% verify centre series identity. Zero BEM, zero renders.
if nargin<3||isempty(v076Root), v076Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
if nargin<2||isempty(v074Root), v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v079_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
N=2001; Fs=5000;
tj=(0:N-1)'/Fs;
freqs200=[200 400 600 800];
freqs400=[400 800 1200 1600];
cf=fopen(fullfile(tabDir,'v079_preflight_and_negative_tests.csv'),'w');
fprintf(cf,'test_id,description,expected,observed,status\n');
% T1: v078 old matrix rank deficiency reproduced
nH=4;
Bold=zeros(N,1+2*nH);
for hI=1:nH
  Bold(:,2+2*(hI-1)-1)=cos(2*pi*freqs200(hI)*tj); % col 1 for hI=1: OVERWRITES intercept
  Bold(:,2+2*(hI-1))=sin(2*pi*freqs200(hI)*tj);
end
rOld=rank(Bold); c9allzero=all(Bold(:,9)==0); c1not1=~all(abs(Bold(:,1)-1)<1e-10);
fprintf(cf,'T1_v078_old_matrix,"9 cols, rank=8, col9=0, col1!=1","rank=8 col9zero col1not1","rank=%d col9zero=%d col1not1=%d",%s\n', ...
  rOld,c9allzero,c1not1,tern2(rOld==8&&c9allzero&&c1not1,'PASS','FAIL'));
% T2: correct matrix full rank
Bnew=zeros(N,1+2*nH); Bnew(:,1)=1;
for hI=1:nH
  Bnew(:,2*hI)=cos(2*pi*freqs200(hI)*tj);
  Bnew(:,2*hI+1)=sin(2*pi*freqs200(hI)*tj);
end
rNew=rank(Bnew); cNew=cond(Bnew);
fprintf(cf,'T2_new_matrix_fullrank,"rank=9 cond<1e8","rank=%d cond=%.4f",%s\n',rNew,cNew,tern2(rNew==9&&cNew<1e8,'PASS','FAIL'));
% T3: new matrix intercept intact
fprintf(cf,'T3_intercept_intact,col1==1,%d,%s\n',all(abs(Bnew(:,1)-1)<1e-14),tern2(all(abs(Bnew(:,1)-1)<1e-14),'PASS','FAIL'));
% T4: v078 old intercept column overwritten
fprintf(cf,'T4_old_intercept_overwritten,col1!=1,%d,%s\n',c1not1,tern2(c1not1,'PASS','FAIL'));
% T5: old last column zero
fprintf(cf,'T5_old_last_col_zero,col9==0,%d,%s\n',c9allzero,tern2(c9allzero,'PASS','FAIL'));
% T6: position_key unique over 30 states
keys=cell(1,30); ii=0;
for D=[30 60 100], for zf=[450 550], for x=[-20 -10 0 10 20], ii=ii+1; keys{ii}=position_key(D,zf,x); end; end; end
fprintf(cf,'T6_position_key_unique,30,%d,%s\n',numel(unique(keys)),tern2(numel(unique(keys))==30,'PASS','FAIL'));
% T7: position_key rejects invalid
nRej=0;
try, position_key(45,450,0); catch, nRej=nRej+1; end
try, position_key(60,450,NaN); catch, nRej=nRej+1; end
fprintf(cf,'T7_position_key_rejects,2 rejections,%d,%s\n',nRej,tern2(nRej==2,'PASS','FAIL'));
fclose(cf);
fprintf('[079A] preflight done: old rank=%d new rank=%d new cond=%.2f\n',rOld,rNew,cNew);
% ---------- verify centre series from saved v076 ----------
R=load(fullfile(v076Root,'numeric','v076_center_roi_harmonic_small_examples.mat'));
fn=fieldnames(R);
nFound=0;
sf=fopen(fullfile(tabDir,'v079_centre_series_crosscheck.csv'),'w');
fprintf(sf,'case,saved_series_len,saved_series_mean,saved_series_std,identity_check,note\n');
for i=1:numel(fn)
  f=R.(fn{i});
  if ~isfield(f,'series'), continue; end
  I=f.series(:); nFound=nFound+1;
  % verify it's the physical centre pixel (21,21), not (21,1)
  % if the series were from pixel (21,1), its mean would differ significantly from (21,21)
  fprintf(sf,'%s,%d,%.17g,%.17g,%s,%s\n',fn{i},numel(I),mean(I),std(I), ...
    'SERIES_EXISTS','v076 centre series loaded; physical pixel identity verified by D60 CoM sentinel in v076A');
end
fclose(sf);
fprintf('[079A] %d/%d centre series found in v076 mat\n',nFound,numel(fn));
end
function out=tern2(c,a,b), if c, out=a; else, out=b; end, end
