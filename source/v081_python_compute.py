import h5py, numpy as np, os, re, csv

root = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4'
v076 = os.path.join(root, 'v076_return', 'numeric')

f76 = h5py.File(os.path.join(v076, 'v076_center_roi_harmonic_small_examples.mat'), 'r')
N = 2001; Fs = 5000; k0 = 160
results = []

for case_key in sorted(f76.keys()):
    if case_key.startswith('#'): continue
    g = f76[case_key]
    if 'series' not in g: continue
    m = re.match(r'D(\d+)_zf(\d+)_(M\d+)_a(\d+)', case_key)
    if not m: continue
    D = int(m.group(1)); zf = int(m.group(2)); ttype = m.group(3); aa = int(m.group(4))
    freqs = [200,400,600,800] if ttype=='M200' else [400,800,1200,1600]
    nH = len(freqs)
    series = np.array(g['series']).flatten().astype(np.float64)
    Im = np.mean(series); Ic = series - Im
    tj = np.arange(N) / Fs
    B = np.ones((N, 1 + 2*nH))
    for h in range(nH):
        B[:, 2*h] = np.cos(2*np.pi*freqs[h]*tj)
        B[:, 2*h+1] = np.sin(2*np.pi*freqs[h]*tj)
    rank_B = np.linalg.matrix_rank(B)
    cond_B = np.linalg.cond(B)
    coef, _, _, _ = np.linalg.lstsq(B, Ic, rcond=None)
    resid = Ic - B @ coef
    Ah = np.array([complex(coef[2*h], -coef[2*h+1]) for h in range(nH)])
    Ch = Ah / Im
    e = np.exp(-2j*np.pi*k0*np.arange(N)/N)
    Xbin = np.sum(Ic * e)
    Cbin = 2*abs(Xbin) / (N*Im)
    Xmodel = 0+0j
    leak200 = leak400 = leak800 = 0.0
    for h in range(nH):
        fh = freqs[h]
        u1 = fh/Fs - k0/N; u2 = -fh/Fs - k0/N
        piN_u1 = np.pi*N*u1; pi_u1 = np.pi*u1
        G1 = N*np.exp(1j*np.pi*u1*(N-1)) if abs(pi_u1)<1e-12 else np.exp(1j*pi_u1*(N-1))*np.sin(piN_u1)/np.sin(pi_u1)
        piN_u2 = np.pi*N*u2; pi_u2 = np.pi*u2
        G2 = N*np.exp(1j*np.pi*u2*(N-1)) if abs(pi_u2)<1e-12 else np.exp(1j*pi_u2*(N-1))*np.sin(piN_u2)/np.sin(pi_u2)
        Xh = (Ah[h]/2)*G1 + (np.conj(Ah[h])/2)*G2
        Xmodel += Xh
        Ctmp = 2*abs(Xh)/(N*Im)
        if fh==200: leak200 = Ctmp
        if fh==400: leak400 = Ctmp
        if fh==800: leak800 = Ctmp
    Xres = np.sum(resid * e)
    closure_abs = abs(Xbin - Xmodel - Xres)
    normY = np.sqrt(N)*np.linalg.norm(Ic)
    closure_rel = closure_abs/max(normY,1e-14)
    rmsR = np.sqrt(np.mean(resid**2))
    i400 = freqs.index(400)
    C400fit = abs(Ch[i400])
    st = 'PASS' if rank_B==1+2*nH and cond_B<1e8 and closure_rel<1e-10 else 'FAIL'
    results.append({'case_id':case_key,'D':D,'zf':zf,'type':ttype,'a':aa,
        'rank_B':rank_B,'cond_B':cond_B,'bin161_absC':abs(Xbin),
        'C400_fit_abs':C400fit,'leak200':leak200,'leak400':leak400,'leak800':leak800,
        'closure_abs':closure_abs,'closure_rel':closure_rel,'rmsR':rmsR,'status':st})

f76.close()
outdir = r'C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v081_return\tables'
os.makedirs(outdir, exist_ok=True)
with open(os.path.join(outdir,'v081_harmonics24_correct.csv'),'w',newline='') as f:
    w = csv.DictWriter(f, fieldnames=results[0].keys())
    w.writeheader(); w.writerows(results)
for r in results:
    print(f"{r['case_id']}: rank={r['rank_B']} cond={r['cond_B']:.2f} bin161={r['bin161_absC']:.6g} fit={r['C400_fit_abs']:.6g} ratio={r['bin161_absC']/max(r['C400_fit_abs'],1e-30):.4f} {r['status']}")
print(f"\nTotal: {len(results)}, PASS: {sum(1 for r in results if r['status']=='PASS')}")
