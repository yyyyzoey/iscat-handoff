function run_v076_C_dynamic_center(outRoot, v075Root, v074Root)
% v076 C: recompute 24 prescribed trajectories + 8 exposure variants with the
% CORRECT physical-centre ROI (fine 61:265). Zero BEM, zero new renders
% (anchors from v074 cache, holdouts cached in v075). Old v075 values kept side-by-side.
if nargin<2||isempty(v075Root), v075Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return'; end
if nargin<3||isempty(v074Root), v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
projectRoot=fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
v74cache=fullfile(v074Root,'numeric','render_cache'); % v074 cache holds the 30 signed anchor states
SIG=+1; Ds=[30 60 100]; zfs=[450 550]; xs=[-20 -10 0 10 20];
L=41; N=2001; Fs=5000; q=5;
% correct centre ROI: physical pixels 13:53 -> fine 61:265
i0=(13-1)*q+1; assert(i0==61);
% old v075 centre values for side-by-side
old=containers.Map('KeyType','char','ValueType','char');
try
  o75=readtable(fullfile(v075Root,'tables','v075_dynamic_C400_corrected.csv'),'VariableNamingRule','preserve');
  for rI=1:height(o75)
    key=sprintf('D%d_zf%g_%s_a%d',o75.D_nm(rI),o75.zf_nm(rI),o75.trajectory_type{rI},o75.amplitude_nm_assumed(rI));
    old(key)=sprintf('%.17g',o75.absC400_center(rI));
  end
catch
  old('NA')='NA';
end
anchor=struct();
for D=Ds
  for zf=zfs
    for x=xs
      key=position_key(D,zf,x);
      A=load(fullfile(v74cache,sprintf('D%d_zf%g_x%+g.mat',D,zf,x)));
      anchor.(key)=struct('Es',A.a.Es,'Eref',A.a.Eref,'x',x);
    end
  end
end
fprintf('[076C] 30 anchors loaded (zero renders)\n');
gf=fopen(fullfile(tabDir,'v076_dynamic_center_corrected.csv'),'w');
fprintf(gf,'D_nm,zf_nm,trajectory_type,amplitude_nm_assumed,frequency_Hz,absC400_center_corrected,absC400_center_v075_legacy,complexC400_center_real,complexC400_center_imag,ROI_normC400_valid,ROI_normC400_v075_legacy,ROI_valid_fraction,FFT_DFT_relmax,A400bin161_median,A200bin80_median,A800bin320_median,flags\n');
res=struct(); nEval=0;
for D=Ds
  for zf=zfs
    Es=cell(1,5);
    for i=1:5
      ak=anchor.(position_key(D,zf,xs(i))); Es{i}=ak.Es;
      if i==3, Eref=ak.Eref; end
    end
    E=cat(4,Es{:});
    [blk,ErefB]=roiBlocksCorrect(E,Eref);
    nA=5; Lm=cell(1,nA); Dm=cell(1,nA);
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
          [wa,wb,ia,ib]=linWeights(xj(j2),xs);
          Ifine(:)=single(Iref + wa*Lm{ia}+wb*Lm{ib} + wa^2*Dm{ia}+wb^2*Dm{ib} + wa*wb*Qm{ia,ib});
          Ipix(:,:,1,j2)=pixel_mean(Ifine,q);
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
        % harmonics at correct ROI (explicit DFT medians over valid pixels)
        ImS=squeeze(mean(Ipix,4));
        A80=median(abs(2*sum((Ipix-ImS).*reshape(exp(-2i*pi*80*(0:N-1)'/N),1,1,1,[]),4)./(N*ImS)),'all');
        A400=median(abs(2*sum((Ipix-ImS).*reshape(exp(-2i*pi*160*(0:N-1)'/N),1,1,1,[]),4)./(N*ImS)),'all');
        A800=median(abs(2*sum((Ipix-ImS).*reshape(exp(-2i*pi*320*(0:N-1)'/N),1,1,1,[]),4)./(N*ImS)),'all');
        okey=matlab.lang.makeValidName(sprintf('D%d_zf%g_M%d_a%d',D,zf,ttype,ampn));
        if isKey(old,okey), oldV=old(okey); else, oldV='NA'; end
        tname=sprintf('M%d',ttype);
        fprintf(gf,'%d,%g,%s,%g,%g,%.17g,%s,%.17g,%.17g,%.17g,%s,%.6f,%.3g,%.17g,%.17g,%.17g,PRESCRIBED_TRAJECTORY_NOT_REAL_MAGNETIC_MOTION\n', ...
          D,zf,tname,ampn,ttype,abs(cc),oldV,real(cc),imag(cc),nrm,'NA',nnz(vm)/(L*L),dftmax,A400,A80,A800);
        nEval=nEval+1;
        key=sprintf('D%d_zf%g_%s_a%d',D,zf,tname,ampn);
        res.(matlab.lang.makeValidName(key))=struct('C400',o.C_k,'absC',o.absC,'absCenter',abs(cc),'D',D,'zf',zf,'ttype',tname,'amp',ampn, ...
          'dftmax',dftmax,'A80',A80,'A400',A400,'A800',A800, ...
          'tseries_center',double(Ipix(ci,1,1,:)),'tseries_off1',double(Ipix(ci+5,1,1,:)),'tseries_off2',double(Ipix(ci-5,1,1,:)));
        % exposure variants (D60/zf450)
        if D==60 && zf==450
          for tau=[1e-4 2e-4]
            IpixE=zeros(L,L,1,N,'single');
            for j2=1:N
              acc=zeros(205,205,'single');
              for m2=0:4
                tE=tj(j2)+m2*tau/5; xE=ampn*cos(2*pi*ttype*tE);
                [wa,wb,ia,ib]=linWeights(xE,xs);
                acc=acc+single(Iref + wa*Lm{ia}+wb*Lm{ib} + wa^2*Dm{ia}+wb^2*Dm{ib} + wa*wb*Qm{ia,ib})/5;
              end
              IfineE=acc; IpixE(:,:,1,j2)=pixel_mean(IfineE,q);
            end
            oE=extract_fft_v073(IpixE,4,Fs,400);
            ccE=oE.C_k(ci,ci);
            ekey=sprintf('D60_zf450_%s_a%d_tau%g',tname,ampn,tau);
            res.(matlab.lang.makeValidName(ekey))=struct('C400',oE.C_k,'absCenter',abs(ccE),'tau',tau,'ttype',tname,'amp',ampn);
            nEval=nEval+1;
          end
        end
      end
    end
  end
end
save(fullfile(numOut,'v076_dynamic_center_corrected.mat'),'-struct','res','-v7.3');
fclose(gf);
% exposure CSV with sinc reference
ef=fopen(fullfile(tabDir,'v076_exposure8_center_corrected.csv'),'w');
fprintf(ef,'case,trajectory_type,amplitude_nm_assumed,tau_s,interval_convention,absC400_center_tau,absC400_center_tau0,rel_change,sinc_reference_pure_sine,note\n');
for ttype=[200 400]
  for ampn=[5 20]
    bKey=matlab.lang.makeValidName(sprintf('D%d_zf%g_%s_a%d',60,450,tname_of(ttype),ampn));
    b=res.(bKey);
    for tau=[1e-4 2e-4]
      eKey=matlab.lang.makeValidName(sprintf('D%d_zf%g_%s_a%d_tau%g',60,450,tname_of(ttype),ampn,tau));
      v=res.(eKey);
      sincRef=abs(sinc_of(ttype*tau));
      fprintf(ef,'D60_zf450_%s_a%d,M%d,%d,%g,[t_j,t_j+tau] forward 5-node,%0.6g,%0.6g,%0.6f,%0.6f,SYNTHETIC tau only; sinc reference valid for pure sinusoid intensity modulation\n', ...
        tname_of(ttype),ampn,tname_of(ttype),ampn,tau,v.absCenter,b.absCenter,(v.absCenter-b.absCenter)/max(b.absCenter,realmin),sincRef);
    end
  end
end
fclose(ef);
fprintf('[076C] done: %d evaluations\n',nEval);
end
function s=tname_of(t), s=sprintf('M%d',t); end
function v=sinc_of(x), v=1; m=x~=0; v(m)=sin(pi*x(m))./(pi*x(m)); end
function [blk,ErefB]=roiBlocksCorrect(E,Eref)
H=size(E,1); q=5; i0=(13-1)*q+1; % =61, physical pixels 13:53
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

