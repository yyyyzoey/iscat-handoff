function run_v062_p0_layout_tests(nanobemRoot, outRoot)
% v062 P0: duffy1/eval2 layout tests. Same-mode aligned pair lists ('rows',1).
% Independent reference = explicit scalar index summation (fix1+fix2 used).
projectRoot='C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4';
addpath(fullfile(projectRoot,'src'),fullfile(projectRoot,'config'));
[~,~]=prepare_nanobem(projectRoot,nanobemRoot);
if nargin<2, outRoot=fullfile(projectRoot,'v062_return','p0_layout'); end
if ~isfolder(outRoot), mkdir(outRoot); end
tag='baseline'; if contains(nanobemRoot,'p0layout2'), tag='candidate'; end
diary(fullfile(outRoot,['layout_' tag '_v062.log'])); cl=onCleanup(@() diary('off'));
q=trisphere(4,35.5);
mats=[Material(1.5^2,1),Material(1.33^2,1),Material(epstable('gold.dat'),1)];
tau=BoundaryEdge(mats,q,[3,2]);
M=touching(tau,tau);
[fa,fb]=find(M==3); [ea,eb]=find(M==2); [va,vb]=find(M==1);
k1=2*pi/520/1.33;
cases={};
for k=[1,2,3]
  cases{end+1}={tau(fa(1:min(k,end))),tau(fb(1:min(k,end))),'face',k}; %#ok<AGROW>
  if numel(ea)>=k, cases{end+1}={tau(ea(1:k)),tau(eb(1:k)),'edge',k}; end %#ok<AGROW>
  if numel(va)>=k, cases{end+1}={tau(va(1:k)),tau(vb(1:k)),'vert',k}; end %#ok<AGROW>
end
rows={};
for cc=1:numel(cases)
  t1=cases{cc}{1}; t2=cases{cc}{2}; modes=cases{cc}{3}; kexp=cases{cc}{4};
  pts=quadduffy(t1,t2,3,'rows',1);
  for m=1:numel(pts)
    obj=galerkin.pot1.duffy1('nduffy',3); obj.pts=pts(m);
    npair=numel(pts(m).tau1); mmode=char(string(pts(m).mode));
    err='';
    try
      data=eval2(obj,k1);
      sz=mat2str(size(data.SL));
      [pos1,f1,fp1]=eval(pts(m),1); [pos2,f2,fp2]=eval(pts(m),2);
      w=pts(m).w; Q=size(pos1,2);
      ref=zeros(npair,3,3); refDL=zeros(npair,3,3);
      for p=1:npair
        for qq=1:Q
          dx=pos1(p,qq,1)-pos2(p,qq,1); dy=pos1(p,qq,2)-pos2(p,qq,2); dz=pos1(p,qq,3)-pos2(p,qq,3);
          dv=sqrt(dx*dx+dy*dy+dz*dz);
          Gpq=exp(1i*k1*dv)/(4*pi*dv); Fpq=(1i*k1-1/dv)*Gpq;
          for a1=1:3, for a2=1:3
            d3=f1(p,qq,a1,1)*f2(p,qq,a2,1)+f1(p,qq,a1,2)*f2(p,qq,a2,2)+f1(p,qq,a1,3)*f2(p,qq,a2,3);
            SLpq=Gpq*(d3-fp1(p,qq,a1)*fp2(p,qq,a2)/k1^2);
            v1=[f1(p,qq,a1,1),f1(p,qq,a1,2),f1(p,qq,a1,3)];
            v2=[f2(p,qq,a2,1),f2(p,qq,a2,2),f2(p,qq,a2,3)];
            u=[dx,dy,dz];
            cr=[v1(2)*u(3)-v1(3)*u(2), v1(3)*u(1)-v1(1)*u(3), v1(1)*u(2)-v1(2)*u(1)];
            tr=dot(cr,v2);
            ref(p,a1,a2)=ref(p,a1,a2)+w(p,qq)*SLpq;
            refDL(p,a1,a2)=refDL(p,a1,a2)-w(p,qq)*Fpq*tr/dv;
          end, end
        end
      end
      mSL=max(abs(data.SL(:)-ref(:))); mDL=max(abs(data.DL(:)-refDL(:)));
      rows{end+1}=struct('case',cc,'npair',npair,'modes',mmode,'status','OK','SL_shape',sz, ...
        'ref_SL_max_abs_diff',mSL,'ref_DL_max_abs_diff',mDL,'layout_candidate',strcmp(tag,'candidate')); %#ok<AGROW>
      fprintf('[062:p0] case=%d npair=%d modes=%s OK SL%s refSL=%.3g refDL=%.3g\n',cc,npair,mmode,sz,mSL,mDL);
    catch ME
      rows{end+1}=struct('case',cc,'npair',npair,'modes',mmode,'status','ERROR', ...
        'error',ME.message,'stack_top',ME.stack(1).name,'layout_candidate',strcmp(tag,'candidate')); %#ok<AGROW>
      fprintf('[062:p0] case=%d npair=%d modes=%s ERROR: %s @%s\n',cc,npair,mmode,ME.message,ME.stack(1).name);
    end
  end
end
allf={};
for ri0=1:numel(rows), allf=[allf,fieldnames(rows{ri0}).']; end %#ok<AGROW>
allf=unique(allf,'stable');
srows=struct();
for ri0=1:numel(rows)
  r0=rows{ri0};
  for j0=1:numel(allf)
    f0=allf{j0};
    if isfield(r0,f0), srows(ri0).(f0)=r0.(f0); else, srows(ri0).(f0)=NaN; end
  end
end
writetable(struct2table(srows),fullfile(outRoot,['layout_' tag '_v062.csv']));
end


