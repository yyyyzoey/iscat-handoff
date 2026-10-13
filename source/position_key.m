function key=position_key(D,zf,dx)
% v075 collision-free physical-state key (signed; pm integers; fixed width).
% Hardened v076: rejects non-finite and non-authorised D/zf/x values.
allowedD=[30 60 100]; allowedZF=[450 550]; allowedX=[-20 -15 -10 -5 0 5 10 15 20];
assert(isscalar(D)&&isscalar(zf)&&isscalar(dx),'position_key: scalars required');
assert(all(isfinite([D zf dx])),'position_key: non-finite input rejected');
assert(any(D==allowedD),'position_key: D=%g not in authorised set',D);
assert(any(zf==allowedZF),'position_key: zf=%g not in authorised set',zf);
assert(any(abs(dx-allowedX)<1e-9),'position_key: dx=%g not in authorised set',dx);
s='P'; if dx<0, s='M'; end
key=sprintf('D%d_ZF%d_X%s%07d',D,zf,s,round(abs(dx)*1000));
end
