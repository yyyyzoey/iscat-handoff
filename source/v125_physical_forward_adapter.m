function ledger = v125_physical_forward_adapter(repoRoot, configFile, casesFile, outDir)
%V125_PHYSICAL_FORWARD_ADAPTER V125 batch driver over the V124 physics chain.
% Fixes S0.4 root resolution (no implicit cd), S0.7 two-level cache identity
% (solve key: material/interface/geometry/D/h/incidence/discrete/solver id;
%  render key: + NA/focus/pixel/polarization/ROI/q/offset/imaging id).
% Render variant 'particle_shift' images a translated particle with the
% reference field evaluated on the FIXED camera grid (S1-B correct semantics).
% Adapter source file itself participates in the identity fingerprint.
adapterFile = [mfilename('fullpath') '.m'];
repoFull    = fileparts(fileparts(adapterFile));            % repo root, no cd
projectRoot = fileparts(repoFull);                          % iscat_v0_4
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,guard] = prepare_nanobem(projectRoot,''); %#ok<NASGU>
if nargin<4 || isempty(outDir), outDir = fullfile(repoFull,'results','v125'); end
if ~isfolder(outDir), mkdir(outDir); end
cacheDir = fullfile(outDir,'bem_cache'); if ~isfolder(cacheDir), mkdir(cacheDir); end
rendDir  = fullfile(outDir,'renders');   if ~isfolder(rendDir),  mkdir(rendDir);  end
logDir   = fullfile(outDir,'logs');      if ~isfolder(logDir),   mkdir(logDir);   end
cfg  = jsondecode(fileread(configFile));
cj   = jsondecode(fileread(casesFile));
cases = cj.cases;
if isstruct(cases)
    cases = arrayfun(@(k) cases(k), 1:numel(cases), 'UniformOutput', false);
elseif ~iscell(cases)
    cases = {cases};
end
% ---- frozen V125 forward configuration (mirrors V124 physics identity) ----
c = iscat_config('camera');
c.lambda_nm = 520;
nwater = 1.3353; nglass = 1.5;
c.layers.n = [nglass, nwater];
c.layers.interfaces_nm = 0;
c.layers.particle_layer = 2;
c.objective.NA = 0.8;
c.objective.nominal_magnification = 50;
c.tube.actual_focal_mm = 200; c.tube.relay_magnification = 1;
c.sampling.pixel_um = 14;
c.sampling.Nx = 17; c.sampling.Ny = 17;
c.sampling.subpixels = 5;
c.numerics.ntheta = 50; c.numerics.nphi = 51;
c.numerics.bessel_table_points = 2001;
c.illumination.angle_deg = 0;
c.image_side_n = 1;
effM = 50; pxNm = 1000*c.sampling.pixel_um/effM;
assert(abs(pxNm-280)<1e-9, 'object pixel mismatch');
% two-level identity fingerprints (S0.7). solver_id covers the physics chain:
% pinned NANOBEM commit + this adapter file bytes + frozen parameter set.
adapterHash = CalcSHA1(adapterFile);
solver_id = ['v125.1_nanobem_ce49f77f_adapter_' adapterHash];
imaging_id = ['v125img.1_NA0p8_px280_q5_roi17_focusvar_' adapterHash];
importMapFile = fullfile(logDir,'v124_cache_map.json');
importMap = struct();
if isfile(importMapFile)
    importMap = jsondecode(fileread(importMapFile));
end
ledgerFile = fullfile(logDir,'v125_matlab_ledger.csv');
if ~isfile(ledgerFile)
    fid=fopen(ledgerFile,'w');
    fprintf(fid,'timestamp_utc,case_tag,case_key,action,ok,seconds,d_nm,h_nm,np_re,np_im,mesh,error_msg,file\n');
    fclose(fid);
end
ledger = struct('n_solves',0,'n_solve_fails',0,'n_cache_hits',0,'n_renders',0,'n_render_fails',0,'n_render_cache_hits',0);
for ic = 1:numel(cases)
    cs = cases{ic};
    D = cs.D_nm; h = cs.h_nm;
    np = complex(cs.np_re, cs.np_im);
    mesh = cs.mesh; tag = cs.tag;
    gap = h - D/2;
    assert(gap >= 100 - 1e-9, 'gap below 100nm min for %s', tag);
    skey = sprintf('%s__%s__D%g_h%g_np%.8f%+.8f_mesh%d', solver_id, tag, D, h, real(np), imag(np), mesh);
    sfile = fullfile(cacheDir, ['sol_' CalcStrSHA1(skey) '.mat']);  % short: Windows MAX_PATH safe
    v125_map_row(logDir, 'solve', skey, sfile);
    imported = false;
    if ~isfile(sfile)
        % S0.7 imported-cache path: identity-verified V124 solve reused without
        % a new solve; s.cfg re-verified here before acceptance.
        ikey = sprintf('D%g_h%g_np%.8f%+.8f_mesh%d', D, h, real(np), imag(np), mesh);
        if isfield(importMap, ikey)
            src = importMap.(ikey);
            tmp = load(src, 's');
            sc = tmp.s.cfg; clear tmp;
            h_chk = sc.particle.gap_nm + sc.particle.diameter_nm/2;
            if abs(sc.particle.diameter_nm-D)<1e-12 && abs(h_chk-h)<1e-9 ...
                    && abs(real(sc.particle.n_complex)-real(np))<1e-12 ...
                    && sc.numerics.mesh_request==mesh && sc.objective.NA==c.objective.NA ...
                    && sc.lambda_nm==c.lambda_nm
                meta = struct('D_nm',D,'h_nm',h,'np_re',real(np),'np_im',imag(np),'mesh',mesh, ...
                    'gap_nm',h-D/2,'nwater',nwater,'nglass',nglass,'NA',c.objective.NA, ...
                    'lambda_nm',c.lambda_nm,'solver_id',[solver_id '_imported_v124_verified']);
                v125_save_mat(sfile, s, meta);
                v125_ledger_row(ledgerFile,'cache_hit_imported',tag,skey,D,h,np,mesh,true,0,src,sfile);
                ledger.n_cache_hits = ledger.n_cache_hits+1;
                imported = true;
                fprintf('[v125] CACHE IMPORTED %s <- %s\n',skey,src);
            else
                fprintf('[v125] IMPORT REJECTED identity mismatch for %s\n',ikey);
            end
        end
    end
    if ~imported
        if isfile(sfile)
            t0=tic; tmp=load(sfile,'s','meta'); s=tmp.s; clear tmp; dt=toc(t0);
            assert(abs(meta.D_nm-D)<1e-12 && abs(meta.h_nm-h)<1e-12 && abs(meta.np_re-real(np))<1e-12, 'cache identity mismatch %s', skey);
            v125_ledger_row(ledgerFile,'cache_hit',tag,skey,D,h,np,mesh,true,dt,'',sfile);
            ledger.n_cache_hits = ledger.n_cache_hits+1;
            fprintf('[v125] CACHE HIT %s (%.2fs)\n',skey,dt);
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
            meta = struct('D_nm',D,'h_nm',h,'np_re',real(np),'np_im',imag(np),'mesh',mesh, ...
                'gap_nm',gap,'nwater',nwater,'nglass',nglass,'NA',c.objective.NA, ...
                'lambda_nm',c.lambda_nm,'solver_id',solver_id);
            v125_save_mat(sfile, s, meta);
            v125_ledger_row(ledgerFile,'solve',tag,skey,D,h,np,mesh,true,dt,'',sfile);
            ledger.n_solves = ledger.n_solves+1;
            fprintf('[v125] SOLVE OK %s %.1fs\n',skey,dt);
        catch err
            dt=toc(t0);
            v125_ledger_row(ledgerFile,'solve',tag,skey,D,h,np,mesh,false,dt,err.message,'');
            ledger.n_solve_fails = ledger.n_solve_fails+1;
            fprintf('[v125] SOLVE FAIL %s: %s\n',skey,err.message);
            continue;
        end
        end
    end
    variants = cs.renders;
    if isempty(variants)
        variants = {};
    elseif isstruct(variants)
        variants = arrayfun(@(k) variants(k), 1:numel(variants), 'UniformOutput', false);
    elseif ~iscell(variants)
        variants = {variants};
    end
    for iv = 1:numel(variants)
        vr = variants{iv};
        vname = 'default'; if isfield(vr,'variant'), vname = vr.variant; end
        rc = c;
        if isfield(vr,'focus_z_nm'), rc.focus_nm = [0,0,vr.focus_z_nm]; else, rc.focus_nm = [0,0,450]; end
        if isfield(vr,'subpixels'), rc.sampling.subpixels = vr.subpixels; end
        mode = 'default';
        if isfield(vr,'mode'), mode = vr.mode; end
        dx=0; dy=0;
        if isfield(vr,'shift_xy_nm'), dx=vr.shift_xy_nm(1); dy=vr.shift_xy_nm(2); end
        rkey = sprintf('%s__%s__%s_dx%g_dy%g', imaging_id, skey, vname, dx, dy);
        rfile = fullfile(rendDir, ['ren_' CalcStrSHA1(rkey) '.mat']);  % short: MAX_PATH safe
        v125_map_row(logDir, 'render', rkey, rfile);
        if isfile(rfile)
            v125_ledger_row(ledgerFile,'render_cache_hit',tag,rkey,D,h,np,mesh,true,0,'',rfile);
            ledger.n_render_cache_hits = ledger.n_render_cache_hits+1;
            fprintf('[v125] RENDER CACHE HIT %s\n',rfile);
            continue;
        end
        try
            t0=tic;
            r = v125_render_variant(s, rc, mode, dx, dy);
            dt=toc(t0);
            rmeta = struct('mode',mode,'dx',dx,'dy',dy,'variant',vname, ...
                'focus_z',rc.focus_nm(3),'q',rc.sampling.subpixels,'imaging_id',imaging_id);
            v125_save_mat_r(rfile, r, rmeta);
            v125_ledger_row(ledgerFile,'render',tag,rkey,D,h,np,mesh,true,dt,'',rfile);
            ledger.n_renders = ledger.n_renders+1;
            fprintf('[v125] RENDER OK %s/%s %.1fs peakC=%.6g\n',skey,vname,dt,max(abs(r.contrast(:))));
        catch err
            dt=toc(t0);
            v125_ledger_row(ledgerFile,'render',tag,rkey,D,h,np,mesh,false,dt,err.message,'');
            ledger.n_render_fails = ledger.n_render_fails+1;
            fprintf('[v125] RENDER FAIL %s/%s: %s\n',skey,vname,err.message);
        end
    end
end
fprintf('[v125] batch done: solves=%d fails=%d cache_hits=%d renders=%d render_fails=%d render_cache_hits=%d\n', ...
    ledger.n_solves,ledger.n_solve_fails,ledger.n_cache_hits,ledger.n_renders,ledger.n_render_fails,ledger.n_render_cache_hits);
end

function r = v125_render_variant(s, c, mode, dx, dy)
% Three imaging modes with explicit semantics:
%  default        : centered particle, standard render_system
%  particle_shift : Es sampled at (x-dx, y-dy); Eref FIXED on camera grid
%  camera_shift   : both Es and Eref sampled at (x-dx, y-dy) (V124-style grid
%                   shift; kept for the S1-B covariance comparison only)
effM = c.objective.nominal_magnification;
px = 1000*c.sampling.pixel_um/effM; q = c.sampling.subpixels;
Nx = c.sampling.Nx; Ny = c.sampling.Ny;
x0 = ((0:Nx*q-1)-(Nx*q-1)/2)*px/q;
y0 = ((0:Ny*q-1)-(Ny*q-1)/2)*px/q;
xc = ((0:Nx-1)-(Nx-1)/2)*px;
yc = ((0:Ny-1)-(Ny-1)/2)*px;
switch mode
    case 'default'
        r = render_system(s, c);
    case 'wide'
        % 25x25 camera grid: same physics/imaging, wider fine-grid support for
        % lateral-shift interpolation (central 17x17 must equal default render)
        cw = c; cw.sampling.Nx = 25; cw.sampling.Ny = 25;
        r = render_system(s, cw);
    case 'particle_shift'
        es0 = efield(s.lens, s.far, x0-dx, y0-dy, 'focus', c.focus_nm, 'ntab', c.numerics.bessel_table_points);
        er0 = efield(s.lens, s.reference, x0, y0, 'focus', c.focus_nm);
        es = flip(es0,1); er = flip(er0,1);
        r = v125_assemble_render(es, er, s, x0, y0, xc, yc, px, q, effM, mode, dx, dy, c);
    case 'camera_shift'
        es0 = efield(s.lens, s.far, x0-dx, y0-dy, 'focus', c.focus_nm, 'ntab', c.numerics.bessel_table_points);
        er0 = efield(s.lens, s.reference, x0-dx, y0-dy, 'focus', c.focus_nm);
        es = flip(es0,1); er = flip(er0,1);
        r = v125_assemble_render(es, er, s, x0, y0, xc, yc, px, q, effM, mode, dx, dy, c);
    otherwise
        error('Unknown render mode %s', mode);
end
end

function r = v125_assemble_render(es, er, s, x0, y0, xc, yc, px, q, effM, mode, dx, dy, c)
assert(size(es,3)==3 && size(er,3)==3,'Expected 3-vector fields.');
assert(all(isfinite(es(:))) && all(isfinite(er(:))),'Nonfinite computed field.');
I0 = pixel_mean(sum(abs(er).^2,3),q);
Is = pixel_mean(sum(abs(es).^2,3),q);
Ix = pixel_mean(2*real(sum(conj(er).*es,3)),q);
It = pixel_mean(sum(abs(er+es).^2,3),q);
err = norm(It(:)-I0(:)-Is(:)-Ix(:))/max(norm(It(:)),realmin);
assert(err<1e-10,'Coherent intensity identity failed.');
r = struct('x_nm',xc,'y_nm',yc,'fine_x_nm',x0,'fine_y_nm',y0, ...
    'Esca',es,'Eref',er,'Iref',I0,'Isca',Is,'Icross',Ix,'Itotal',It, ...
    'contrast',(It-I0)./I0,'subpixels',q,'effective_magnification',effM, ...
    'object_pixel_nm',px,'intensity_identity_relative_error',err, ...
    'render_mode',mode,'shift_xy_nm',[dx,dy],'focus_nm',c.focus_nm, ...
    'particle_n',s.particle_n,'center_nm',s.center_nm);
end

function v125_save_mat_r(target, r, rmeta)
tfile = [target(1:end-4) '_tmp.mat'];
try
    save(tfile,'r','rmeta','-v7.3');
catch
    delete(tfile);
    save(tfile,'r','rmeta','-v7.3');
end
movefile(tfile, target, 'f');
end

function v125_save_mat(target, s, meta)
% Save via temp file + move to avoid HDF5 create/open transient lock failures.
tfile = [target(1:end-4) '_tmp.mat'];
try
    save(tfile,'s','meta','-v7.3');
catch
    delete(tfile);
    save(tfile,'s','meta','-v7.3');  % single retry
end
movefile(tfile, target, 'f');
end

function v125_ledger_row(csv,action,tag,key,D,h,np,mesh,ok,secs,msg,fpath)
fid=fopen(csv,'a');
fprintf(fid,'%s,%s,%s,%s,%d,%.4f,%g,%g,%.10g,%.10g,%d,%s,%s\n', ...
    char(datetime('now','TimeZone','UTC','Format','yyyy-MM-dd HH:mm:ss')), ...
    tag,key,action,ok,secs,D,h,real(np),imag(np),mesh,msg,fpath);
fclose(fid);
end

function hex = CalcStrSHA1(str)
sha=java.security.MessageDigest.getInstance('SHA-1');
jbytes=int8(str);
sha.update(jbytes);
out=typecast(sha.digest(),'uint8');
hex=lower(reshape(dec2hex(out,2).',1,[]));
end

function v125_map_row(logDir, keytype, fullkey, fpath)
% audit map: full human-readable key -> short hashed filename
mapFile = fullfile(logDir,'cache_key_map.csv');
if ~isfile(mapFile)
    fid=fopen(mapFile,'w'); fprintf(fid,'keytype,full_key,file\n'); fclose(fid);
end
fid=fopen(mapFile,'a');
fprintf(fid,'%s,%s,%s\n',keytype,fullkey,fpath);
fclose(fid);
end

function hex = CalcSHA1(filename)
fid=fopen(filename,'r'); bytes=fread(fid,Inf,'*uint8'); fclose(fid);
sha=java.security.MessageDigest.getInstance('SHA-1');
sha.update(typecast(bytes(:),'int8'));
out=typecast(sha.digest(),'uint8');
hex=lower(reshape(dec2hex(out,2).',1,[]));
end
