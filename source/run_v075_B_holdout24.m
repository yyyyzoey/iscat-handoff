function run_v075_B_holdout24(outRoot, v074Root)
% v075 B: re-verify the 24 interpolation holdouts with collision-free signed keys.
% Anchors load from the v074 render cache (files were always signed correctly);
% only the in-memory struct had collided. 24 non-BEM direct holdout renders (budget).
if nargin<2||isempty(v074Root), v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
cacheDir=fullfile(numOut,'render_cache'); if ~isfolder(cacheDir), mkdir(cacheDir); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
projectRoot=fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
od65=fullfile(projectRoot,'v065_return');
SIG=+1; Ds=[30 60 100]; zfs=[450 550]; xs=[-20 -10 0 10 20];
% ---------- anchors from v074 cache (signed filenames are correct) ----------
v74cache=fullfile(v074Root,'numeric','render_cache');
anchor=struct();
for D=Ds
  for zf=zfs
    for x=xs
      key=position_key(D,zf,x);
      f74=fullfile(v74cache,sprintf('D%d_zf%g_x%+g.mat',D,zf,x));
      A=load(f74); a=A.a;
      anchor.(key)=struct('Es',a.Es,'Eref',a.Eref,'x',x);
    end
  end
end
fprintf('[075B] 30 anchors loaded from v074 cache with position_key\n');
% ---------- 24 holdouts ----------
holdL={30,450,-5;30,450,5;30,450,-15;30,450,15; 60,450,-5;60,450,5;60,450,-15;60,450,15; 100,450,-5;100,450,5;100,450,-15;100,450,15; 30,550,-5;30,550,5;30,550,-15;30,550,15; 60,550,-5;60,550,5;60,550,-15;60,550,15; 100,550,-5;100,550,5;100,550,-15;100,550,15};
hf=fopen(fullfile(tabDir,'v075_holdout24_corrected.csv'),'w');
fprintf(hf,'D_nm,zf_nm,dx_nm,Esca_relL2_full,Itot_roi_relL2,center_Itot_absdiff,S_area_absdiff,gate,status\n');
holdData=struct(); nRender=0;
for k=1:size(holdL,1)
  D=holdL{k,1}; zf=holdL{k,2}; dx=holdL{k,3};
  hkey=position_key(D,zf,dx);
  fmat=fullfile(cacheDir,[hkey '.mat']);
  if isfile(fmat)
    A=load(fmat); rh=A.a; fprintf('[075B] %s CACHE_HIT\n',hkey);
  else
    rh=renderState(D,zf,dx,od65,SIG); save(fmat,'rh','-v7.3'); nRender=nRender+1;
  end
  % 5-anchor interpolation with FIXED keys
  xs=xs5(); Es=cell(1,5); 
  for i=1:5
    ak=anchor.(position_key(D,zf,xs(i)));
    Es{i}=ak.Es;
    if i==3, Eref=ak.Eref; end
  end
  Es4=cat(4,Es{:});
  EsI=interpField(Es4,xs,dx);
  ItI=intensityOf(EsI,Eref);
  ItD=intensityOf(rh.Es,rh.Eref);
  relEs=norm(double(EsI(:))-double(rh.Es(:)))/max(norm(double(rh.Es(:))),realmin);
  Cm=(size(ItD,1)+1)/2;
  roiD=ItD(Cm-20:Cm+20,Cm-20:Cm+20); roiI=ItI(Cm-20:Cm+20,Cm-20:Cm+20);
  relIt=norm(roiD(:)-roiI(:))/max(norm(roiD(:)),realmin);
  cD=ItD(Cm,Cm); cI=ItI(Cm,Cm); sD=sum(roiD(:)); sI=sum(roiI(:));
  if relEs<1e-3, st='PASS'; else, st='FAIL'; end
  fprintf(hf,'%d,%g,%g,%.17g,%.17g,%.17g,%.17g,0.001,%s\n',D,zf,dx,relEs,relIt,abs(cD-cI),abs(sD-sI),st);
  holdData.(hkey)=struct('relEs',relEs,'relIt',relIt,'st',st,'Es_direct',rh.Es,'Es_interp',EsI,'Eref',Eref);
  fprintf('[075B] %s relEs=%.4g %s\n',hkey,relEs,st);
end
fclose(hf);
% small signed-side examples for independent recheck (D60/zf450 +-5)
for sgn={'M','P'}
  dx=-5; if strcmp(sgn{1},'P'), dx=5; end
  hkey=position_key(60,450,dx);
  H=holdData.(hkey);
  roi=(130:195); % 66x66 interior crop for a compact example
  ex=struct('dx',dx,'Es_direct',H.Es_direct(roi,roi,:),'Es_interp',H.Es_interp(roi,roi,:), ...
    'Eref',H.Eref(roi,roi,:),'relEs',H.relEs);
  save(fullfile(numOut,sprintf('v075_holdout_example_D60_zf450_%s5.mat',sgn{1})),'ex','-v7.3');
end
save(fullfile(numOut,'v075_holdout_data.mat'),'-struct','holdData','-v7.3');
fprintf('[075B] done; new holdout renders: %d\n',nRender);
end
function xs=xs5(), xs=[-20 -10 0 10 20]; end
function a=renderState(D,zf,dx,od65,SIG)
S=load(fullfile(od65,sprintf('D%d_s_1444.mat',D)),'s'); sv=S.s;
c=sv.cfg; c.focus_nm=[0,0,zf]; c.sampling.subpixels=5; c.particle.xy_nm=[dx,0];
if dx~=0
  n1=sv.cfg.layers.n(1); k1=n1*2*pi/520; dirv=sv.lens.dir;
  sv.far=sv.far.*reshape(exp(SIG*(-1i*k1*(dirv(:,1)*dx))),[],1,1);
end
r=render_system(sv,c);
a=struct('Es',r.Esca,'Eref',r.Eref,'D',D,'zf',zf,'dx',dx,'render_source',which('render_system'));
end
function Es=interpField(Es4,xg,x)
x=max(min(x,xg(end)),xg(1));
ia=find(x>=xg(1:end-1) & x<=xg(2:end),1,'last');
wb=(x-xg(ia))/(xg(ia+1)-xg(ia));
Es=(1-wb)*Es4(:,:,:,ia)+wb*Es4(:,:,:,ia+1);
end
function It=intensityOf(Es,Eref)
It=sum(abs(Eref+Es).^2,3);
end
