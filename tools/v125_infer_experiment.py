"""V125 single-particle experimental ROI interface (S6-E).

Accepts a raw linear-intensity 17x17 (or larger, auto-centred) ROI plus a
same-conditions background ROI, and estimates D/h/x/y under the frozen V125
model. Rejects min-max PNG-style or arbitrarily normalised magnitude images.
All outputs are CONDITIONAL_MODEL_ESTIMATE_NOT_ABSOLUTE_MEASUREMENT until
independent optical/material/ruler calibration exists.

Usage:
  python tools/v125_infer_experiment.py --model results/v125/library/v125_Dh_train_fields.h5 \
      --input roi.npy --background blank.npy --config config/v125_effective_config.json \
      --out results/v125/experiment_interface_smoketest/
"""
import argparse, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v125_model_library as vml
import v125_invert_particle as vin
import v125_stats as vst

def load_array(path):
    if path.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise SystemExit('REJECTED: display image (PNG/JPG) has unknown normalization; '
                         'provide raw linear-intensity .npy/.tif/.mat')
    if path.lower().endswith('.npy'):
        return np.load(path)
    if path.lower().endswith(('.tif', '.tiff')):
        import tifffile
        return tifffile.imread(path)
    if path.lower().endswith('.mat'):
        import h5py
        with h5py.File(path, 'r') as f:
            k = list(f.keys())[0]
            return np.array(f[k]).T
    raise SystemExit(f'REJECTED: unsupported input type {path}')

def extract_roi(img):
    img = np.asarray(img, float)
    if img.ndim == 3:
        img = img[..., 0] if img.shape[-1] <= 4 else img[0]
    if img.shape[0] < 17 or img.shape[1] < 17:
        raise SystemExit(f'REJECTED: ROI smaller than 17x17 (got {img.shape})')
    if img.min() < 0:
        raise SystemExit('REJECTED: negative values imply signed/processed C, not raw linear intensity')
    if img.max() <= img.min():
        raise SystemExit('REJECTED: constant image')
    # centre on the brightest pixel, take central 17x17
    iy, ix = np.unravel_index(np.argmax(img), img.shape)
    r = 8
    y0 = min(max(iy - r, 0), img.shape[0] - 17)
    x0 = min(max(ix - r, 0), img.shape[1] - 17)
    return img[y0:y0 + 17, x0:x0 + 17]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--tab', default=None)
    ap.add_argument('--input', required=True)
    ap.add_argument('--background', required=True)
    ap.add_argument('--config', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--background_e', type=float, default=None,
                    help='expected background electrons at 100us; if omitted, estimated from --background ROI mean')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    img = extract_roi(load_array(args.input))
    bg = extract_roi(load_array(args.background))
    B_hat = float(np.mean(bg)) if args.background_e is None else float(args.background_e)
    if not np.isfinite(B_hat) or B_hat <= 1:
        raise SystemExit('REJECTED: background electrons not positive; linear raw data required')
    # normalize both to the same exposure scale: relative C from counts
    Cobs = (img - bg) / bg
    tab = args.tab or os.path.join(os.path.dirname(args.model), 'v125_shift_tables.h5')
    lib = vml.TrainLibrary(args.model, tab)
    est = vin.Estimator(lib)
    r1 = est.m1(Cobs[2:15, 2:15])
    result = dict(
        particle_id=os.path.basename(args.input),
        model_diameter_type='UNIFORM_SPHERE_OPTICAL_EQUIVALENT',
        D_est_nm=r1['best']['D'], h_est_nm=r1['best']['h'],
        x_est_nm=r1['best']['x'], y_est_nm=r1['best']['y'],
        fit_loss=r1['best']['loss'],
        alternative_solutions=[dict(D=b['D'], h=b['h'], x=b['x'], y=b['y'], loss=b['loss'])
                               for b in r1['basins'][1:]],
        boundary=bool(r1['best']['boundary_D'] or r1['best']['boundary_h'] or r1['best']['boundary_xy']),
        rejected=bool(r1['best']['loss'] > 0.05),
        rejection_reason='residual above frozen clean-observation threshold' if r1['best']['loss'] > 0.05 else '',
        claim='CONDITIONAL_MODEL_ESTIMATE_NOT_ABSOLUTE_MEASUREMENT',
        model_hash=vml.sha256(args.model),
        background_e_per_pix=B_hat,
        Cobs_17x17=Cobs.tolist(),
        model_C_13x13=lib.template_C(r1['best']['D'], r1['best']['h']).tolist(),
    )
    with open(os.path.join(args.out, 'particle_result.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=1)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 3, figsize=(12, 3.6), constrained_layout=True)
        vmax = np.max(np.abs(Cobs)) or 1
        for a, (d, t) in zip(ax, [(Cobs, 'observed C'), (lib.template_C(r1['best']['D'], r1['best']['h']), 'model C'),
                                  (Cobs[2:15, 2:15] - lib.template_C(r1['best']['D'], r1['best']['h']), 'residual')]):
            im = a.imshow(d, cmap='RdBu_r', vmin=-vmax, vmax=vmax, origin='lower')
            a.set_title(t); plt.colorbar(im, ax=a, shrink=0.85)
        fig.savefig(os.path.join(args.out, 'fit.png'), dpi=150)
    except Exception as e:
        result['figure_error'] = str(e)
    print(json.dumps({k: result[k] for k in ('D_est_nm', 'h_est_nm', 'x_est_nm', 'y_est_nm', 'fit_loss', 'claim')}, indent=1))

if __name__ == '__main__':
    main()
