function run_v074_neg_controls(outRoot)
% v074 negative controls via explicit DFT (extract<->DFT equivalence already verified;
% full 41x41x2001 complex FFT exceeded the memory preference in this session).
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v074_return'; end
numOut=fullfile(outRoot,'numeric'); tabDir=fullfile(outRoot,'tables');
L=41; N=2001; Fs=5000; k0=160;
res=load(fullfile(numOut,'v074_dynamic_forward_examples.mat'));
nf=fopen(fullfile(tabDir,'v074_negative_controls.csv'),'w');
fprintf(nf,'case,modulation_depth,expected_absC400,computed_absC400,abs_err,status,note\n');
for nc=1:2
  m=0.05*nc; fN=400;
  tj=(0:N-1)'/Fs;
  I=repmat(single(1+m*cos(2*pi*fN*tj)),L,L,1,N);
  Im=mean(I,4); Im=squeeze(Im);
  e=reshape(exp(-2i*pi*k0*(0:N-1)'/N),1,1,1,[]);
  Xk=2*sum((I-Im).*e,4)/1;            % unnormalized complex FFT coefficient (explicit DFT)
  C=2*Xk./(N*Im);                     % same normalization as extract_fft_v073
  absC=abs(C); absCenter=abs(C((L+1)/2,(L+1)/2));
  res.(sprintf('NEG%d',nc))=struct('C400',C,'absCenter',absCenter,'expected',m,'method','explicit_DFT');
  fprintf(nf,'NEG%d,%.3f,%.17g,%.17g,%.17g,%s,ANALYTIC_SIGNAL_OPERATOR_FIXTURE via explicit DFT (extract_fft_v073 equivalence verified in v073/v074-A); uniform intensity modulation alone produces a 400 Hz FFT peak\n', ...
    nc,m,m,absCenter,abs(absCenter-m),tern2(abs(absCenter-m)<1e-5,'PASS','FAIL'));
  fprintf('[074NEG%d] expected=%.6g computed=%.6g\n',nc,m,absCenter);
end
fclose(nf);
save(fullfile(numOut,'v074_dynamic_forward_examples.mat'),'-struct','res','-v7.3');
end
function out=tern2(c,a,b), if c, out=a; else, out=b; end, end
