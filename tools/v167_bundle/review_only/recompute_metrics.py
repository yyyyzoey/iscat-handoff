import json,csv,pathlib,statistics,hashlib
out=pathlib.Path(__file__).parent
# Numeric transcription from the fixed GitHub estimates and unified task table.
# This is reviewer-only arithmetic, not estimator input or a new optical run.
D={
'ANON_01':{'truth':59.,'NO_HEIGHT':[45.249898467399106],'H1':[94.13205395576593,113.7177490983573,123.65892669431452],'H10':[54.19141232622576,88.72512186807795,106.96858578276624]},
'ANON_02':{'truth':101.,'NO_HEIGHT':[124.0907197448066],'H1':[104.32504401954736,104.48686070210665,104.10422471409653],'H10':[107.04248484328876,110.28643935792385,104.21612410929158]},
'ANON_03':{'truth':143.,'NO_HEIGHT':[134.84797622741573],'H1':[143.9824723576268,150.6737179132982,142.2349638626859],'H10':[134.71750214275426,138.34686820343953,133.58875126771497]},
'ANON_04':{'truth':181.,'NO_HEIGHT':[188.22477824843978],'H1':[181.275304830255,185.5181770499016,176.76524458375494],'H10':[187.17411524010774,190.6655246930207,178.8820469220334]}}
rows=[];group={}
for g,r in D.items():
 group[g]={}
 for method in ('NO_HEIGHT','H1','H10'):
  es=[abs(x-r['truth']) for x in r[method]]; group[g][method]=dict(candidate_D_nm=r[method],absolute_errors_nm=es,mean_absolute_error_nm=statistics.mean(es),median_absolute_error_nm=statistics.median(es))
  for rep,(d,e) in enumerate(zip(r[method],es)):
   partial=g=='ANON_01' and (method=='H1' or (method=='H10' and rep<2))
   tid=f'B100000_{g}_NO_HEIGHT' if method=='NO_HEIGHT' else f'B100000_{g}_{method}_R{rep:02d}'
   rows.append(dict(task_id=tid,group=g,design=method,replicate=None if method=='NO_HEIGHT' else rep,D_nm=d,abs_error_nm=e,state='PARTIAL_SEARCH' if partial else 'FINISHED',detected=g!='ANON_01'))
report={'scope':'INDEPENDENT_ARITHMETIC_REDERIVATION_FROM_PUBLISHED_VALUES_NOT_FULL_ARCHIVE_AUDIT','fixed_commit':'06b35cd4e0a47f7f49ef4b05401a07266f2c03b6','groups':group,
'all_four_available_candidates_descriptive_only':{m:statistics.mean(group[g][m]['mean_absolute_error_nm'] for g in D) for m in ('NO_HEIGHT','H1','H10')},
'detected_three_group_MAE':{m:statistics.mean(group[g][m]['mean_absolute_error_nm'] for g in D if g!='ANON_01') for m in ('NO_HEIGHT','H1','H10')},
'primary_all_four_complete_search_MAE':{'NO_HEIGHT':statistics.mean(group[g]['NO_HEIGHT']['mean_absolute_error_nm'] for g in D),'H1':None,'H10':None},
'partial_tasks':[r['task_id'] for r in rows if r['state']=='PARTIAL_SEARCH']}
with (out/'reviewer_candidate_metrics.json').open('w') as f:json.dump(report,f,indent=2,allow_nan=False)
with (out/'reviewer_candidate_values.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
print(json.dumps(report,indent=2))
