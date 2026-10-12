function run_v068_comprehensive(outRoot)
% v068: clean re-export of 27 conditions + 30/100nm homogeneous + 6-key-condition diagnostics.
% Apertures data goes to a SEPARATE file (not embedded in main CSV).
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,'');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v042_handoff\iSCAT_v042_Codex_handoff\matlab');
addpath('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v047_handoff\iSCAT_v047_Codex_handoff\matlab');
if nargin<1, outRoot=fullfile(projectRoot,'v068_return'); end
if ~isfolder(outRoot), mkdir(outRoot); end
diary(fullfile(outRoot,'matlab_run.log')); cl=onCleanup(@() diary('off'));
od65='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v065_return';
cx=33; ix=(cx-20):(cx+20);
Zf=375:25:575; sizes=[30,60,100];
apertures=[21,31,41,51,61,65];

% ==== B: export 30/100nm homogeneous results (already solved in v067) ====
for D=[30,100]
  sid=sprintf('D%d',D);
  f1=fullfile(projectRoot,'v067_return',sprintf('%s_homog1444.mat',sid));
  L=load(f1); s=L;
  fields=fieldnames(L);
  export=struct();
  for fi=1:numel(fields)
    fn=fields{fi}; v=L.(fn);
    if isnumeric(v)&&isscalar(v), export.(fn)=v;
    elseif ischar(v)||isstring(v), export.(fn)=char(v);
    elseif islogical(v)&&isscalar(v), export.(fn)=double(v);
    end
  end
  export.D_nm=D; export.material='Fe3O4 complex(2.349,0.083)'; export.medium='homogeneous water 1.33';
  fid=fopen(fullfile(outRoot,sprintf('%s_homog_full_precision.json',sid)),'w');
  fwrite(fid,jsonencode(export)); fclose(fid);
  fprintf('[068:B] %s homogeneous exported (rawL2=%.4f sca=%.4f abs=%.4f ext=%.4f)\n', ...
    sid,L.fm.raw_complex_relative_L2,L.es,L.ea,L.ex);
end

% ==== C: re-render and re-export 27 conditions (flat CSV, no apertures) ====
main_rows={}; ap_rows={};
for D=sizes
  sid=sprintf('D%d',D);
  sp=load(fullfile(od65,sprintf('%s_s_576.mat',sid)),'s'); sp=sp.s;
  sf=load(fullfile(od65,sprintf('%s_s_1444.mat',sid)),'s'); sf=sf.s;
  for zf=Zf
    cp=sp.cfg; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
    rp=render_system(sp,cp);
    cf=sf.cfg; cf.focus_nm=[0,0,zf]; cf.sampling.subpixels=5;
    rf=render_system(sf,cf);
    % D1: field decomposition
    Es_p=rp.Esca; Er_p=rp.Eref; I0_p=rp.Iref;
    Cs_p=pixel_mean(sum(abs(Es_p).^2,3),5)./I0_p;
    Cint_p=pixel_mean(2*real(sum(conj(Er_p).*Es_p,3)),5)./I0_p;
    Es_f=rf.Esca; Er_f=rf.Eref; I0_f=rf.Iref;
    Cs_f=pixel_mean(sum(abs(Es_f).^2,3),5)./I0_f;
    Cint_f=pixel_mean(2*real(sum(conj(Er_f).*Es_f,3)),5)./I0_f;
    % Frobenius (correct)
    P=rp.contrast(ix,ix); R=rf.contrast(ix,ix);
    num=norm(P(:)-R(:),2); den=norm(R(:),2); rF=num/den;
    rSpec=norm(P-R,2)/norm(R,2);
    % D2: apertures
    ap_data=[];
    for ap=apertures
      half=round((ap-1)/2); x0=cx-half;
      if x0<1, ap_data=[ap_data struct('aperture',ap,'status','NOT_AVAILABLE')]; continue; end
      ia=(x0):(x0+ap-1);
      CpA=rp.contrast(ia,ia); CfA=rf.contrast(ia,ia);
      rel=norm(CpA(:)-CfA(:),2)/max(norm(CfA(:)),realmin);
      S_p=65^2*sum(CpA(:),'all'); S_f=65^2*sum(CfA(:),'all');
      Sp=65^2*sum(max(CpA(:),0)); Sm=65^2*sum(min(CpA(:),0));
      ap_data=[ap_data struct('aperture',ap,'relL2',rel,'S_prod',S_p,'S_fine',S_f,'S_plus_prod',Sp,'S_minus_prod',Sm)]; %#ok<AGROW>
    end
    % flat main record
    main_rows{end+1}={D,zf,num,den,rF,rSpec,rF<0.02, ...
      mean(Cs_p(:)),mean(Cint_p(:)),mean(Cs_f(:)),mean(Cint_f(:)), ...
      rp.contrast(33,33),rf.contrast(33,33), ...
      65^2*sum(rp.contrast(ix,ix),'all'),65^2*sum(rf.contrast(ix,ix),'all')}; %#ok<AGROW>
    % flat aperture records
    for ai=1:numel(ap_data)
      a0=ap_data(ai);
      if isfield(a0,'relL2')
        ap_rows{end+1}={D,zf,a0.aperture,a0.relL2,a0.S_prod,a0.S_fine,a0.S_plus_prod,a0.S_minus_prod}; %#ok<AGROW>
      else
        ap_rows{end+1}={D,zf,a0.aperture,NaN,NaN,NaN,NaN,NaN}; %#ok<AGROW>
      end
    end
    fprintf('[068:c] D=%g zf=%d rF=%.4f rSpec=%.4f\n',D,zf,rF,rSpec);
  end
end
% write main CSV (all flat, same field count)
hdr={'D_nm','zf_nm','numerator','denominator','frobenius_relL2_41x41','spectral_diagnostic','gate2pct_frobenius', ...
  'Cs_prod_mean','Cint_prod_mean','Cs_fine_mean','Cint_fine_mean', ...
  'C_center_prod','C_center_fine','S_area_prod_nm2','S_area_fine_nm2'};
fid=fopen(fullfile(outRoot,'v068_27condition_clean.csv'),'w');
fprintf(fid,'%s\n',strjoin(hdr,','));
for i=1:numel(main_rows), fprintf(fid,'%d,%d,%.17g,%.17g,%.17g,%.17g,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n',main_rows{i}{:}); end
fclose(fid);
% write aperture CSV (separate)
ahdr={'D_nm','zf_nm','aperture_px','relL2','S_prod_nm2','S_fine_nm2','S_plus_prod_nm2','S_minus_prod_nm2'};
fid=fopen(fullfile(outRoot,'v068_aperture_dependence.csv'),'w');
fprintf(fid,'%s\n',strjoin(ahdr,','));
for i=1:numel(ap_rows), fprintf(fid,'%d,%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g\n',ap_rows{i}{:}); end
fclose(fid);
fprintf('[068:c] 27-condition clean CSV + %d aperture records written\n',numel(ap_rows));

% ==== D: six key conditions deep dive ====
key_conds=[30,450;30,550;60,450;60,550;100,450;100,550];
d_rows={};
for ki=1:size(key_conds,1)
  D=key_conds(ki,1); zf=key_conds(ki,2);
  sid=sprintf('D%d',D);
  sp=load(fullfile(od65,sprintf('%s_s_576.mat',sid)),'s'); sp=sp.s;
  sf=load(fullfile(od65,sprintf('%s_s_1444.mat',sid)),'s'); sf=sf.s;
  cp=sp.cfg; cp.focus_nm=[0,0,zf]; cp.sampling.subpixels=5;
  rp=render_system(sp,cp);
  cf=sf.cfg; cf.focus_nm=[0,0,zf]; cf.sampling.subpixels=5;
  rf=render_system(sf,cf);
  % signed response metrics
  Cc_p=rp.contrast(33,33); Cc_f=rf.contrast(33,33);
  S_p=65^2*sum(rp.contrast(ix,ix),'all'); S_f=65^2*sum(rf.contrast(ix,ix),'all');
  Sp=65^2*sum(max(rp.contrast(ix,ix),0),'all');
  Sm=65^2*sum(min(rp.contrast(ix,ix),0),'all');
  Sfp=65^2*sum(max(rf.contrast(ix,ix),0),'all');
  Smf=65^2*sum(min(rf.contrast(ix,ix),0),'all');
  % chi1 (cancellation metric): sum|C| / |sum C|
  tmp_p=rp.contrast(ix,ix); chi1_p=sum(abs(tmp_p(:)))/abs(sum(tmp_p(:)));
  tmp_f=rf.contrast(ix,ix); chi1_f=sum(abs(tmp_f(:)))/abs(sum(tmp_f(:)));
  % K_S2: sqrt(N)*||C||_2 / |sum C|
  N41=41*41;
  K_p=sqrt(N41)*norm(tmp_p,2)/abs(sum(tmp_p(:)));
  K_f=sqrt(N41)*norm(tmp_f,2)/abs(sum(tmp_f(:)));
  d_rows{end+1}={D,zf,Cc_p,Cc_f,S_p,S_f,Sp,Sm,Sfp,Smf,chi1_p,chi1_f,K_p,K_f}; %#ok<AGROW>
  fprintf('[068:d] D=%g zf=%d chi1_p=%.2f chi1_f=%.2f K_p=%.1f K_f=%.1f\n',D,zf,chi1_p,chi1_f,K_p,K_f);
end
dhdr={'D_nm','zf_nm','C_center_prod','C_center_fine','S_area_prod_nm2','S_area_fine_nm2', ...
  'S_plus_prod_nm2','S_minus_prod_nm2','S_plus_fine_nm2','S_minus_fine_nm2', ...
  'chi1_prod','chi1_fine','K_S2_prod','K_S2_fine'};
fid=fopen(fullfile(outRoot,'v068_six_key_observations.csv'),'w');
fprintf(fid,'%s\n',strjoin(dhdr,','));
for i=1:numel(d_rows), fprintf(fid,'%d,%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n',d_rows{i}{:}); end
fclose(fid);
fprintf('[068:d] six key conditions done\n');
fprintf('[068] ALL DONE\n');
end

