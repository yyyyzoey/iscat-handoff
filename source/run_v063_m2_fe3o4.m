function report=run_v063_m2_fe3o4(outdir)
% v063 M2: 60nm Fe3O4 homogeneous-medium BEM vs Mie (1444/rule3, 520nm, water).
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'),fullfile(projectRoot,'handoff','matlab'));
[~,compatibilityGuard]=prepare_nanobem(projectRoot,''); %#ok<NASGU>
if nargin<1
    outdir=fullfile(projectRoot,'v063_return','m2_fe3o4_60nm');
    if ~isfolder(outdir), mkdir(outdir); end
end
diary(fullfile(outdir,'matlab_run.log')); cleanup=onCleanup(@() diary('off'));
fprintf('[063:m2] start 60nm Fe3O4 in water 1.33 @520nm\n');
meshes=[1444]; rules=[3]; lam=[520]; diameter=60;
mw=Material(1.33^2,1);
nC=2.349+0.0831; % Fe3O4 Querry 1987 linear interp @520nm (refractiveindex.info, CC0)
mp=Material(nC^2,1);
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
        k=k+1;
        k0=2*pi/lam(j);
        sol=bem\exc(tau,k0);
        eB=farfields(sol,dirRef); eB=squeeze(eB); if ~ismatrix(eB), eB=reshape(eB,[],3); end
        eM=farscattering(ms,k0,[1,0,0],dirRef); eM=eM.e;
        fm=iscat04.field_metrics(eB,eM,wRef);
        bs=scattering(exc,sol); ba=absorption(exc,sol); bx=extinction(exc,sol);
        as=scattering(ms,k0); aa=absorption(ms,k0); ax=extinction(ms,k0);
        passed=fm.raw_complex_relative_L2<0.02 && abs(bs-as)/max(abs(as),realmin)<0.02 ...
          && abs(ba-aa)/max(abs(aa),realmin)<0.02 && abs(bx-ax)/max(abs(ax),realmin)<0.02;
        rows=[rows; struct('mesh_request',meshes(im),'rule_id',rules(im), ...
          'lambda_nm',lam(j),'material','Fe3O4_Querry1987_interp520','n_complex',nC, ...
          'BEM_sca',bs,'Mie_sca',as,'sca_error',abs(bs-as)/max(abs(as),realmin), ...
          'BEM_abs',ba,'Mie_abs',aa,'abs_error',abs(ba-aa)/max(abs(aa),realmin), ...
          'BEM_ext',bx,'Mie_ext',ax,'ext_error',abs(bx-ax)/max(abs(ax),realmin), ...
          'raw_complex_relative_L2',fm.raw_complex_relative_L2, ...
          'norm_ratio',fm.norm_ratio,'passed',passed)]; %#ok<AGROW>
        fprintf('[063:m2] mesh=%g rawL2=%.6g scaErr=%.6g absErr=%.6g extErr=%.6g passed=%d\n', ...
          meshes(im),fm.raw_complex_relative_L2,abs(bs-as)/max(abs(as),realmin), ...
          abs(ba-aa)/max(abs(aa),realmin),abs(bx-ax)/max(abs(ax),realmin),passed);
    end
end
T=struct2table(rows);
writetable(T,fullfile(outdir,'m2_fe3o4_mie_results.csv'));
save(fullfile(outdir,'m2_fe3o4_mie_results.mat'),'T','-v7.3');
report=struct('passed',all([rows.passed]),'tolerance',0.02,'table',T);
fid=fopen(fullfile(outdir,'m2_report.json'),'w'); fwrite(fid,jsonencode(report)); fclose(fid);
fprintf('[063:m2] passed=%d\n',report.passed);
end
