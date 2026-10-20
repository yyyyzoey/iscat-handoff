function tab = v124_mie_reference(outCsv)
%V124_MIE_REFERENCE Independent small-sphere Mie benchmark (no NANOBEM code).
%   Bohren & Huffman Mie coefficients for a lossless uniform sphere
%   np=1.38 in water nw=1.3353 at 520nm, compared with the Rayleigh limit
%   Qsca = (8/3) x^4 |(m^2-1)/(m^2+2)|^2. This is a scattering benchmark
%   ONLY; it is never used as an iSCAT contrast or diameter calibration.
lam = 520; nw = 1.3353; np_ = 1.38;
m = np_/nw;
Dlist = [10,15,20,30];
rows = cell(0,1);
for D = Dlist
    x = pi*nw*D/lam;
    lmax = ceil(x + 4*x^(1/3) + 2);
    ell = (1:lmax).';
    psi  = arrayfun(@(l)sph_bessel_j(l,x*m),ell);
    dpsi = arrayfun(@(l)sph_bessel_jd(l,x*m),ell);
    psix  = arrayfun(@(l)sph_bessel_j(l,x),ell);
    dpsix = arrayfun(@(l)sph_bessel_jd(l,x),ell);
    psi_m = psi; dpsi_m = dpsi;
    xi   = psix  - 1i*arrayfun(@(l)sph_bessel_y(l,x),ell);
    dxi  = dpsix - 1i*arrayfun(@(l)sph_bessel_yd(l,x),ell);
    a = (m*psi_m.*dpsix - psix.*dpsi_m)./(m*psi_m.*dxi - xi.*dpsi_m);
    b = (psi_m.*dpsix - m*psix.*dpsi_m)./(psi_m.*dxi - m*xi.*dpsi_m);
    Qsca = (2/x^2)*sum((2*ell+1).*(abs(a).^2+abs(b).^2));
    Qext = (2/x^2)*sum((2*ell+1).*real(a+b));
    Qabs = Qext - Qsca;
    F = (m^2-1)./(m^2+2);
    Qsca_ray = (8/3)*x^4*abs(F)^2;
    rows{end+1} = table(D,x,lmax,Qsca,Qext,Qabs,Qsca_ray,abs(Qsca-Qsca_ray)/Qsca_ray); %#ok<AGROW><SAGROW>
    fprintf('[v124:mie] D=%g x=%.6g Qsca=%.10g Qsca_ray=%.10g reldiff=%.3g\n', ...
        D,x,Qsca,Qsca_ray,abs(Qsca-Qsca_ray)/Qsca_ray);
end
tab = vertcat(rows{:});
tab.Properties.VariableNames = {'D_nm','size_parameter_x','lmax','Qsca_mie','Qext_mie','Qabs_mie','Qsca_rayleigh_limit','rel_diff_vs_rayleigh'};
if nargin>=1 && ~isempty(outCsv)
    writetable(tab,outCsv);
    fprintf('[v124:mie] wrote %s\n',outCsv);
end
end

function y = sph_bessel_j(l,x)
y = sqrt(pi/(2*x))*besselj(l+0.5,x);
end
function y = sph_bessel_y(l,x)
y = sqrt(pi/(2*x))*bessely(l+0.5,x);
end
function d = sph_bessel_jd(l,x)
d = sph_bessel_j(l-1,x) - l/x*sph_bessel_j(l,x);
end
function d = sph_bessel_yd(l,x)
d = sph_bessel_y(l-1,x) - l/x*sph_bessel_y(l,x);
end
