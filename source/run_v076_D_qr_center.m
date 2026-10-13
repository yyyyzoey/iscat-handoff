function run_v076_D_qr_center(outRoot, v074Root)
% Correct centre-pixel (physical pixel 33, fine 161:165 block) time series per
% trajectory via the quadratic-form expansion; QR harmonic decomposition.
if nargin<2||isempty(v074Root), v074Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
numOut=fullfile(outRoot,'numeric'); tabDir=fullfile(outRoot,'tables');
logDir=fullfile(outRoot,'logs'); if ~isfolder(logDir), mkdir(logDir); end
diary(fullfile(logDir,'matlab_native_run.log')); cl=onCleanup(@() diary('off'));
Ds=[30 60 100]; zfs=[450 550]; xs=[-20 -10 0 10 20];
N=2001; Fs=5000;
qf=fopen(fullfile(tabDir,'v076_motion_harmonics_qrfit.csv'),'w');
fprintf(qf,'D_nm,zf_nm,trajectory_type,amplitude_nm_assumed,C200_fit,C400_fit,C800_fit,residual_rms,bin161_absC400,bin161_over_fit,series_saved,note\n');
res=struct(); saved=struct();
for D=Ds
  for zf=zfs
    Es=cell(1,5); 
    for i=1:5
      A=load(fullfile(v074Root,'numeric','render_cache',sprintf('D%d_zf%g_x%+g.mat',D,zf,xs(i))),'a');
      Es{i}=A.a.Es(161:165,161:165,:); % centre physical pixel fine block (25 subpixels)
      if i==3, ErefC=A.a.Eref(161:165,161:165,:); end
    end
    E=cat(4,Es{:});
    nA=5; Lm=zeros(25,nA); Dm=zeros(25,nA); Qm=zeros(25,nA,nA);
    for i=1:nA
      Lm(:,i)=reshape(2*real(sum(conj(ErefC).*E(:,:,:,i),3)),25,1); Dm(:,i)=reshape(sum(abs(E(:,:,:,i)).^2,3),25,1);
      for j2=i+1:nA
        Qm(:,i,j2)=reshape(2*real(sum(conj(E(:,:,:,i)).*E(:,:,:,j2),3)),25,1);
      end
    end
    Iref=sum(abs(ErefC).^2,3); Iref=Iref(:);
    for ttype=[200 400]
      for ampn=[5 20]
        tj=(0:N-1)'/Fs; xj=ampn*cos(2*pi*ttype*tj);
        Iser=zeros(1,1,1,N,'single');
        for j2=1:N
          x=max(min(xj(j2),20),-20);
          ia=find(x>=xs(1:end-1) & x<=xs(2:end),1,'last');
          wb=(x-xs(ia))/(xs(ia+1)-xs(ia)); wa=1-wb;
          v=Iref + wa*Lm(:,ia)+wb*Lm(:,ia+1) + wa^2*Dm(:,ia)+wb^2*Dm(:,ia+1) + wa*wb*Qm(:,ia,ia+1);
          Iser(1,1,1,j2)=single(mean(v));
        end
        o=extract_fft_v073(Iser,4,Fs,400);
        Imean=mean(double(Iser(1,1,1,:)));
        I=double(reshape(Iser(1,1,1,:),[],1)); Im=mean(I); Ic=I-Im;
        tj2=(0:N-1)'/Fs;
        B=[ones(N,1),cos(2*pi*200*tj2),sin(2*pi*200*tj2),cos(2*pi*400*tj2),sin(2*pi*400*tj2),cos(2*pi*800*tj2),sin(2*pi*800*tj2)];
        coef=B\Ic; resid=Ic-B*coef;
        C200=2*abs(complex(coef(2),-coef(3)))/(N*Im);
        C400=2*abs(complex(coef(4),-coef(5)))/(N*Im);
        C800=2*abs(complex(coef(6),-coef(7)))/(N*Im);
        rmsR=rms(resid);
        binAbs=abs(o.C_k); % extract run on the 1x1 pixel stack -> single-pixel C400
        tname=sprintf('M%d',ttype);
        fprintf(qf,'%d,%g,%s,%g,%.17g,%.17g,%.17g,%.17g,%.17g,%.6f,saved,%s\n', ...
          D,zf,tname,ampn,C200,C400,C800,rmsR,binAbs,binAbs/max(C400,realmin),'centre physical pixel 33 (fine 161:165 block) direct series');
        key=matlab.lang.makeValidName(sprintf('D%d_zf%g_%s_a%d',D,zf,tname,ampn));
        res.(key)=struct('series',double(Iser(1,1,1,:)),'C200',C200,'C400',C400,'C800',C800,'rmsR',rmsR,'binAbs',binAbs,'D',D,'zf',zf,'ttype',tname,'amp',ampn);
      end
    end
  end
end
save(fullfile(numOut,'v076_center_roi_harmonic_small_examples.mat'),'-struct','res','-v7.3');
fclose(qf);
fprintf('[076D-QR] done\n');
end



