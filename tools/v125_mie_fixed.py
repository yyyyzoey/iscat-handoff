"""V125 S1-A: corrected independent Mie reference (contract formula, exp(-iwt)).

Riccati-Psi convention: psi_l(z)=z j_l(z), xi_l(z)=z h_l^(1)(z)=z(j_l+ i y_l),
a_l,b_l per contract Eq. Energy fixture: lossless sphere must give
Qabs = Qext - Qsca ~= 0 (this FAILS for a wrong outgoing convention).
"""
import numpy as np
from scipy.special import spherical_jn, spherical_yn

def mie_ab(D_nm, lam_nm=520.0, n_p=1.38+0j, n_w=1.3353, lmax=None):
    m = n_p / n_w
    x = np.pi * n_w * D_nm / lam_nm
    if lmax is None:
        lmax = max(int(np.ceil(x + 4 * x ** (1/3) + 2)), 5)
    ell = np.arange(1, lmax + 1)
    def psi(l, z): return z * spherical_jn(l, z)          # z j_l
    def dpsi(l, z): return spherical_jn(l, z) + z * spherical_jn(l, z, derivative=True)
    def xi(l, z): return z * (spherical_jn(l, z) + 1j * spherical_yn(l, z))   # z h^(1)
    def dxi(l, z): return (spherical_jn(l, z) + 1j * spherical_yn(l, z)
                           + z * (spherical_jn(l, z, derivative=True) + 1j * spherical_yn(l, z, derivative=True)))
    a = np.empty(lmax, complex); b = np.empty(lmax, complex)
    mx = x * m
    for i, l in enumerate(ell):
        a[i] = (m * psi(l, mx) * dpsi(l, x) - psi(l, x) * dpsi(l, mx)) / \
               (m * psi(l, mx) * dxi(l, x) - xi(l, x) * dpsi(l, mx))
        b[i] = (psi(l, mx) * dpsi(l, x) - m * psi(l, x) * dpsi(l, mx)) / \
               (psi(l, mx) * dxi(l, x) - m * xi(l, x) * dpsi(l, mx))
    return x, a, b

def mie_efficiencies(D_nm, lam_nm=520.0, n_p=1.38+0j, n_w=1.3353, lmax=None):
    x, a, b = mie_ab(D_nm, lam_nm, n_p, n_w, lmax)
    ell = np.arange(1, len(a) + 1)
    Qsca = float(2 / x**2 * np.sum((2*ell+1) * (np.abs(a)**2 + np.abs(b)**2)))
    Qext = float(2 / x**2 * np.sum((2*ell+1) * np.real(a + b)))
    return dict(D_nm=D_nm, x=float(x), lmax=len(a), a1=complex(a[0]), b1=complex(b[0]),
                Qsca=Qsca, Qext=Qext, Qabs=Qext - Qsca,
                rayleigh_Qsca=float(8/3 * x**4 * abs((m2 := (n_p/n_w))**2 - 1)**2 / abs(m2**2 + 2)**2))

def s1_regression():
    """Fixtures: (F1) lossless Qabs~0; (F2) n-match Qsca->0; (F3) small-x Rayleigh."""
    rows = []
    for D in (10, 15, 20, 30, 100, 200):
        r = mie_efficiencies(D)
        rows.append(dict(fixture=f'lossless_Qabs_D{D}', value=r['Qabs'],
                         passed=abs(r['Qabs']) < 1e-8 * max(r['Qext'], 1e-30) + 1e-14,
                         detail=f"Qsca={r['Qsca']:.6g} Qext={r['Qext']:.6g}"))
    rn = mie_efficiencies(100, n_p=1.3353+0j)
    rows.append(dict(fixture='nmatch_Qsca_zero', value=rn['Qsca'], passed=rn['Qsca'] < 1e-20,
                     detail='np=nwater'))
    for D in (10, 20):
        r = mie_efficiencies(D)
        rows.append(dict(fixture=f'smallx_rayleigh_D{D}', value=r['Qsca'] / r['rayleigh_Qsca'],
                         passed=abs(r['Qsca'] / r['rayleigh_Qsca'] - 1) < 0.03,
                         detail=f"x={r['x']:.4f} ratio_vs_Rayleigh"))
    return rows

if __name__ == '__main__':
    for r in s1_regression():
        print(('PASS' if r['passed'] else 'FAIL'), r['fixture'], r['value'], r['detail'])
