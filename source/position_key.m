function key=position_key(D,zf,dx)
% v075 collision-free physical-state key (signed; pm integers; fixed width).
% Example: position_key(60,450,-10) -> 'D60_ZF450_XM10000'
%          position_key(60,450,+10) -> 'D60_ZF450_XP10000'
s='P'; if dx<0, s='M'; end
key=sprintf('D%d_ZF%d_X%s%07d',D,zf,s,round(abs(dx)*1000));
end
