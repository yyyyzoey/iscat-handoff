function run_v076_A_coord(outRoot, v075Root)
% v076 A: coordinate mapping verification, position_key hardening tests, negative tests.
% Zero BEM, zero new renders.
if nargin<2||isempty(v075Root), v075Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
projectRoot=fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
od65=fullfile(projectRoot,'v065_return');
cf=fopen(fullfile(tabDir,'v076_coordinate_mapping_and_negative_tests.csv'),'w');
fprintf(cf,'test_id,description,expected,observed,status,note\n');
% T1: collision regression (v074 defect still reproducible in makeValidName)
k1=matlab.lang.makeValidName('D60_zf450_x-10'); k2=matlab.lang.makeValidName('D60_zf450_x+10');
fprintf(cf,'T1_makeValidName_collision,makeValidName maps +-10 to same field,equal,%d,%s,documented v074 defect\n',strcmp(k1,k2),tern2(strcmp(k1,k2),'PASS','FAIL'));
% T2: position_key uniqueness over 30 states
keys=cell(1,30); i=0;
for D=[30 60 100]
  for zf=[450 550]
    for x=[-20 -10 0 10 20]
      i=i+1; keys{i}=position_key(D,zf,x);
    end
  end
end
u=numel(unique(keys));
fprintf(cf,'T2_position_key_unique_30,30 unique keys,%d,%s,fixed key helper\n',u,tern2(u==30,'PASS','FAIL'));
% T3: position_key rejects unauthorised inputs
nRej=0;
try, position_key(45,450,0); catch, nRej=nRej+1; end
try, position_key(60,500,0); catch, nRej=nRej+1; end
try, position_key(60,450,7); catch, nRej=nRej+1; end
try, position_key(60,450,NaN); catch, nRej=nRej+1; end
fprintf(cf,'T3_position_key_rejects,4 unauthorised inputs rejected,%d,%s,hardened v076\n',nRej,tern2(nRej==4,'PASS','FAIL'));
% T4: coordinate mapping from a real rendered state (D60/zf450 x=0): fine_x_nm axes
S=load(fullfile(od65,'D60_s_1444.mat'),'s'); sv=S.s;
c=sv.cfg; c.focus_nm=[0,0,450]; c.sampling.subpixels=5; c.particle.xy_nm=[0,0];
r=render_system(sv,c);
fx=r.fine_x_nm; fy=r.fine_y_nm;
i0correct=(13-1)*5+1; i1correct=53*5; % 61..265
fineCenter=163;
fprintf(cf,'T4_fine_axis_center,fine_x(163)=0,actual %.6g nm,%s,fine_x_nm from render_system\n',fx(fineCenter),tern2(abs(fx(fineCenter))<1e-9,'PASS','FAIL'));
fprintf(cf,'T5_fine_axis_step,13 nm per subpixel,actual %.6g nm,%s,q=5 with 65nm pixel\n',fx(2)-fx(1),tern2(abs((fx(2)-fx(1))-13)<1e-9,'PASS','FAIL'));
% T6: legacy 64:268 vs correct 61:265 centre offset = 39 nm
fprintf(cf,'T6_legacy_offset,legacy centre fine166 = +39 nm vs correct 163,actual %.6g nm,%s,deterministic 3-subpixel offset\n',(166-fineCenter)*13,tern2(abs((166-fineCenter)*13-39)<1e-9,'PASS','FAIL'));
% T7: numeric equivalence: C(33,33) from render_system vs recomputed from fine fields via correct ROI
q=5;
ItF=sum(abs(r.Eref+r.Esca).^2,3); I0F=sum(abs(r.Eref).^2,3); IsF=sum(abs(r.Esca).^2,3); IiF=2*real(sum(conj(r.Eref).*r.Esca,3));
ItP=pixel_mean(ItF,q); I0P=pixel_mean(I0F,q); IsP=pixel_mean(IsF,q); IiP=pixel_mean(IiF,q);
Cre=(ItP-I0P)./I0P; Cas=(IsP+IiP)./I0P;
d33=abs(Cre(33,33)-r.contrast(33,33)); d33b=abs(Cas(33,33)-r.contrast(33,33));
fprintf(cf,'T7_C33_recompute_itpath,abs diff <=1e-6,%.3g,%s,pixel_mean path reproduces render_system contrast\n',d33,tern2(d33<=1e-6,'PASS','FAIL'));
fprintf(cf,'T8_C33_recompute_aspath,abs diff <=1e-6,%.3g,%s,(Isca+Iint)/Iref decomposition identity\n',d33b,tern2(d33b<=1e-6,'PASS','FAIL'));
cblk=r.contrast(13:53,13:53); CreB=Cre(13:53,13:53); dBlk=max(abs(CreB(:)-cblk(:)));
fprintf(cf,'T9_Cblock_recompute,max abs diff <=1e-6,%.3g,%s,full 41x41 physical-pixel ROI block\n',dBlk,tern2(dBlk<=1e-6,'PASS','FAIL'));
% T10: legacy shifted block does NOT match the identity of the correct block (negative test)
leg=Cre(14:54,14:54); % 64:268 corresponds to pixel block 14:54
cblk=r.contrast(13:53,13:53); dLeg=max(abs(leg(:)-cblk(:)));
fprintf(cf,'T10_legacy_block_rejected,legacy 64:268 block differs from correct 13:53 block,maxdiff %.3g > 0,%s,3-subpixel offset must FAIL identity\n',dLeg,tern2(dLeg>0,'PASS','FAIL'));
% T11: CoM sentinel from actual arrays (65nm pixel units)
w=abs(r.Isca); w=reshape(w,65,65);
com=(1:65)*sum(w,2)/sum(w(:));
fprintf(cf,'T11_com_reference,x=0 CoM at pixel 33,actual %.6f,%s,\n',com,tern2(abs(com-33)<1e-6,'PASS','FAIL'));
fclose(cf);
% static sentinels mat
save(fullfile(numOut,'v076_center_roi_static_sentinels.mat'),'r','Cre','Cas','I0P','IsP','IiP','ItP','fx','fy','-v7.3');
fprintf('[076A] done\n');
end
function out=tern2(c,a,b), if c, out=a; else, out=b; end, end




