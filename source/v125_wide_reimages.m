function wide_map = v125_wide_reimages()
% Re-image the already-solved V125 caches on the 25x25 wide camera grid.
% Identity of each solve is re-verified from the cached s.cfg/meta before use.
% Zero new BEM solves; each render counts once against the render budget.
repo = fileparts(fileparts(mfilename('fullpath')));
outDir = fullfile(repo, 'results', 'v125');
mapFile = fullfile(outDir, 'logs', 'cache_key_map.csv');
fid = fopen(mapFile, 'r'); hdr = fgetl(fid);
rows = {};
while ~feof(fid)
    ln = fgetl(fid);
    if ~ischar(ln), break; end
    parts = strsplit(ln, ',', 'CollapseDelimiters', false);
    if numel(parts) >= 3 && strcmp(parts{1}, 'solve')
        rows{end+1} = parts; %#ok<AGROW>
    end
end
fclose(fid);
projectRoot = fileparts(repo);
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~] = prepare_nanobem(projectRoot,'');
rendDir = fullfile(outDir, 'renders');
outCsv = fullfile(outDir, 'logs', 'wide_render_map.csv');
fid2 = fopen(outCsv, 'w');
fprintf(fid2, 'tag,phys,file\n');
n = 0;
for k = 1:numel(rows)
    fullkey = rows{k}{2};
    fpath = rows{k}{3};
    if ~isfile(fpath), continue; end
    tok = regexp(fullkey, '__', 'split');
    if numel(tok) < 3, continue; end
    tag = tok{2}; phys = tok{3};
    mm = regexp(phys, 'D([-0-9.]+)_h([-0-9.]+)_np([-+0-9.]+)', 'tokens', 'once');
    if isempty(mm), continue; end
    D = str2double(mm{1}); h = str2double(mm{2}); npr = str2double(mm{3});
    if ~(strcmp(tag(1:5),'train') || strcmp(tag(1:7),'holdout')), continue; end
    tmp = load(fpath, 's', 'meta');
    s = tmp.s; meta = tmp.meta;
    if abs(meta.D_nm - D) > 1e-12 || abs(meta.h_nm - h) > 1e-9 || abs(meta.np_re - npr) > 1e-12
        fprintf('[wide] identity MISMATCH %s\n', fullkey); continue;
    end
    cw = meta_cfg(s);
    cw.sampling.Nx = 25; cw.sampling.Ny = 25;
    r = render_system(s, cw);
    rfile = fullfile(rendDir, sprintf('widere_%s.mat', tag));
    save(rfile, 'r', '-v7.3');
    fprintf(fid2, '%s,%s,%s\n', tag, phys, rfile);
    n = n + 1;
    fprintf('[wide] %s C %dx%d peak=%.6g\n', tag, size(r.contrast,1), size(r.contrast,2), max(abs(r.contrast(:))));
end
% second phase: V124-verified nodes (import map) that have no V125 solve
importFile = fullfile(outDir, 'logs', 'cache_import_map.csv');
fid3 = fopen(importFile, 'r'); hdr3 = fgetl(fid3);
while ~feof(fid3)
    ln = fgetl(fid3);
    if ~ischar(ln), break; end
    p = strsplit(ln, ',', 'CollapseDelimiters', false);
    fprintf('[wide-v124] row %s verified=%s\n', p{1}, p{3});
    if numel(p) < 5 || ~(strcmp(p{3}, 'True') || strcmp(p{3}, '1')), continue; end
    node = p{1}; meshv = str2double(p{2}); src = p{5};
    if ~isfile(src)
        src2 = fullfile(repo, 'results', 'v124', 'bem_cache', src);
        if isfile(src2), src = src2; else, continue; end
    end
    tag = ['train_' node];
    rfile = fullfile(rendDir, sprintf('widere_%s.mat', tag));
    if isfile(rfile), continue; end
    tD = regexp(node, 'D([-0-9.]+)', 'tokens', 'once');
    tH = regexp(node, '_h([-0-9.]+)', 'tokens', 'once');
    D = str2double(tD{1}); h = str2double(tH{1});
    tmp = load(src, 's'); s = tmp.s; clear tmp;
    sc = s.cfg;
    h_chk = sc.particle.gap_nm + sc.particle.diameter_nm/2;
    if abs(sc.particle.diameter_nm - D) > 1e-12 || abs(h_chk - h) > 1e-9, continue; end
    cw = meta_cfg(s); cw.sampling.Nx = 25; cw.sampling.Ny = 25;
    r = render_system(s, cw);
    save(rfile, 'r', '-v7.3');
    fprintf(fid2, '%s,%s,%s\n', tag, sprintf('D%g_h%g_np1.38000000+0.00000000_mesh%d', D, h, meshv), rfile);
    n = n + 1;
    fprintf('[wide-v124] %s C %dx%d\n', tag, size(r.contrast,1), size(r.contrast,2));
end
fclose(fid3);
fclose(fid2);
wide_map = outCsv;
fprintf('[wide] done: %d wide re-images\n', n);
end

function c = meta_cfg(~)
c = iscat_config('camera');
c.lambda_nm = 520; c.layers.n = [1.5, 1.3353]; c.layers.interfaces_nm = 0;
c.layers.particle_layer = 2; c.objective.NA = 0.8;
c.objective.nominal_magnification = 50; c.tube.actual_focal_mm = 200;
c.tube.relay_magnification = 1; c.sampling.pixel_um = 14;
c.sampling.subpixels = 5; c.numerics.ntheta = 50; c.numerics.nphi = 51;
c.numerics.bessel_table_points = 2001; c.illumination.angle_deg = 0;
c.image_side_n = 1; c.focus_nm = [0,0,450];
end
