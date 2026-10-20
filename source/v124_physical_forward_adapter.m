function ledger = v124_physical_forward_adapter(repoRoot, configFile, casesFile, outDir)
%V124_PHYSICAL_FORWARD_ADAPTER NANOBEM stratified BEM + vector iSCAT imaging batch driver.
%   ledger = v124_run_cases(repoRoot, configFile, casesFile, outDir)
%   Reads the V124 unified config and a cases JSON, then for each case:
%     - solves the stratified BEM once per physics identity (cached on disk;
%       a cache hit is a legitimate exact-configuration reuse and is logged);
%     - renders each requested camera variant (focus/subpixel/shifted grid).
%   Every actual solve attempt (success OR failure) and every actual render
%   is appended to outDir/logs/v124_matlab_ledger.csv. No empirical contrast
%   formula is used anywhere; C comes only from |Eref+Esca|^2 coherence.
if isfolder(repoRoot) && ~strcmp(repoRoot,'.'), repoRootFull = repoRoot; else, repoRootFull = fullfile(pwd,repoRoot); end
repoRootFull = cd(repoRootFull); % canonicalize (collapses '.')
if ~isfolder(repoRootFull), error('iscat:BadRoot', 'iscat:BadRoot'); end
projectRoot = fileparts(repoRootFull); % iscat_v0_4 project root
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,guard] = prepare_nanobem(projectRoot,''); %#ok<NASGU>
if nargin<4 || isempty(outDir), outDir = fullfile(repoRoot,'results','v124'); end
if ~isfolder(outDir), mkdir(outDir); end
cacheDir = fullfile(outDir,'bem_cache'); if ~isfolder(cacheDir), mkdir(cacheDir); end
rendDir  = fullfile(outDir,'renders');   if ~isfolder(rendDir),  mkdir(rendDir);  end
logDir   = fullfile(outDir,'logs');      if ~isfolder(logDir),   mkdir(logDir);   end
cfgText = fileread(configFile); cfg = jsondecode(cfgText);
casesText = fileread(casesFile); cj = jsondecode(casesText);
cases = cj.cases;
if isstruct(cases)
    cases = arrayfun(@(k) cases(k), 1:numel(cases), 'UniformOutput', false);
elseif ~iscell(cases)
    cases = {cases};
end
% ---- frozen V124 forward configuration -------------------------------------
c = iscat_config('camera');
c.lambda_nm = cfg.user_confirmed.wavelength_nm.value;
nwater = cfg.assumed.n_water.value;
nglass = cfg.assumed.n_glass.value;
c.layers.n = [nglass, nwater];
c.layers.interfaces_nm = 0;
c.layers.particle_layer = 2;
c.objective.NA = cfg.assumed.collection_NA.value;
c.objective.nominal_magnification = cfg.user_confirmed.objective_magnification.value;
c.tube.actual_focal_mm = 200; c.tube.relay_magnification = cfg.assumed.relay_magnification.value;
c.sampling.pixel_um = cfg.user_confirmed.camera_pixel_um.value(1);
c.sampling.Nx = cfg.assumed.roi_pixels.value(1);
c.sampling.Ny = cfg.assumed.roi_pixels.value(2);
c.sampling.subpixels = cfg.assumed.subpixel_quadrature.value(1);
c.numerics.ntheta = cfg.forward.ntheta;
c.numerics.nphi = cfg.forward.nphi;
c.numerics.bessel_table_points = cfg.forward.bessel_table_points;
c.illumination.angle_deg = 0;
c.image_side_n = 1;
effM = c.objective.nominal_magnification * c.tube.actual_focal_mm/c.objective.design_tube_focal_mm * c.tube.relay_magnification;
pxNm = 1000*c.sampling.pixel_um/effM;
assert(abs(pxNm-cfg.assumed.physical_pixel_nm.value)<1e-9, 'object pixel mismatch');
fp = sprintf('lam%.1f_nw%.6f_ng%.4f_NA%.3f_px%.1f_N%d_q%d', c.lambda_nm,nwater,nglass, ...
    c.objective.NA,c.sampling.pixel_um,c.sampling.Nx,c.sampling.subpixels);
ledgerFile = fullfile(logDir,'v124_matlab_ledger.csv');
if ~isfile(ledgerFile)
    fid=fopen(ledgerFile,'w');
    fprintf(fid,'timestamp_utc,case_tag,case_key,action,ok,seconds,d_nm,h_nm,np_re,np_im,mesh,error_msg,file\n');
    fclose(fid);
end
ledger = struct('rows',{{}},'n_solves',0,'n_solve_fails',0,'n_cache_hits',0,'n_renders',0,'n_render_fails',0);
for ic = 1:numel(cases)
    cs = cases{ic};
    D  = cs.D_nm; h = cs.h_nm;
    np = complex(cs.np_re, cs.np_im);
    mesh = cs.mesh;
    tag = cs.tag;
    gap = h - D/2;
    assert(gap >= cfg.assumed.min_gap_nm.value - 1e-9, 'gap below min for %s', tag);
    key = sprintf('%s__%s__D%g_h%g_np%.6f%+.6f_mesh%d', fp, tag, D, h, real(np), imag(np), mesh);
    sfile = fullfile(cacheDir,[key '_solve.mat']);
    % ---- solve (or exact-configuration cache reuse) ----
    if isfile(sfile)
        t0=tic; tmp=load(sfile,'s'); s=tmp.s; clear tmp; dt=toc(t0);
        v124_ledger_row(ledgerFile,'cache_hit',tag,key,D,h,np,mesh,true,dt,'',sfile);
        ledger.n_cache_hits = ledger.n_cache_hits+1;
        fprintf('[v124] CACHE HIT %s (%.2fs load)\n',key,dt);
    else
        try
            cs_cfg = c;
            cs_cfg.particle.diameter_nm = D;
            cs_cfg.particle.gap_nm = gap;
            cs_cfg.particle.xy_nm = [0,0];
            cs_cfg.particle.material = 'constant_index';
            cs_cfg.particle.n_complex = np;
            cs_cfg.numerics.mesh_request = mesh;
            t0=tic; s = build_system(cs_cfg); dt=toc(t0);
            save(sfile,'s','-v7.3');
            v124_ledger_row(ledgerFile,'solve',tag,key,D,h,np,mesh,true,dt,'',sfile);
            ledger.n_solves = ledger.n_solves+1;
            fprintf('[v124] SOLVE OK %s %.1fs\n',key,dt);
        catch err
            dt=toc(t0);
            v124_ledger_row(ledgerFile,'solve',tag,key,D,h,np,mesh,false,dt,err.message,'');
            ledger.n_solve_fails = ledger.n_solve_fails+1;
            fprintf('[v124] SOLVE FAIL %s: %s\n',key,err.message);
            continue;
        end
    end
    % ---- renders ----
    variants = cs.renders;
    if ~iscell(variants), variants = {variants}; end
    for iv = 1:numel(variants)
        vr = variants{iv};
        vname = 'default';
        if isfield(vr,'variant'), vname = vr.variant; end
        rc = c; % sampling/focus per variant, solve untouched
        zf = 450.0; if isfield(vr,'focus_z_nm'), zf = vr.focus_z_nm; end
        rc.focus_nm = [0,0,zf];
        if isfield(vr,'subpixels'), rc.sampling.subpixels = vr.subpixels; end
        dx=0; dy=0;
        if isfield(vr,'shift_xy_nm'), dx=vr.shift_xy_nm(1); dy=vr.shift_xy_nm(2); end
        rfile = fullfile(rendDir, sprintf('%s__%s.mat', key, vname));
        if isfile(rfile)
            v124_ledger_row(ledgerFile,'render_cache_hit',tag,key,D,h,np,mesh,true,0,'',rfile);
            fprintf('[v124] RENDER CACHE HIT %s\n',rfile);
            continue;
        end
        try
            t0=tic;
            if abs(dx)>0 || abs(dy)>0
                % sample the SAME solved field on a translated camera grid
                effM2 = rc.objective.nominal_magnification * rc.tube.actual_focal_mm/rc.objective.design_tube_focal_mm * rc.tube.relay_magnification;
                px2 = 1000*rc.sampling.pixel_um/effM2; q=rc.sampling.subpixels;
                x0 = ((0:rc.sampling.Nx*q-1)-(rc.sampling.Nx*q-1)/2)*px2/q;
                y0 = ((0:rc.sampling.Ny*q-1)-(rc.sampling.Ny*q-1)/2)*px2/q;
                es0 = efield(s.lens,s.far,x0-dx,y0-dy,'focus',rc.focus_nm,'ntab',rc.numerics.bessel_table_points);
                er0 = efield(s.lens,s.reference,x0-dx,y0-dy,'focus',rc.focus_nm);
                es = flip(es0,1); er = flip(er0,1);
                xc = ((0:rc.sampling.Nx-1)-(rc.sampling.Nx-1)/2)*px2;
                yc = ((0:rc.sampling.Ny-1)-(rc.sampling.Ny-1)/2)*px2;
                I0 = pixel_mean(sum(abs(er).^2,3),q);
                Is = pixel_mean(sum(abs(es).^2,3),q);
                Ix = pixel_mean(2*real(sum(conj(er).*es,3)),q);
                It = pixel_mean(sum(abs(er+es).^2,3),q);
                err = norm(It(:)-I0(:)-Is(:)-Ix(:))/max(norm(It(:)),realmin);
                assert(err<1e-10,'Coherent intensity identity failed (shifted).');
                r = struct('x_nm',xc,'y_nm',yc,'fine_x_nm',x0,'fine_y_nm',y0, ...
                    'Esca',es,'Eref',er,'Iref',I0,'Isca',Is,'Icross',Ix,'Itotal',It, ...
                    'contrast',(It-I0)./I0,'subpixels',q,'effective_magnification',effM2, ...
                    'object_pixel_nm',px2,'intensity_identity_relative_error',err, ...
                    'grid_shift_xy_nm',[dx,dy],'focus_nm',rc.focus_nm, ...
                    'mesh_vertices',s.mesh_vertices,'mesh_faces',s.mesh_faces, ...
                    'solve_seconds',s.solve_seconds,'particle_n',s.particle_n, ...
                    'center_nm',s.center_nm);
            else
                r = render_system(s,rc);
            end
            dt=toc(t0);
            save(rfile,'r','key','vname','-v7.3');
            v124_ledger_row(ledgerFile,'render',tag,key,D,h,np,mesh,true,dt,'',rfile);
            ledger.n_renders = ledger.n_renders+1;
            fprintf('[v124] RENDER OK %s/%s %.1fs peakC=%.6g\n',key,vname,dt,max(abs(r.contrast(:))));
        catch err
            dt=toc(t0);
            v124_ledger_row(ledgerFile,'render',tag,key,D,h,np,mesh,false,dt,err.message,'');
            ledger.n_render_fails = ledger.n_render_fails+1;
            fprintf('[v124] RENDER FAIL %s/%s: %s\n',key,vname,err.message);
        end
    end
end
fprintf('[v124] batch done: solves=%d fails=%d cache_hits=%d renders=%d render_fails=%d\n', ...
    ledger.n_solves,ledger.n_solve_fails,ledger.n_cache_hits,ledger.n_renders,ledger.n_render_fails);
end

function v124_ledger_row(csv,action,tag,key,D,h,np,mesh,ok,secs,msg,fpath)
fid=fopen(csv,'a');
fprintf(fid,'%s,%s,%s,%s,%d,%.4f,%g,%g,%.10g,%.10g,%d,%s,%s\n', ...
    char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd HH:mm:ss')), ...
    tag,key,action,ok,secs,D,h,real(np),imag(np),mesh,msg,fpath);
fclose(fid);
end
