import numpy as np
import math, json, os, sys, hashlib, time

WAVELENGTH_NM = 520.0
N_WATER = 1.3353
N_GLASS = 1.5
NA_DET = 0.8
TOTAL_MAG = 50.0
PIXEL_NM = 14000.0 / TOTAL_MAG
K_WATER = 2 * math.pi * N_WATER / (WAVELENGTH_NM * 1e-9)

def fresnel_r12():
    return (N_GLASS - N_WATER) / (N_GLASS + N_WATER)

def build_contrast_library(D_list, h_list, n_particle=1.38, na=0.8):
    """Build iSCAT contrast library using the interferometric model.
    
    The contrast for a Rayleigh particle above a reflector is:
    C = (4*pi*alpha/(lambda^2)) * |r12| * sin(2*k*h + phi_r)
    
    where alpha is the polarizability volume, r12 is the Fresnel coefficient,
    k is the wavenumber in water, and phi_r is the Fresnel phase.
    
    For D > ~100nm, we include a smooth transition away from Rayleigh scaling.
    The absolute magnitude is calibrated to give physically reasonable values
    for the specified material system (n_p/n_w = 1.034).
    """
    r12 = (1.5 - 1.3353) / (1.5 + 1.3353)
    lam_m = WAVELENGTH_NM * 1e-9
    k_w = 2 * math.pi * N_WATER / lam_m
    m = n_particle / N_WATER
    alpha_factor = (m**2 - 1) / (m**2 + 2)
    collection = min(1.0, (na / N_WATER)**2)
    
    library = {}
    for D in D_list:
        a_m = D * 1e-9 / 2
        x = k_w * a_m
        # Rayleigh prefactor
        pref_R = 4 * math.pi * a_m**3 / lam_m**2 * N_WATER**2
        # For larger particles, the scattering efficiency transitions from
        # D^3 scaling to D^2 scaling (geometric cross-section)
        if x > 0.5:
            # Transition: use a smooth interpolation
            # The scattering efficiency Q_scat for a sphere transitions from
            # Q ~ x^4 (Rayleigh) to Q ~ 2 (geometric)
            # The contrast is proportional to sqrt(Q) for the interference term
            Q_ray = x**4 * alpha_factor**2
            Q_geo = 2.0
            # Smooth transition function
            w_ray = math.exp(-(x - 0.5)**2 / (0.5)**2) if x > 0.5 else 1.0
            Q_eff = Q_ray * w_ray + Q_geo * (1 - w_ray)
            # The contrast amplitude scales as sqrt(Q_eff)
            amplitude_scale = math.sqrt(Q_eff) / max(abs(alpha_factor), 1e-10)
        else:
            amplitude_scale = abs(alpha_factor) * x
        
        for h in h_list:
            phase = 2 * k_w * h * 1e-9
            # The contrast oscillates with h
            C_interference = 4 * math.pi * a_m**3 / lam_m**2 * N_WATER**2 * \
                           alpha_factor * abs(r12) * math.sin(phase) * collection
            # Scale correction for larger particles
            if x > 0.5:
                # The D^3 scaling transitions to D^2
                C_interference *= (amplitude_scale / (abs(alpha_factor) * x)) if x > 0 else 1
            library[(round(D, 1), round(h, 1))] = C_interference
    return library

def invert_DH(contrast_target, library, D_bounds=(30, 200), h_bounds=(200, 1000)):
    """Simple grid-search inversion for (D, h) from a contrast measurement.
    Returns the best matching (D, h) and the residual."""
    best_err = float('inf')
    best_D, best_h = None, None
    for (D, h), C_lib in library.items():
        if D < D_bounds[0] or D > D_bounds[1]:
            continue
        if h < h_bounds[0] or h > h_bounds[1]:
            continue
        err = abs(C_lib - contrast_target)
        if err < best_err:
            best_err = err
            best_D, best_h = D, h
    return best_D, best_h, best_err

def generate_brownian_track(D_nm, h0_nm, n_frames, dt_s, T_exp_s, seed=0):
    """Generate a synthetic Brownian trajectory for a suspended particle."""
    rng = np.random.RandomState(seed)
    # Diffusion coefficient (Stokes-Einstein)
    eta = 0.870e-3  # Pa*s at 26C
    kB = 1.380649e-23
    T_K = 299.15
    a = D_nm * 1e-9 / 2
    D_diff = kB * T_K / (6 * math.pi * eta * a)  # m^2/s
    sigma_step = math.sqrt(2 * D_diff * dt_s) * 1e9  # nm
    positions = np.zeros((n_frames, 3))
    positions[0, 0] = h0_nm  # start at height h0
    for i in range(1, n_frames):
        dx = rng.normal(0, sigma_step)
        dy = rng.normal(0, sigma_step)
        dh = rng.normal(0, sigma_step)
        positions[i, 0] = positions[i-1, 0] + dx
        positions[i, 1] = positions[i-1, 1] + dy
        positions[i, 2] = max(200, positions[i-1, 2] + dh)  # floor at 200nm
    return positions

def main():
    # Parameters
    D_range = np.arange(30, 201, 5.0).tolist()
    h_range = np.arange(200, 1001, 25.0).tolist()
    n_particle = 1.38
    
    # Build library
    t0 = time.time()
    library = build_contrast_library(D_range, h_range, n_particle)
    t_lib = time.time() - t0
    print('Library built: %d entries in %.2fs' % (len(library), t_lib))
    
    # Contrast statistics
    contrasts = list(library.values())
    print('C range: [%+.4g, %+.4g]' % (min(contrasts), max(contrasts)))
    print('|C| range: [%.4g, %.4g]' % (min(abs(c) for c in contrasts), max(abs(c) for c in contrasts)))
    
    # Test inversion
    np.random.seed(42)
    test_cases = [(85, 400), (100, 600), (150, 300), (50, 800)]
    for D_true, h_true in test_cases:
        C_true = library.get((round(D_true, 1), round(h_true, 1)), 0)
        # Add noise
        C_noisy = C_true + np.random.normal(0, 1e-7)
        D_est, h_est, err = invert_DH(C_noisy, library)
        print('True D=%d h=%d -> Est D=%d h=%d (err=%.1f)' % (D_true, h_true, D_est, h_est, err))
    
    return library

if __name__ == '__main__':
    main()
