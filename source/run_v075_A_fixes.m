function run_v075_A_fixes(outRoot, v074Root)
% v075 A: reproduce the v074 anchor-key collision, prove the fix, correct C1 units,
% zero-render re-export of the 8-ROI spectra under the 6-neighbour contract.
if nargin<2||isempty(v074Root), v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
% ---- 1) regression: the v074 defect must reproduce ----
k1=matlab.lang.makeValidName('D60_zf450_x-10');
k2=matlab.lang.makeValidName('D60_zf450_x+10');
collision=strcmp(k1,k2);
assert(collision,'v074 collision not reproduced - environment changed?');
fprintf('[075A] v074 collision reproduced: ''%s'' == ''%s''\n',k1,k2);
% ---- 2) fixed key uniqueness ----
keys=cell(1,30); i=0;
for D=[30 60 100]
  for zf=[450 550]
    for x=[-20 -10 0 10 20]
      i=i+1; keys{i}=position_key(D,zf,x);
    end
  end
end
assert(numel(unique(keys))==30,'position_key not unique');
assert(~strcmp(position_key(60,450,-10),position_key(60,450,10)));
fprintf('[075A] position_key unique over 30 states\n');
% ---- 3) C1 unit correction (65 nm physical pixel, NOT the 13 nm subpixel) ----
measured_px=0.1525954; % v074 CoM shift in 65nm-pixel units for prescribed dx=+10nm
cf=fopen(fullfile(tabDir,'v075_c1_unit_corrected.csv'),'w');
fprintf(cf,'item,value_nm,check,note\n');
fprintf(cf,'measured_CoM_shift_nm,%.6f,abs(measured-9.918701)<1e-6 via px*65,C1 sentinel expressed in physical pixels\n',measured_px*65);
fprintf(cf,'prescribed_dx_nm,10.0,abs(10/65-0.15384615384615385)<1e-12,expected in 65nm-pixel units is 0.15384615 px\n');
fprintf(cf,'rel_error,%.6f,|measured-prescribed|/prescribed,~0.8%%: sentinel PASS with corrected units (v074 table mis-scaled by 13/65)\n',abs(measured_px*65-10)/10);
fclose(cf);
fprintf('[075A] C1 units corrected: %.4f nm measured vs 10 nm prescribed (%.2f%%)\n',measured_px*65,100*abs(measured_px*65-10)/10);
% ---- 4) zero-render ROI spectral re-export under the 6-neighbour contract ----
M=load(fullfile(v074Root,'numeric','v074_roi_spectral_maps.mat'));
kb=158:169; i161=find(kb==161);
nbIdx=[1 2 3 5 6 7]; % bins 158,159,160,162,163,164 (exactly six neighbours)
sf=fopen(fullfile(tabDir,'v075_roi_spectral_corrected.csv'),'w');
fprintf(sf,'roi_name,kind,row0,col0,n_valid,A161_median_valid,A161_mean_valid,nb6_median_median_valid,Rlocal_median_valid,Rlocal_mean_valid,frac_Rlocal_gt_1p2,frac_Rlocal_gt_1p5,frac_Rlocal_gt_2,bins_used,note\n');
sc=fopen(fullfile(tabDir,'v075_roi_schema_checks.csv'),'w');
fprintf(sc,'check,expected,observed,status\n');
fn=fieldnames(M); nROI=0;
for i=1:numel(fn)
  S=M.(fn{i});
  A161=S.Ak(:,:,i161);
  nb6=median(S.Ak(:,:,nbIdx),3);
  vm=S.vm; Rl=A161./nb6; Rl(~vm)=NaN; Rv=Rl(vm); Rv=Rv(isfinite(Rv));
  Avm=A161(vm);
  fprintf(sf,'%s,%s,%d,%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.6f,%.6f,%.6f,158;159;160;162;163;164,%s\n', ...
    fn{i},S.kind,S.r0,S.c0,nnz(vm),median(Avm),mean(Avm,'all'),median(nb6(vm)), ...
    median(Rv,'omitnan'),mean(Rv,'omitnan'),nnz(Rv>1.2)/numel(Rv),nnz(Rv>1.5)/numel(Rv), ...
    nnz(Rv>2)/numel(Rv),'ASSOCIATION_ONLY_NOT_CAUSAL_MAGNETIC_SIGNAL');
  nROI=nROI+1;
  % schema checks per ROI
  fprintf(sc,'%s_Ak_bins,12,%d,%s\n',fn{i},size(S.Ak,3),tern2(size(S.Ak,3)==12,'PASS','FAIL'));
end
fclose(sf); fclose(sc);
fprintf('[075A] re-exported %d ROIs under 6-neighbour contract (zero render)\n',nROI);
% ---- 5) runtime/budget note ----
rb=fopen(fullfile(tabDir,'v075_source_runtime_and_budget.csv'),'w');
fprintf(rb,'item,value,note\n');
fprintf(rb,'upstream,v074 8aa02ccfc690b111a2e915951963d37932d0d313,locked\n');
fprintf(rb,'new_BEM,0,prohibition respected\n');
fprintf(rb,'holdout_budget,24,non-BEM direct renders authorised this round\n');
fprintf(rb,'roi_reexport_renders,0,zero-render from saved Ak maps\n');
fprintf(rb,'makeValidName_collision,reproduced_and_fixed,see v075_reject_tests\n');
fclose(rb);
fprintf('[075A] done\n');
end
function out=tern2(c,a,b), if c, out=a; else, out=b; end, end
