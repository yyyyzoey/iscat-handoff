import csv, json, math, os
base=r"C:\Users\PC\Documents\Codex\2026-09-20\https-chatgpt-com-share-6aafd462-6e70\work\iscat_v0_4"
outdir=os.path.join(base,"v063_return","tables"); os.makedirs(outdir,exist_ok=True)
fz=json.load(open(os.path.join(base,"v061_return","r5_detection","threshold_freeze.json")))
tau=fz["tau_unrounded"]
src=os.path.join(base,"v062_return","tables","r6_per_trial_rechecked.csv")
rows=list(csv.DictReader(open(src,encoding="utf-8-sig")))
def parse_bool(v):
    if v in ("1",1): return 1
    if v in ("0",0): return 0
    if v in ("True","true"): return 1
    if v in ("False","false"): return 0
    raise ValueError("ambiguous boolean: %r"%(v,))
def parse_num(v):
    if v is None or v=="" or (isinstance(v,str) and v.lower() in ("nan","unknown")): return None
    return float(v)
out=[]
for r0 in rows:
    tc=parse_bool(r0["threshold_crossed"])
    scope=r0["fit_scope_label"]
    atb=parse_bool(r0["at_boundary"])
    rep=parse_bool(r0["diameter_reportable"])
    de=float(r0["D_err"]); ze=float(r0["z_err"]); pe=float(r0["pos_err_px"])
    out.append({"cond_id":r0["cond_id"],"trial":int(r0["trial"]),
      "D_true_nm":float(r0["D_true"]),"zf_true_nm":float(r0["zf_true"]),
      "x_true_nm":float(r0["x_true"]),"y_true_nm":float(r0["y_true"]),
      "D_fit_nm":float(r0["D_fit"]),"z_fit_nm":float(r0["z_fit"]),
      "x_fit_nm":float(r0["x_fit"]),"y_fit_nm":float(r0["y_fit"]),
      "D_err_nm":de,"z_err_nm":ze,"pos_err_px":pe,
      "T":float(r0["T"]),"threshold_crossed":tc,"fit_scope_label":scope,
      "numerically_at_boundary":atb,
      "boundary_distance_px":0.0,
      "diameter_reportable_v062_mark":rep,
      "quality_aware_detection":"UNKNOWN"})
fields=list(out[0].keys())
fixed=os.path.join(outdir,"r6_per_trial_quality_fixed.csv")
with open(fixed,"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for r0 in out: w.writerow({k:(r0[k]) for k in fields})
# re-load and assert (write-then-read-back check)
back=list(csv.DictReader(open(fixed,encoding="utf-8-sig")))
assert len(back)==len(out)==1000
for a,b in zip(out,back):
    assert int(b["threshold_crossed"])==a["threshold_crossed"]
    assert b["fit_scope_label"]==a["fit_scope_label"]
    assert float(b["D_err_nm"])==a["D_err_nm"]
# subsets per contract
def stats(subset):
    n=len(subset)
    if n==0: return {"n":0,"Bias_nm":None,"RMSE_nm":None,"Std_population_nm":None,"Std_sample_nm_ddof1":None,"max_abs_D_err_nm":None}
    e=[r0["D_err_nm"] for r0 in subset]
    bias=sum(e)/n; rmse=math.sqrt(sum(x*x for x in e)/n)
    sp=math.sqrt(sum((x-bias)**2 for x in e)/n)
    ss=math.sqrt(sum((x-bias)**2 for x in e)/(n-1)) if n>1 else None
    return {"n":n,"Bias_nm":bias,"RMSE_nm":rmse,"Std_population_nm":sp,
      "Std_sample_nm_ddof1":ss if ss is not None else None,
      "max_abs_D_err_nm":max(abs(x) for x in e)}
summary=[]
for cid in sorted(set(r0["cond_id"] for r0 in out)):
    g=[r0 for r0 in out if r0["cond_id"]==cid]
    tc=[r0 for r0 in g if r0["threshold_crossed"]==1]
    mark=[r0 for r0 in tc if r0["diameter_reportable_v062_mark"]==1]
    interior=[r0 for r0 in g if r0["fit_scope_label"]=="LOCAL_RESULT_UNCALIBRATED"]
    boundary=[r0 for r0 in g if r0["fit_scope_label"]=="BOUNDARY_CANDIDATE"]
    s_all=stats(g); s_tc=stats(tc); s_mark=stats(mark); s_int=stats(interior); s_bnd=stats(boundary)
    # SSE reconciliation
    sse_all=sum((r0["D_err_nm"])**2 for r0 in g)
    sse_parts=sum((r0["D_err_nm"])**2 for r0 in interior)+sum((r0["D_err_nm"])**2 for r0 in boundary)
    summary.append({"cond_id":cid,"n_total":len(g),
      "n_threshold_crossed":len(tc),"n_marked_reportable":len(mark),
      "n_interior_label":len(interior),"n_boundary_label":len(boundary),
      "all_legal":json.dumps(s_all),"marked_reportable":json.dumps(s_mark),
      "interior_label":json.dumps(s_int),"boundary_label":json.dumps(s_bnd),
      "sse_reconciliation_absdiff":repr(abs(sse_all-sse_parts))})
with open(os.path.join(outdir,"r6_quality_stratified_summary_fixed.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0].keys())); w.writeheader()
    for r0 in summary: w.writerow(r0)
for r0 in summary:
    print(r0["cond_id"],"n=%d tc=%d mark=%d int=%d bnd=%d sse_ok=%s"%(r0["n_total"],r0["n_threshold_crossed"],r0["n_marked_reportable"],r0["n_interior_label"],r0["n_boundary_label"],float(r0["sse_reconciliation_absdiff"])<1e-20))
print("A1 done")
