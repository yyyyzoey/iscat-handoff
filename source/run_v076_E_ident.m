function run_v076_E_ident(outRoot)
if nargin<1||isempty(outRoot), outRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v076_return'; end
r=load('C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4\v075_return\numeric\v075_dynamic_C400_corrected.mat');
f=fopen(fullfile(outRoot,'tables','v076_dynamic_nuisance_identifiability.csv'),'w');
fprintf(f,'state_i,state_j,changed_parameter,complex_relL2,abs_relL2,note\n');
fn=fieldnames(r); n=0;
for i=1:numel(fn)
  for j2=i+1:numel(fn)
    ci=r.(fn{i}); cj=r.(fn{j2});`n    if ~isfield(ci,'D')||~isfield(cj,'D'), continue; end
    chg='';
    if ci.D~=cj.D, chg=[chg '+D']; end
    if ci.zf~=cj.zf, chg=[chg '+zf']; end
    if ci.amp~=cj.amp, chg=[chg '+a']; end
    if ~strcmp(ci.ttype,cj.ttype), chg=[chg '+type']; end
    if isempty(chg), continue; end
    relC=norm(double(ci.C400(:))-double(cj.C400(:)))/max(norm(double(cj.C400(:))),realmin);
    relA=norm(abs(ci.C400(:))-abs(cj.C400(:)))/max(norm(abs(cj.C400(:))),realmin);
    fprintf(f,'%s,%s,%s,%.17g,%.17g,%s\n',fn{i},fn{j2},chg,relC,relA,'PRESCRIBED trajectories; no arbitrary amplitude/phase fitting');
    n=n+1;
  end
end
fclose(f);
fprintf('[076E] pairs: %d\n',n);
end


