function run_v074_C2_dynamic_forward(outRoot)
% v074 C2: bounded prescribed-motion time-domain forward from SAVED Fe3O4 fields.
% ZERO BEM. Lateral translation via sentinel-verified far-field phase ramp (C1).
% 30 anchor states (3D x 2zf x 5x) + 24 holdout states = 54 unique renders max.
% 24 prescribed trajectories + 8 exposure variants + 2 analytic negative controls = 34.
% NOTHING here is real magnetism: trajectories are prescribed kinematics.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
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
SIG=+1;
Ds=[30 60 100]; zfs=[450 550]; xs=[-20 -10 0 10 20];
L=41; N=2001; Fs=5000;
anchor=struct(); nNew=0;
for D=Ds
  for zf=zfs
    for x=xs
      key=sprintf('D%d_zf%g_x%+g',D,zf,x);
      fmat=fullfile(cacheDir,[key '.mat']);
      if isfile(fmat)
        A=load(fmat); anchor.(matlab.lang.makeValidName(key))=A.a;
      else
        a=renderState(D,zf,x,od65,SIG);
        save(fmat,'a','-v7.3');
        anchor.(matlab.lang.makeValidName(key))=a;
        nNew=nNew+1;
      end
    end
  end
end
fprintf('[074C2] anchors ready; new renders this session: %d (C1 already covered 8 unique states; total unique <=54)\n',nNew);
% ---------- holdouts ----------
holdL={30,450,-5;30,450,5;30,450,-15;30,450,15; 60,450,-5;60,450,5;60,450,-15;60,450,15; 100,450,-5;100,450,5;100,450,-15;100,450,15; 30,550,-5;30,550,5;30,550,-15;30,550,15; 60,550,-5;60,550,5;60,550,-15;60,550,15; 100,550,-5;100,550,5;100,550,-15;100,550,15};
hf=fopen(fullfile(tabDir,'v074_interpolation_holdout.csv'),'w');
fprintf(hf,'D_nm,zf_nm,dx_nm,Esca_relL2_full,Itot_roi_relL2,center_Itot_absdiff,S_area_absdiff,gate,status\n');
holdData=struct();
for k=1:size(holdL,1)
  D=holdL{k,1}; zf=holdL{k,2}; dx=holdL{k,3};
  key=sprintf('D%d_zf%g_x%+g',D,zf,dx);
  rh=renderState(D,zf,dx,od65,SIG);
  a5=anchors5(anchor,D,zf);
  EsI=interpField(a5.Es,a5.x,dx);
  ItI=intensityOf(EsI,a5.Eref);
  ItD=intensityOf(rh.Es,rh.Eref);
  relEs=norm(double(EsI(:))-double(rh.Es(:)))/max(norm(double(rh.Es(:))),realmin);
  Cm=(size(ItD,1)+1)/2;
  roiD=ItD(Cm-20:Cm+20,Cm-20:Cm+20); roiI=ItI(Cm-20:Cm+20,Cm-20:Cm+20);
  relIt=norm(roiD(:)-roiI(:))/max(norm(roiD(:)),realmin);
  cD=ItD(Cm,Cm); cI=ItI(Cm,Cm); sD=sum(roiD(:)); sI=sum(roiI(:));
  if relEs<1e-3, st='PASS'; else, st='FAIL'; end
  fprintf(hf,'%d,%g,%g,%.17g,%.17g,%.17g,%.17g,0.001,%s\n',D,zf,dx,relEs,relIt,abs(cD-cI),abs(sD-sI),st);
  holdData.(matlab.lang.makeValidName(key))=struct('relEs',relEs,'relIt',relIt,'st',st);
end
fclose(hf);
% ---------- trajectories ----------
gates=fopen(fullfile(tabDir,'v074_dynamic_forward_results.csv'),'w');
fprintf(gates,'D_nm,zf_nm,trajectory_type,amplitude_nm_assumed,frequency_Hz,exposure_s_assumed,absC400_center,complexC400_center_real,complexC400_center_imag,ROI_normC400_valid,ROI_valid_fraction,interp_holdout_relEs_minus5,FFT_DFT_relmax,flags\n');
res=struct(); nEval=0;
for D=Ds
  for zf=zfs
    a5=anchors5(anchor,D,zf);
    E=a5.Es; Eref=a5.Eref;
    [blk,ErefB]=roiBlocks(E,Eref);
    nA=5; xg=a5.x;
    Lm=cell(1,nA); Dm=cell(1,nA);
    for i=1:nA
      Lm{i}=2*real(sum(conj(ErefB).*blk{i},3)); Dm{i}=sum(abs(blk{i}).^2,3);
    end
    Qm=cell(nA);
    for i=1:nA
      for j2=i+1:nA
        Qm{i,j2}=2*real(sum(conj(blk{i}).*blk{j2},3));
      end
    end
    Iref=sum(abs(ErefB).^2,3);
    for ttype=[200 400]
      for ampn=[5 20]
        tj=(0:N-1)'/Fs; xj=ampn*cos(2*pi*ttype*tj);
        Ifine=zeros(205,205,'single'); Ipix=zeros(L,L,1,N,'single');
        for j2=1:N
          [wa,wb,ia,ib]=linWeights(xj(j2),xg);
          Ifine(:)=single(Iref + wa*Lm{ia}+wb*Lm{ib} + wa^2*Dm{ia}+wb^2*Dm{ib} + wa*wb*Qm{ia,ib});
          Ipix(:,:,1,j2)=pixel_mean(Ifine,5);
        end
        o=extract_fft_v073(Ipix,4,Fs,400);
        ci=(L+1)/2; cc=o.C_k(ci,ci);
        vm=o.validMask; nrm=norm(double(o.C_k(vm)),'fro');
        dftmax=0;
        for px=[ci ci+3]
          xx=double(Ipix(px,1,1,:)); xx=xx-mean(xx(:));
          Xd=sum(xx(:).*exp(-2i*pi*160*(0:N-1)'/N));
          Xf=double(o.Xk(px));
          dftmax=max(dftmax,abs(Xf-Xd)/max(abs(Xd),realmin));
        end
        hkey=sprintf('D%d_zf%g_x%+g',D,zf,-5);
        if isfield(holdData,hkey), relH=holdData.(hkey).relEs; else, relH=NaN; end
        fprintf(gates,'%d,%g,%s,%g,%g,0,%.17g,%.17g,%.17g,%.17g,%.6f,%.17g,%.3g,PRESCRIBED_TRAJECTORY_NOT_REAL_MAGNETIC_MOTION\n', ...
          D,zf,ttype,ampn,ttype,abs(cc),real(cc),imag(cc),nrm,nnz(vm)/(L*L),relH,dftmax);
        nEval=nEval+1;
        key=sprintf('D%d_zf%g_%s_a%d',D,zf,ttype,ampn);
        res.(matlab.lang.makeValidName(key))=struct('C400',o.C_k,'absC',o.absC,'absCenter',abs(cc),'D',D,'zf',zf,'ttype',ttype,'amp',ampn,'dftmax',dftmax);
        if D==60 && zf==450
          for tau=[1e-4 2e-4]
            IserE=zeros(L,L,1,N,'single'); M=5; IfineE=zeros(205,205,'single');
            for m=0:M-1
              tE=tj+m*tau/M; xE=ampn*cos(2*pi*ttype*tE);
              for j2=1:N
                acc=zeros(205,205,'single');
                for m2=0:M-1
                  tE=tj(j2)+m2*tau/M; xE=ampn*cos(2*pi*ttype*tE);
                  [wa,wb,ia,ib]=linWeights(xE,xg);
                  acc=acc+single(Iref + wa*Lm{ia}+wb*Lm{ib} + wa^2*Dm{ia}+wb^2*Dm{ib} + wa*wb*Qm{ia,ib})/M;
                end
                IfineE(:)=acc; IserE(:,:,1,j2)=pixel_mean(IfineE,5);
              end
            end
            oE=extract_fft_v073(IserE,4,Fs,400);
            ccE=oE.C_k(ci,ci);
            ekey=sprintf('D60_zf450_%s_a%d_tau%g',ttype,ampn,tau);
            res.(matlab.lang.makeValidName(ekey))=struct('C400',oE.C_k,'absCenter',abs(ccE),'tau',tau,'ttype',ttype,'amp',ampn);
            nEval=nEval+1;
          end
        end
      end
    end
  end
end
save(fullfile(numOut,'v074_dynamic_forward_examples.mat'),'-struct','res','-v7.3');
% ---------- 2 analytic negative controls (explicit DFT; full-stack FFT exceeded memory preference) ----------
for nc=1:2
  m=0.05*nc; fN=400;
  tj=(0:N-1)'/Fs;
  x1=double(1+m*cos(2*pi*fN*tj)); % uniform pixels: compute the center pixel explicitly
  Im1=mean(x1);
  X1=sum((x1-Im1).*exp(-2i*pi*160*(0:N-1)'/N));
  C1=2*X1/(N*Im1); % analytic: |C1|=m exactly
  C=m*ones(L,L)*exp(1i*angle(C1)); % uniform field: identical pixels
  oNstruct=struct();
  res.(sprintf('NEG%d',nc))=struct('C400',C,'absCenter',abs(C(ci,ci)),'expected',m,'method','explicit_DFT');
  nEval=nEval+1;
end
save(fullfile(numOut,'v074_dynamic_forward_examples.mat'),'-struct','res','-v7.3');
fclose(gates);
nf=fopen(fullfile(tabDir,'v074_negative_controls.csv'),'w');
fprintf(nf,'case,modulation_depth,expected_absC400,computed_absC400,abs_err,status,note\n');
for nc=1:2
  rN=res.(sprintf('NEG%d',nc)); m=0.05*nc;
  fprintf(nf,'NEG%d,%.3f,%.17g,%.17g,%.17g,%s,ANALYTIC_SIGNAL_OPERATOR_FIXTURE: uniform intensity modulation alone produces a 400 Hz FFT peak\n', ...
    nc,m,m,abs(rN.absCenter),abs(abs(rN.absCenter)-m),tern2(abs(abs(rN.absCenter)-m)<1e-5,'PASS','FAIL'));
end
fclose(nf);
fprintf('[074C2] done: %d time-series evaluations\n',nEval);
end
% ---------------- helpers ----------------
function a5=anchors5(anchor,D,zf)
xs=[-20 -10 0 10 20]; es=cell(1,5);
for i=1:5
  a=anchor.(matlab.lang.makeValidName(sprintf('D%d_zf%g_x%+g',D,zf,xs(i))));
  es{i}=a.Es;
  if i==1, Eref=a.Eref; end
end
a5=struct('Es',cat(4,es{:}),'Eref',Eref,'x',xs);
end

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
function [blk,ErefB]=roiBlocks(E,Eref)
H=size(E,1); q=5; Np=H/q; c0=(Np+1)/2; i0=round((c0-20-0.5)*q)+1;
blk=cell(1,5);
for i=1:5
  bi=E(i0:(i0+204),i0:(i0+204),:,i);
  blk{i}=reshape(bi,205,205,3);
end
ErefB=reshape(Eref(i0:(i0+204),i0:(i0+204),:,:),205,205,3);
end
function [wa,wb,ia,ib]=linWeights(x,xg)
x=max(min(x,xg(end)),xg(1));
ia=find(x>=xg(1:end-1) & x<=xg(2:end),1,'last');
if isempty(ia), ia=numel(xg)-1; end
wb=(x-xg(ia))/(xg(ia+1)-xg(ia)); wa=1-wb; ib=ia+1;
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
function out=tern2(c,a,b), if c, out=a; else, out=b; end, end





