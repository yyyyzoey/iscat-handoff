function run_v075_C_dynamic_redo(outRoot, v074Root)
% v075 C: recompute the 24 prescribed trajectories + 8 exposure variants with
% collision-free keys. Zero new renders: anchors from v074 cache, holdouts from v075 cache.
if nargin<2||isempty(v074Root), v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return'; end
tabDir=fullfile(outRoot,'tables'); if ~isfolder(tabDir), mkdir(tabDir); end
numOut=fullfile(outRoot,'numeric'); if ~isfolder(numOut), mkdir(numOut); end
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
projectRoot=fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
v74cache=fullfile(v074Root,'numeric','render_cache');
v75cache=fullfile(numOut,'render_cache');
SIG=+1; Ds=[30 60 100]; zfs=[450 550]; xs=[-20 -10 0 10 20];
L=41; N=2001; Fs=5000;
% gate: all 24 holdouts must have passed (verified in v075_holdout24_corrected.csv)
hd=load(fullfile(numOut,'v075_holdout_data.mat'));
holdData=hd;
allPass=true; fn=fieldnames(holdData);
for i=1:numel(fn), if ~strcmp(holdData.(fn{i}).st,'PASS'), allPass=false; end; end
fprintf('[075C] gate: all 24 holdouts PASS = %d\n',allPass);
% gate/plan CSV
gf=fopen(fullfile(tabDir,'v075_motion_plan_and_gate.csv'),'w');
fprintf(gf,'D_nm,zf_nm,gate_status,trajectories_recomputed,note\n');
for D=Ds
  for zf=zfs
    fprintf(gf,'%d,%g,%s,%d,per-(D,zf) holdouts both sides PASS under fixed keys\n',D,zf,tern2(allPass,'PASS','FAIL'),2);
  end
end
fclose(gf);
if ~allPass, error('holdout gate failed - dynamic redo not authorised'); end
% ---------- load anchors via fixed keys (zero new renders) ----------
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
fprintf('[075C] 30 anchors loaded via position_key (zero renders)\n');
% ---------- 24 trajectories ----------
gf=fopen(fullfile(tabDir,'v075_dynamic_C400_corrected.csv'),'w');
fprintf(gf,'D_nm,zf_nm,trajectory_type,amplitude_nm_assumed,frequency_Hz,exposure_s_assumed,absC400_center,complexC400_center_real,complexC400_center_imag,ROI_normC400_valid,ROI_valid_fraction,FFT_DFT_relmax,harmonic_A200_bin80,harmonic_A400_bin161,harmonic_A800_bin320,flags\n');
res=struct(); nEval=0;
for D=Ds
  for zf=zfs
    xs5v=[-20 -10 0 10 20]; Es=cell(1,5);
    for i=1:5
      ak=anchor.(position_key(D,zf,xs5v(i))); Es{i}=ak.Es;
      if i==3, Eref=ak.Eref; end
    end
    E=cat(4,Es{:});
    [blk,ErefB]=roiBlocks(E,Eref);
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
          [wa,wb,ia,ib]=linWeights(xj(j2),xs5v);
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
        % harmonic structure via explicit DFT on the ROI (bins 80/161/320)
        ImeanS=squeeze(mean(Ipix,4));
        A80=median(abs(2*sum((Ipix-ImeanS).*reshape(exp(-2i*pi*80*(0:N-1)'/N),1,1,1,[]),4)./(N*ImeanS)),'all');
        A400=median(abs(2*sum((Ipix-ImeanS).*reshape(exp(-2i*pi*160*(0:N-1)'/N),1,1,1,[]),4)./(N*ImeanS)),'all');
        A800=median(abs(2*sum((Ipix-ImeanS).*reshape(exp(-2i*pi*320*(0:N-1)'/N),1,1,1,[]),4)./(N*ImeanS)),'all');
        tname=sprintf('M%d',ttype);
        fprintf(gf,'%d,%g,%s,%g,%g,0,%.17g,%.17g,%.17g,%.17g,%.6f,%.3g,%.17g,%.17g,%.17g,PRESCRIBED_TRAJECTORY_NOT_REAL_MAGNETIC_MOTION\n', ...
          D,zf,tname,ampn,ttype,abs(cc),real(cc),imag(cc),nrm,nnz(vm)/(L*L),dftmax,A80,A400,A800);
        nEval=nEval+1;
        key=sprintf('D%d_zf%g_%s_a%d',D,zf,tname,ampn);
        res.(matlab.lang.makeValidName(key))=struct('C400',o.C_k,'absC',o.absC,'absCenter',abs(cc),'D',D,'zf',zf,'ttype',tname,'amp',ampn,'dftmax',dftmax,'A80',A80,'A400',A400,'A800',A800);
        % ---------- 8 exposure variants (D60/zf450 only) ----------
        if D==60 && zf==450
          for tau=[1e-4 2e-4]
            IpixE=zeros(L,L,1,N,'single');
            for j2=1:N
              acc=zeros(205,205,'single');
              for m2=0:4
                tE=tj(j2)+m2*tau/5; xE=ampn*cos(2*pi*ttype*tE);
                [wa,wb,ia,ib]=linWeights(xE,xs5v);
                acc=acc+single(Iref + wa*Lm{ia}+wb*Lm{ib} + wa^2*Dm{ia}+wb^2*Dm{ib} + wa*wb*Qm{ia,ib})/5;
              end
              IpixE(:,:,1,j2)=pixel_mean(acc,5);
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
save(fullfile(numOut,'v075_dynamic_C400_corrected.mat'),'-struct','res','-v7.3');
fclose(gf);
% ---------- exposure CSV ----------
ef=fopen(fullfile(tabDir,'v075_exposure8_corrected.csv'),'w');
fprintf(ef,'case,trajectory_type,amplitude_nm_assumed,tau_s,absC400_center,absC400_tau0,rel_change,note\n');
for ttype=[200 400]
  for ampn=[5 20]
    baseKey=matlab.lang.makeValidName(sprintf('D60_zf450_M%d_a%d',ttype,ampn));
    b=res.(baseKey);
    for tau=[1e-4 2e-4]
      ekey=matlab.lang.makeValidName(sprintf('D60_zf450_M%d_a%d_tau%g',ttype,ampn,tau));
      v=res.(ekey);
      fprintf(ef,'%s,%s,%d,%g,%.17g,%.17g,%.6f,SYNTHETIC tau assumption only; not real exposure\n', ...
        ekey,tname_of(ttype),ampn,tau,v.absCenter,b.absCenter,(v.absCenter-b.absCenter)/max(b.absCenter,realmin));
    end
  end
end
fclose(ef);
% ---------- evenness / leakage ----------
mf=fopen(fullfile(tabDir,'v075_motion_evenness_and_leakage.csv'),'w');
fprintf(mf,'D_nm,zf_nm,trajectory_type,amplitude_nm_assumed,A200Hz_bin80,A400Hz_bin161,A800Hz_bin320,leakage_note\n');
for D=Ds
  for zf=zfs
    for ttype=[200 400]
      for ampn=[5 20]
        key=matlab.lang.makeValidName(sprintf('D%d_zf%g_M%d_a%d',D,zf,ttype,ampn));
        rL=res.(key);
        fprintf(mf,'%d,%g,M%d,%g,%.17g,%.17g,%.17g,%s\n',D,zf,ttype,ampn,rL.A80,rL.A400,rL.A800, ...
          'M200: 400Hz is the second harmonic of the prescribed 200Hz motion (geometric nonlinearity); M400: 400Hz is the fundamental; bin 161=399.8001Hz, off-bin leakage applies');
      end
    end
  end
end
fclose(mf);
fprintf('[075C] done: %d evaluations\n',nEval);
end
function s=tname_of(t), s=sprintf('M%d',t); end


function out=tern2(c,a,b), if c, out=a; else, out=b; end, end

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
