function run_v071_examples(outRoot)
% Package small K01 ROI examples (41x41 contrasts + evidence) for readable handoff.
numDir=fullfile(outRoot,'numeric');
ix=(33-20):(33+20);
names={'P_base','F_base','F_q7','F_bessel'};
E=struct();
for i=1:numel(names)
  cand=dir(fullfile(numDir,sprintf('side_K01_%s_*.mat',names{i})));
  S=load(fullfile(cand(1).folder,cand(1).name));
  evi=S.evi; evi.sol_sha256=S.evi.sol_sha256; 
  C=S.r.contrast(ix,ix);
  E.(['roi_' names{i}])=C;
  E.(['evi_' names{i}])=evi;
  E.(['cfg_' names{i}])=rmfield(S.r.cfg,{'camera','noise','scan','profile','paper_doi','source_commit','validation'});
end
E.probe_angle_deadswitch=load(fullfile(numDir,'probe_angle_deadswitch.mat')).pevi;
save(fullfile(numDir,'controlled_recovered_examples.mat'),'-struct','E','-v7.3');
fprintf('[071:examples] saved controlled_recovered_examples.mat\n');
end
