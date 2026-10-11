function report=run_v064_m2r_fe3o4(outdir)
% v064 M2R: corrected 60nm Fe3O4 absorbing BEM vs Mie (four gates <0.02).
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'),fullfile(projectRoot,'handoff','matlab'));
[~,compatibilityGuard]=prepare_nanobem(projectRoot,''); %#ok<NASGU>
if nargin<1
    outdir=fullfile(projectRoot,'v064_return','m2r_fe3o4_60nm');
    if ~isfolder(outdir), mkdir(outdir); end
end
diary(fullfile(outdir,'matlab_run.log')); cleanup=onCleanup(@() diary('off'));
fprintf('[064:m2r] start corrected 60nm Fe3O4 (n=2.349+0.083i) in water 1.33 @520nm\n');
meshes=[1444]; rules=[3]; lam=[520]; diameter=60;
mw=Material(1.33^2,1);
nr=2.349; kap=0.083;
nParticle=complex(nr,kap);
epsParticle=nParticle^2;
% material readback guard
mp=Material(epsParticle,1);
n_read=mp.n(2*pi/520);
assert(abs(real(n_read)-nr)<=1e-9&&abs(imag(n_read)-kap)<=1e-9,'MATERIAL_READBACK_LOST_COMPLEX');
fprintf('[064:m2r] material readback n=%.17g%+.17gi OK\n',real(n_read),imag(n_read));
ms=miesolver(mp,mw,diameter);
[dirRef,wRef]=iscat04.sphere_rule(48,97);
rows=[]; k=0;
for im=1:numel(meshes)
    p=trisphere(meshes(im),diameter);
    tau=BoundaryEdge([mw,mp],p,[2,1]);
    qAsm=quadboundary.rules('quad3',triquad(3));
    qNear=quadboundary.rules('quad3',triquad(11));
    bem=galerkin.bemsolver(tau,'rules',qAsm,'rules1',qNear, ...
        'nduffy',3,'relcutoff',2,'order',3,'waitbar',0);
    exc=galerkin.planewave([1,0,0],[0,0,1],'rules',quadboundary.rules('quad3',triquad(3)));
    for j=1:numel(lam)
        k=k+1; k0=2*pi/lam(j);
        sol=bem\exc(tau,k0);
        eB=farfields(sol,dirRef); eB=squeeze(eB); if ~ismatrix(eB), eB=reshape(eB,[],3); end
        eM=farscattering(ms,k0,[1,0,0],dirRef); eM=eM.e;
        fm=iscat04.field_metrics(eB,eM,wRef);
        bs=scattering(exc,sol); ba=absorption(exc,sol); bx=extinction(exc,sol);
        as=scattering(ms,k0); aa=absorption(ms,k0); ax=extinction(ms,k0);
        err_sca=abs(bs-as)/max(abs(as),realmin); err_abs=abs(ba-aa)/max(abs(aa),realmin);
        err_ext=abs(bx-ax)/max(abs(ax),realmin);
        passed=fm.raw_complex_relative_L2<0.02 && err_sca<0.02 && err_abs<0.02 && err_ext<0.02;
        rows=[rows; struct('mesh_request',meshes(im),'lambda_nm',lam(j), ...
          'material','Fe3O4_complex_2.349+0.083i','raw_complex_relative_L2', ...
          fm.raw_complex_relative_L2,'BEM_sca',bs,'Mie_sca',as,'sca_error',err_sca, ...
          'BEM_abs',ba,'Mie_abs',aa,'abs_error',err_abs, ...
          'BEM_ext',bx,'Mie_ext',ax,'ext_error',err_ext,'passed',passed)]; %#ok<AGROW>
        fprintf('[064:m2r] rawL2=%.6g scaErr=%.6g absErr=%.6g extErr=%.6g passed=%d\n', ...
          fm.raw_complex_relative_L2,err_sca,err_abs,err_ext,passed);
    end
end
T=struct2table(rows);
writetable(T,fullfile(outdir,'m2r_fe3o4_results.csv'));
save(fullfile(outdir,'m2r_fe3o4_results.mat'),'T','-v7.3');
report=struct('passed',all([rows.passed]),'tolerance',0.02,'table',T);
fid=fopen(fullfile(outdir,'m2r_report.json'),'w'); fwrite(fid,jsonencode(report)); fclose(fid);
fprintf('[064:m2r] passed=%d\n',report.passed);
end
