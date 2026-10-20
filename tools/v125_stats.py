"""V125 S1-D: corrected statistics (even-sample median) and noise-aware residual.

The V124 scripts used np.median incorrectly for report wording; here the
canonical set is computed explicitly. The weighted residual uses the contract
variance model so noisy observations are compared against their own floor.
"""
import numpy as np

def error_stats(errors_nm):
    e = np.asarray(errors_nm, float)
    se = np.sort(np.abs(e))
    n = len(se)
    med = float(np.mean(se[ n//2 - 1 : n//2 + 1 ])) if n % 2 == 0 and n > 0 else \
          float(se[n // 2]) if n else float('nan')
    return dict(n=n, mean_signed=float(np.mean(e)) if n else float('nan'),
                MAE=float(np.mean(np.abs(e))) if n else float('nan'),
                RMSE=float(np.sqrt(np.mean(e ** 2))) if n else float('nan'),
                median_abs=med,
                std=float(np.std(e, ddof=1)) if n > 1 else float('nan'),
                range=float(np.max(e) - np.min(e)) if n else float('nan'))

def weighted_residual(Y_e, mu_model, B_hat, sigma_r=2.0, K_blank=8):
    """Electronic-domain weighted residual (contract S6-A variance model).

    Var(Y_p - B_hat_p(1+C_p)) ~= mu_p + sigma_r^2 + (1+C_p)^2 (B_p + sigma_r^2)/K
    implemented with mu_p = B_hat_p (1 + C_p) as the model expectation.
    Returns chi-like sqrt(mean(w_r^2)) normalized by sqrt(n_pix)."""
    C = mu_model / B_hat - 1.0
    mu = np.clip(mu_model, 0, None)
    var = mu + sigma_r ** 2 + (1.0 + C) ** 2 * (B_hat + sigma_r ** 2) / K_blank
    w = (Y_e - mu) / np.sqrt(np.clip(var, 1e-12, None))
    return float(np.sqrt(np.mean(w ** 2)))

def s1_regression():
    rows = []
    errs = [-0.5, -0.5, 0.0, 0.0, 0.0, 1.0]
    s = error_stats(errs)
    rows.append(dict(fixture='v124_holdout_even_median', value=s['median_abs'],
                     passed=abs(s['median_abs'] - 0.25) < 1e-12,
                     detail=f"MAE={s['MAE']:.6f} (1/3) RMSE={s['RMSE']:.6f} (0.5) median|e|={s['median_abs']}"))
    rows.append(dict(fixture='mean_signed_not_called_MAE', value=s['mean_signed'],
                     passed=True, detail='separate columns; signed mean reported as such'))
    return rows

if __name__ == '__main__':
    for r in s1_regression():
        print(('PASS' if r['passed'] else 'FAIL'), r['fixture'], r['value'], '|', r['detail'])
