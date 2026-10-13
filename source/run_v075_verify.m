function run_v075_verify(outRoot)
% Independent-session recheck: only saved arrays; no renders, no anchors in memory.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return'; end
tabDir=fullfile(outRoot,'tables'); numOut=fullfile(outRoot,'numeric');
vf=fopen(fullfile(tabDir,'v075_independent_recheck.csv'),'w');
fprintf(vf,'check,expected,recomputed,status\n');
% 1) holdout examples: recompute relEs from the saved crops
nOk=0;
for sgn={'M','P'}
  dx=-5; if strcmp(sgn{1},'P'), dx=5; end
  E=load(fullfile(numOut,sprintf('v075_holdout_example_D60_zf450_%s5.mat',sgn{1})));
  rel=norm(double(E.ex.Es_interp(:))-double(E.ex.Es_direct(:)))/max(norm(double(E.ex.Es_direct(:))),realmin);
  ok=rel<1e-3; % crop-level relEs (66x66 subset) need not equal the full-field value
  nOk=nOk+ok;
  fprintf(vf,'holdout_D60_zf450_%s5_relEs,crop_relEs_below_1e-3,%.17g,%s\n',sgn{1},rel,tern2(rel<1e-3,'PASS','FAIL'));
end
% 2) dynamic C400 maps: absCenter consistency + M400>M200 ordering + a^2/a scaling
R=load(fullfile(numOut,'v075_dynamic_C400_corrected.mat'));
m2=matlab.lang.makeValidName('D60_zf450_M200_a20'); m4=matlab.lang.makeValidName('D60_zf450_M400_a20');
b2=abs(R.(m2).C400(21,21)); b4=abs(R.(m4).C400(21,21));
fprintf(vf,'D60_M200_a20_center_from_map,%.17g,%.17g,%s\n',R.(m2).absCenter,b2,tern2(abs(b2-R.(m2).absCenter)<1e-15,'PASS','FAIL'));
fprintf(vf,'D60_M400_a20_center_from_map,%.17g,%.17g,%s\n',R.(m4).absCenter,b4,tern2(abs(b4-R.(m4).absCenter)<1e-15,'PASS','FAIL'));
fprintf(vf,'M400_firstorder_gt_M200_secondorder_D60_a20,true,%d,%s\n',b4>b2,tern2(b4>b2,'PASS','FAIL'));
q200=(R.(m2).absCenter/R.(matlab.lang.makeValidName('D60_zf450_M200_a5')).absCenter);
q400=(b4/R.(matlab.lang.makeValidName('D60_zf450_M400_a5')).absCenter);
fprintf(vf,'M200_scaling_superlinear_between_a2_and_a4,4..32,%0.4f,%s\n',q200,tern2(q200>4 && q200<32,'PASS','FAIL'));
fprintf(vf,'M400_scaling_near_linear,4,%0.4f,%s\n',q400,tern2(abs(q400-4)<1.5,'PASS','FAIL'));
% 3) negative controls still exact
n1=abs(R.NEG1.absCenter); 
rn=n1/0.05;
fprintf(vf,'NEG1_absC400_equals_depth_naive_x_Dirichlet_leakage,0.985..1.0,%.6f,%s\n',rn,tern2(rn>=0.985 && rn<=1.0,'PASS','FAIL'));
fclose(vf);
fprintf('[075V] independent recheck written\n');
end
function out=tern2(c,a,b), if c, out=a; else, out=b; end, end




