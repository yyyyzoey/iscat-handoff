function run_v067_comprehensive(outRoot)
% v067: B true homogeneous 30/100nm + C 27-condition Frobenius + D field decomposition + D3 zero-crossing.
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v042_handoff\iSCAT_v042_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v041_handoff\iSCAT_v041_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v048_handoff\iSCAT_v048_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\handoff\matlab');
if nargin<1, outRoot=fullfile(projectRoot,'v067_return'); end
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));
nr=2.349; kap=0.083; nP=complex(nr,kap);

% ==== B: true homogeneous 30/100nm ====
for D=[30,100]
  sid=sprintf('D%d',D);
  f1=fullfile(outRoot,sprintf('%s_homog1444.mat',sid));
  if isfile(f1), fprintf('[067:B] %s cache hit\n',sid); continue; end
  mw=Material(1.33^2,1); mp=Material(nP^2,1);
  n_read=mp.n(2*pi/520);
  assert(abs(real(n_read)-nr)<=1e-9 && abs(imag(n_read)-kap)<=1e-9,'MATERIAL_READBACK_FAIL');
  fprintf('[067:B] %s material readback n=%.10g%+.10gi OK\n',sid,real(n_read),imag(n_read));
  p=trisphere(1444,D);
  tau=BoundaryEdge([mw,mp],p,[2,1]);
  qA=quadboundary.rules('quad3',triquad(3));
  qN=quadboundary.rules('quad3',triquad(11));
  bem=galerkin.bemsolver(tau,'rules',qA,'rules1',qN,'nduffy',3,'relcutoff',2,'order',3,'waitbar',0);
  exc=galerkin.planewave([1,0,0],[0,0,1],'rules',quadboundary.rules('quad3',triquad(3)));
  k0=2*pi/520;
  fprintf('[067:B] %s homogeneous BEM start\n',sid);
  t0=tic; sol=bem\exc(tau,k0); solve_s=toc(t0);
  % Mie comparison
  ms=miesolver(mp,mw,D);
  [dirRef,wRef]=iscat04.sphere_rule(48,97);
  eB=farfields(sol,dirRef); eB=squeeze(eB); if ~ismatrix(eB), eB=reshape(eB,[],3); end
  eM=farscattering(ms,k0,[1,0,0],dirRef); eM=eM.e;
  fm=iscat04.field_metrics(eB,eM,wRef);
  bs=scattering(exc,sol); ba=absorption(exc,sol); bx=extinction(exc,sol);
  as=scattering(ms,k0); aa=absorption(ms,k0); ax=extinction(ms,k0);
  es=abs(bs-as)/max(abs(as),realmin); ea=abs(ba-aa)/max(abs(aa),realmin); ex=abs(bx-ax)/max(abs(ax),realmin);
  passed=fm.raw_complex_relative_L2<0.02 && es<0.02 && ea<0.02 && ex<0.02;
  save(f1,'sol','solve_s','fm','bs','as','ba','aa','bx','ax','es','ea','ex','passed','-v7.3');
  fprintf('[067:B] %s homogeneous solve %.1fs rawL2=%.4f sca=%.4f abs=%.4f ext=%.4f PASS=%d\n', ...
    sid,solve_s,fm.raw_complex_relative_L2,es,ea,ex,passed);
end

% ==== C+D: 27-condition Frobenius + field decomposition + apertures ====
od65='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v065_return';
cx=33; ix=(cx-20):(cx+20);
Zf=375:25:575; sizes=[30,60,100];
apertures=[21,31,41,51,61,65];
res={};
for D=sizes
  sid=sprintf('D%d',D);
  sp=load(fullfile(od65,sprintf('%s_s_576.mat',sid)),'s'); sp=sp.s;
  sf=load(fullfile(od65,sprintf('%s_s_1444.mat',sid)),'s'); sf=sf.s;
  for zf=Zf
    cp=sp.cfg; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
    rp=render_system(sp,cp);
    cf=sf.cfg; cf.focus_nm=[0,0,zf]; cf.sampling.subpixels=5;
    rf=render_system(sf,cf);
    % D1: field decomposition (Es, Eref, I0, Cs, Cint from render_system outputs)
    Es_p=rp.Esca; Er_p=rp.Eref; I0_p=rp.Iref;
    Cs_p=pixel_mean(sum(abs(Es_p).^2,3),5)./I0_p;
    Cint_p=pixel_mean(2*real(sum(conj(Er_p).*Es_p,3)),5)./I0_p;
    Ctot_p=Cs_p+Cint_p;
    Es_f=rf.Esca; Er_f=rf.Eref; I0_f=rf.Iref;
    Cs_f=pixel_mean(sum(abs(Es_f).^2,3),5)./I0_f;
    Cint_f=pixel_mean(2*real(sum(conj(Er_f).*Es_f,3)),5)./I0_f;
    Ctot_f=Cs_f+Cint_f;
    % algebraic closure
    close_p=max(abs(Ctot_p(:)-rp.contrast(:)))/max(1,max(abs(rp.contrast(:))+abs(Cs_p(:))+abs(Cint_p(:))));
    close_f=max(abs(Ctot_f(:)-rf.contrast(:)))/max(1,max(abs(rf.contrast(:))+abs(Cs_f(:))+abs(Cint_f(:))));
    % C1: Frobenius (correct)
    P=rp.contrast(ix,ix); R=rf.contrast(ix,ix);
    num=norm(P(:)-R(:),2); den=norm(R(:),2); rF=num/den;
    rSpec=norm(P-R,2)/norm(R,2);
    % D2: apertures
    aps=[];
    for ap=apertures
      half=round((ap-1)/2); x0=cx-half; x1=cx+half;
      if x0<1 || x1>65, aps=[aps struct('ap',ap,'status','NOT_AVAILABLE')]; continue; end
      ia=(x0):(x1);
      CpA=rp.contrast(ia,ia); CfA=rf.contrast(ia,ia);
      Sp=65^2*sum(max(CpA(:),0)); Sm=65^2*sum(min(CpA(:),0));
      Sf_p=65^2*sum(CpA(:)); Sf_f=65^2*sum(CfA(:));
      diff_ap=norm(CpA(:)-CfA(:),2)/max(norm(CfA(:)),realmin);
      aps=[aps struct('ap',ap,'S_plus_prod',Sp,'S_minus_prod',Sm,'S_prod',Sf_p,'S_fine',Sf_f,'relL2',diff_ap)]; %#ok<AGROW>
    end
    res{end+1}=struct('D',D,'zf',zf,'fwd_frobenius',rF,'fwd_spectral',rSpec, ...
      'gate2pct_frobenius',rF<0.02,'closure_prod',close_p,'closure_fine',close_f, ...
      'C_center_prod',rp.contrast(33,33),'C_center_fine',rf.contrast(33,33), ...
      'S_area_prod',65^2*sum(rp.contrast(ix,ix),'all'),'S_area_fine',65^2*sum(rf.contrast(ix,ix),'all'), ...
      'Cs_prod_mean',mean(Cs_p(:)),'Cint_prod_mean',mean(Cint_p(:)), ...
      'Cs_fine_mean',mean(Cs_f(:)),'Cint_fine_mean',mean(Cint_f(:)), ...
      'apertures',aps); %#ok<AGROW>
    fprintf('[067:cd] D=%g zf=%d rF=%.4f rSpec=%.4f close=%.1e\n',D,zf,rF,rSpec,max(close_p,close_f));
  end
end
writetable(struct2table([res{:}]),fullfile(outRoot,'v067_27condition_full.csv'));
fprintf('[067:cd] all 27 conditions done\n');

% ==== D3: zero-crossing refinement ====
% D60 C_center between zf=500(-0.0133) and 525(+0.0083)
refine_zf=500:2.5:525;
refine={};
for zf=refine_zf
  sp=load(fullfile(od65,'D60_s_576.mat'),'s'); sp=sp.s;
  sf=load(fullfile(od65,'D60_s_1444.mat'),'s'); sf=sf.s;
  cp=sp.cfg; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
  rp=render_system(sp,cp);
  cf=sf.cfg; cf.focus_nm=[0,0,zf]; cf.sampling.subpixels=5;
  rf=render_system(sf,cf);
  refine{end+1}=struct('D',60,'zf',zf,'C_center_prod',rp.contrast(33,33), ...
    'C_center_fine',rf.contrast(33,33),'scope','POST_HOC_LINEAR_INTERPOLATION_NOT_A_SIMULATED_ROOT'); %#ok<AGROW>
  fprintf('[067:d3] D60 zf=%.1f C_center_prod=%.6f\n',zf,rp.contrast(33,33));
end
% D100 S_area between zf=425(S_p=61) and zf=450(S_p=-1746)
refine_zf2=427.5:2.5:447.5;
for zf=refine_zf2
  sp=load(fullfile(od65,'D100_s_576.mat'),'s'); sp=sp.s;
  sf=load(fullfile(od65,'D100_s_1444.mat'),'s'); sf=sf.s;
  cp=sp.cfg; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
  rp=render_system(sp,cp);
  cf=sf.cfg; cf.focus_nm=[0,0,zf]; cf.sampling.subpixels=5;
  rf=render_system(sf,cf);
  sA_p=65^2*sum(rp.contrast(ix,ix),'all'); sA_f=65^2*sum(rf.contrast(ix,ix),'all');
  refine{end+1}=struct('D',100,'zf',zf,'S_area_prod',sA_p,'S_area_fine',sA_f, ...
    'scope','POST_HOC_LINEAR_INTERPOLATION_NOT_A_SIMULATED_ROOT'); %#ok<AGROW>
  fprintf('[067:d3] D100 zf=%.1f S_area_prod=%.2f S_area_fine=%.2f\n',zf,sA_p,sA_f);
end
writetable(struct2table([refine{:}]),fullfile(outRoot,'d3_zero_crossing_refinement.csv'));
fprintf('[067:d3] zero-crossing refinement done: %d points\n',numel(refine));
fprintf('[067] ALL DONE\n');
end




