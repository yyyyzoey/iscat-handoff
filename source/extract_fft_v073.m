function out=extract_fft_v073(stack, timeDim, Fs, targetFreq)
% v073 extractor (pure function; user scripts NOT modified).
% Implements test_with_contrast.m semantics on an explicit time dimension:
%   Imean = mean over time; signal = stack - Imean; F = fft(signal,[],timeDim);
%   X_k = F at bin k=k0+1 (k0 = round(targetFreq*N/Fs), 0-based);
%   scale = 2 (non-DC/non-Nyquist) or 1 (DC/Nyquist);
%   A_k = scale*|X_k|/N (gray-level one-sided amplitude);
%   C_k = scale*X_k/(N*Imean) inside validMask, complex NaN outside (NOT zero);
%   validMask = isfinite(Imean) & Imean > 0.01*median(Imean(isfinite&>0)).
% stack: H x W x N (timeDim=3) or H x W x 1 x N (timeDim=4). Single or double.
% HARD AXIS GUARD: error if timeDim > ndims(stack) (v072 replay failure mode).
validateattributes(timeDim,{'numeric'},{'scalar','integer','positive'});
if timeDim>ndims(stack)
  error('extract_fft_v073:BAD_TIME_DIM', ...
    ['timeDim=%d exceeds ndims(stack)=%d. fft(X,[],dim) with dim>ndims returns X ', ...
     'UNCHANGED (the v072 replay bug). Refusing to continue.'],timeDim,ndims(stack));
end
N=size(stack,timeDim);
validateattributes(N,{'numeric'},{'scalar','integer','positive'});
assert(N==2001,'v073 contract requires N=2001, got %d',N);
validateattributes(Fs,{'numeric'},{'scalar','positive'});
Imean=mean(stack,timeDim);
Imean=squeeze(Imean);
signal=stack-Imean;   % implicit broadcasting over time dim
F=fft(signal,[],timeDim);
k0=round(targetFreq*N/Fs);
k=k0+1;
assert(k>=2 && k<=floor(N/2)+1,'bin %d outside one-sided range',k);
idx=cell(1,ndims(F)); for d=1:ndims(F), idx{d}=':'; end
idx{timeDim}=k;
Xk=F(idx{:});
Xk=squeeze(Xk);
isDC=(k==1); isNyq=(mod(N,2)==0 && k==N/2+1);
if isDC||isNyq, scale=1; else, scale=2; end
A=scale*abs(Xk)/N;
A=squeeze(A);
pos=Imean(Imean>0 & isfinite(Imean));
assert(~isempty(pos),'no positive finite Imean pixels');
meanFloor=0.01*median(pos);
validMask=isfinite(Imean)&Imean>meanFloor;
C=complex(nan(size(Imean),'single'),nan(size(Imean),'single'));
C(validMask)=scale*Xk(validMask)./(N*Imean(validMask));
out=struct('Xk',Xk,'A_k',A,'C_k',C,'absC',abs(C),'phase',angle(C), ...
  'Imean',Imean,'validMask',validMask,'meanFloor',meanFloor, ...
  'k',k,'k0',k0,'actualFreq',(k0)*Fs/N,'targetFreq',targetFreq, ...
  'Fs',Fs,'N',N,'scale',scale,'timeDim',timeDim);
end

