function run_v076_D_harmonics(outRoot, v075Root)
% v076 D: separate true 2f component from finite-window leakage of the 200 Hz
% fundamental; exact two-term complex (Dirichlet) references; odd/even symmetry.
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
if nargin<2||isempty(v075Root), v075Root='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return'; end
tabDir=fullfile(outRoot,'tables'); numOut=fullfile(outRoot,'numeric');
R=load(fullfile(numOut,'v076_dynamic_center_corrected.mat'));
N=2001; Fs=5000;
% ---------- 1) analytic fixtures with exact two-term complex reference ----------
ff=fopen(fullfile(tabDir,'v076_harmonic_leakage_exact_reference.csv'),'w');
fprintf(ff,'fixture_id,description,bin_k0,f_actual_Hz,expected_absC400_exact,computed_absC400_explicitDFT,abs_err,rel_err,status,note\n');
k0=160; k=161;
for fx=1:3
  switch fx
    case 1, m=0.05; comps=[200 0]; desc='200Hz-only intensity modulation (true 400Hz harmonic strictly zero)';
    case 2, m=0.05; comps=[400 0]; desc='400Hz-only intensity modulation';
    case 3, m=0.05; comps=[200 400]; desc='200+400Hz mixed, known phases (0 and 0)';
  end
  tj=(0:N-1)'/Fs;
  x1=ones(N,1);
  for cI=comps
    x1=x1+(m/2)*cos(2*pi*cI*tj); % each component depth m/2 so single-200 case gives naive C=m... 
  end
  % for comps=[200] the modulation depth at 200Hz is m/2 -> bin161 sees only leakage
  Im=mean(x1);
  Xc=sum((x1-Im).*exp(-2i*pi*k0*(0:N-1)'/N));
  Cc=2*Xc/(N*Im);
  % exact two-term reference: signal = sum_c (m/2)cos(2 pi f_c t)
  Xref=0;
  for cI=comps
    u1=cI/Fs-k0/N; u2=-cI/Fs-k0/N;
    G1=exp(1i*pi*u1*(N-1))*sin(pi*N*u1)/sin(pi*u1);
    G2=exp(1i*pi*u2*(N-1))*sin(pi*N*u2)/sin(pi*u2);
    Xref=Xref+(m/2)/2*(G1+G2); % (m/2) amplitude cos -> (m/2)/2*(G+Gconj-structured)
  end
  Cref=2*Xref/(N*Im);
  ae=abs(abs(Cc)-abs(Cref)); re=ae/max(abs(Cref),realmin);
  if ae<1e-7 || re<1e-5, st='PASS'; else, st='FAIL'; end
  fprintf(ff,'FIX%d,%s,%d,%.9f,%.17g,%.17g,%.17g,%.17g,%s,closed-form two-term complex reference (G_N incl. mirror term)\n',fx,desc,k0,399.80009995002496,abs(Cref),abs(Cc),ae,re,st);
end
fclose(ff);
% ---------- 2) per-trajectory QR harmonic decomposition at centre ----------
qf=fopen(fullfile(tabDir,'v076_motion_harmonics_qrfit.csv'),'w');
fprintf(qf,'D_nm,zf_nm,trajectory_type,amplitude_nm_assumed,C200_fit,C400_fit,C800_fit,residual_rms,bin161_absC400,bin161_over_fit,note\n');
fn=fieldnames(R);
for i=1:numel(fn)
  f=R.(fn{i});
  if ~isfield(f,'tseries_center'), continue; end
  I=double(f.tseries_center(:)); Im=mean(I); I=I-Im;
  tj=(0:N-1)'/Fs;
  B=[ones(N,1),cos(2*pi*200*tj),sin(2*pi*200*tj),cos(2*pi*400*tj),sin(2*pi*400*tj),cos(2*pi*800*tj),sin(2*pi*800*tj)];
  coef=B\I; resid=I-B*coef;
  % complex amplitudes: X_h=(N/2)(c_cos - i c_sin)
  C200=2*abs(complex(coef(2),-coef(3)))/(N*mean(double(f.tseries_center(:)))+Im*0+Im); % placeholder fixed below
  Imfull=mean(double(f.tseries_center(:)))+Im; % Im was subtracted; original mean = Im
  C200=2*abs(complex(coef(2),-coef(3)))/(N*(Im));
  C400=2*abs(complex(coef(4),-coef(5)))/(N*(Im));
  C800=2*abs(complex(coef(6),-coef(7)))/(N*(Im));
  rmsR=rms(resid);
  toks=regexp(fn{i},'D(\d+)_zf(\d+)_(M\d+)_a(\d+)','tokens','once');
  D=toks{1}; zf=toks{2}; tt=toks{3}; aa=toks{4};
  fprintf(qf,'%s,%s,%s,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%.6f,QR fit on centre-pixel series; C_h=2|X_h|/(N Imean) with Imean from the same series\n',D,zf,tt,aa,C200,C400,C800,rmsR,f.absCenter,f.absCenter/max(C400,realmin));
end
fclose(qf);
% ---------- 3) odd/even symmetry at the physical centre from holdout renders ----------
H=load(fullfile(v075Root,'numeric','v075_holdout_data.mat'));
of=fopen(fullfile(tabDir,'v076_odd_even_symmetry_and_derivatives.csv'),'w');
fprintf(of,'D_nm,zf_nm,kind,I_minus5,I_0,I_plus5,odd_component,even_component,first_diff,I0_boundary_check,note\n');
for nm={'D60_ZF450_XM0005000','D60_ZF450_XP0005000'}
  rec=H.(nm{1});
  q=5; i0=61;
  ItD=reshape(sum(abs(rec.Es_direct+rec.Eref).^2,3),325,325);
  Im5=pixel_mean(ItD(i0:i0+204,i0:i0+204),5);
  ItP=reshape(sum(abs(rec.Es_interp+rec.Eref).^2,3),325,325); %#ok<NASGU>
end
% need x=0 anchor for I(0): load from v074 cache
S=load(fullfile(fileparts(fileparts(mfilename('fullpath'))),'v074_return','numeric','render_cache','D60_zf450_x+0.mat'),'a');
It0=reshape(sum(abs(S.a.Eref+S.a.Es).^2,3),325,325);
I0c=pixel_mean(It0(61:265,61:265),5);
for nm={'D60_ZF450_XM0005000','D60_ZF450_XP0005000'}
  rec=H.(nm{1});
  ItD=reshape(sum(abs(rec.Es_direct+rec.Eref).^2,3),325,325);
  Ip=pixel_mean(ItD(61:265,61:265),5);
  sgn=-1; if contains(nm{1},'XP'), sgn=+1; end
  Im5=Ip(21,21); I0c5=I0c(21,21);
  odd=(Im5-I0c5)*sgn; even=(Im5+I0c5)/2-I0c5;
  % also an off-centre pixel (+5 px away)
  op=26;
  Im5o=Ip(21,21+5*sgn); I0c5o=I0c(21,21+5*sgn);
  oddo=(Im5o-I0c5o)*sgn; eveno=(Im5o+I0c5o)/2-I0c5o;
  fprintf(of,'60,450,%s,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,odd/even decomposition at physical centre; I0 boundary check=central pixel of x=0 render\n', ...
    nm{1},Im5,I0c5,Ip(21,21),odd,even,Im5-I0c5,I0c5);
  fprintf(of,'60,450,%s_off5px,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,off-centre pixel 5 px away\n', ...
    nm{1},Im5o,I0c5o,Ip(21,21+5*sgn),oddo,eveno,Im5o-I0c5o,I0c5o);
end
fclose(of);
fprintf('[076D] done\n');
end


