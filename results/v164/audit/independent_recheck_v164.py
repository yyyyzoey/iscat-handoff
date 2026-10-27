"""Independent, read-only re-derivation of the published V164 evidence.

Scope and honesty notes:
- stdlib only; imports no v164 bundle module and calls no F2c model.
- Re-derives archive mechanics, ledger accounting, and the stored arithmetic
  identities (fixed-D shift, S = 2*cost, best <= legal witness, common-pool
  monotonicity, reportable_D=None) directly from bytes on disk.
- Model-to-pixel binding was verified by the bundle's charged FINAL_VERIFY
  stage (27 attempts); it is NOT re-run here because that would require new
  model calls outside this round's budget.
- Nothing here establishes a global minimum, a calibrated uncertainty, an
  experimental absolute diameter, or any physical validation.
"""
from __future__ import annotations
import csv, hashlib, io, json, math, pathlib, sqlite3, zipfile

OUT = pathlib.Path(__file__).resolve().parents[1]
ZIP = OUT / "iscat_v164_return.zip"
PARENT_PIN = "06c54419c590b6ddadc50cd6117a7a54b2cf5ddf"
V163_ZIP_PIN = "9bc04fc03ea194ae4b1abaf61baa2b73a7d843679df67d71f3114ffb820bd8b7"
DESIGNS = ("free_hxy", "height_sigma10", "height_sigma1", "exact_height")
EXTERNAL_EXCLUDED = {"iscat_v164_return.zip", "manifest_sha256.csv", "archive_receipt.json"}

report: dict = {"receipt": "independent_recheck_v164", "out": str(OUT),
                "scope": "READONLY_REDERIVATION_OF_STORED_EVIDENCE_NO_MODEL_CALLS",
                "not_established_here": [
                    "global minimum status", "calibrated confidence intervals",
                    "experimental absolute diameter", "physical validation"]}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def section_archive() -> dict:
    out: dict = {"checks": {}}
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        out["members"] = len(names)
        out["checks"]["crc_ok"] = z.testzip() is None
        manifest = list(csv.DictReader(io.StringIO(z.read("manifest_sha256.csv").decode("utf-8"))))
        out["manifest_rows"] = len(manifest)
        out["checks"]["manifest_row_count"] = len(manifest) == len(names) - 1
        out["checks"]["member_set_matches_manifest"] = (
            set(names) == {r["path"] for r in manifest} | {"manifest_sha256.csv"})
        mismatches = []
        for r in manifest:
            raw = z.read(r["path"])
            if len(raw) != int(r["bytes"]) or sha256_bytes(raw) != r["sha256"]:
                mismatches.append(r["path"])
        out["manifest_mismatches"] = mismatches[:10]
        out["manifest_mismatch_count"] = len(mismatches)
        out["checks"]["full_manifest_rehash_ok"] = not mismatches
        members = {n: z.read(n) for n in names}
        disk_mismatch = [n for n, b in members.items()
                         if not (OUT / n).is_file() or (OUT / n).read_bytes() != b]
        out["checks"]["every_zip_member_matches_disk_bytes"] = not disk_mismatch
        out["disk_member_mismatches"] = disk_mismatch[:10]
        out["checks"]["failures_jsonl_recorded_zero_bytes"] = (
            "failures.jsonl" in members and len(members["failures.jsonl"]) == 0)
        raw_zip = ZIP.read_bytes()
    out["sha256"] = sha256_bytes(raw_zip)
    out["bytes"] = len(raw_zip)
    receipt = json.loads((OUT / "archive_receipt.json").read_text(encoding="utf-8"))
    out["archive_receipt"] = receipt
    out["checks"]["archive_receipt_matches_zip"] = (
        receipt["sha256"] == out["sha256"] and receipt["bytes"] == out["bytes"]
        and receipt["members"] == out["members"])
    on_disk = {p.relative_to(OUT).as_posix() for p in OUT.rglob("*") if p.is_file()}
    out["external_disk_files_not_in_zip"] = sorted(on_disk - set(members))
    allowed_external = EXTERNAL_EXCLUDED | {p for p in on_disk if p.startswith("audit/")}
    out["checks"]["external_files_limited_to_receipt_and_audit"] = (
        set(out["external_disk_files_not_in_zip"]) <= allowed_external)
    out["checks"]["no_zip_member_missing_on_disk"] = not (set(members) - on_disk)
    p = OUT / "source_context"
    out["source_context_files"] = sorted(x.name for x in p.glob("*.json"))
    out["checks"]["three_source_context_json_present"] = (
        len(out["source_context_files"]) == 3)
    out["checks"]["source_context_files_in_zip"] = all(
        f"source_context/{n}" in members for n in out["source_context_files"])
    return out


def section_ledger() -> dict:
    db = OUT / "logs" / "v164_budget.sqlite"
    out: dict = {"db": str(db), "checks": {}}
    out["checks"]["no_live_wal_or_journal"] = not any(
        pathlib.Path(str(db) + s).exists() for s in ("-wal", "-journal"))
    con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    try:
        out["integrity_check"] = con.execute("PRAGMA integrity_check").fetchone()[0]
        out["checks"]["integrity_check_ok"] = out["integrity_check"] == "ok"
        out["meta"] = json.loads(con.execute("select value from metadata where id=1").fetchone()[0])
        rows = con.execute("select id, phase, cap, used, state from tasks order by id").fetchall()
        out["tasks"] = [{"task": t, "phase": ph, "cap": c, "used": u, "state": s}
                        for t, ph, c, u, s in rows]
        out["attempt_count"] = con.execute("select count(*) from attempts").fetchone()[0]
        states = con.execute("select distinct state from attempts").fetchall()
        out["attempt_states"] = sorted(s for (s,) in states)
    finally:
        con.close()
    out["checks"]["all_tasks_finished"] = all(t["state"] == "FINISHED" for t in out["tasks"])
    out["checks"]["no_task_over_cap"] = all(t["used"] <= t["cap"] for t in out["tasks"])
    out["checks"]["profile_caps_are_400"] = all(
        t["cap"] == 400 for t in out["tasks"] if t["phase"] == "FIXED_D_DESIGN")
    out["checks"]["used_sum_equals_attempt_rows"] = (
        sum(t["used"] for t in out["tasks"]) == out["attempt_count"])
    out["checks"]["attempts_are_returned_only"] = out["attempt_states"] == ["RETURNED"]
    out["checks"]["total_within_plan_cap"] = sum(t["used"] for t in out["tasks"]) <= out["meta"]["total"]
    return out


def _theta_checks(name: str, theta, fixed_D: float, violations: list) -> None:
    if abs(float(theta[0]) - fixed_D) > 1e-9:
        violations.append(f"{name}: theta_D {theta[0]} != fixed_D {fixed_D}")


def section_profiles(ledger_used: dict) -> dict:
    profiles = json.loads((OUT / "profiles_all.json").read_text(encoding="utf-8"))
    v: list = []
    out: dict = {"count": len(profiles), "checks": {}, "violations_sample": v,
                 "totals": {}}
    if len(profiles) != 24:
        v.append(f"profile count {len(profiles)} != 24")
    keys = set()
    s_best = []
    for r in profiles:
        k = f"{r['group']}|{r['fixed_D_nm']}|{r['design']}"
        if k in keys:
            v.append(f"duplicate key {k}")
        keys.add(k)
        if r["design"] not in DESIGNS:
            v.append(f"{k}: unknown design")
        if r["search_state"] != "LOCAL_TERMINATIONS_ONLY":
            v.append(f"{k}: search_state {r['search_state']}")
        if r["reportable_D"] is not None:
            v.append(f"{k}: reportable_D not None")
        if r["interpretation"] != "ATTAINABLE_UPPER_BOUND_NOT_GLOBAL_MINIMUM_NOT_CI":
            v.append(f"{k}: row interpretation {r['interpretation']}")
        anchor = r["anchor_theta"]
        fixed_D = float(r["fixed_D_nm"])
        if abs(fixed_D - (float(anchor[0]) + float(r["delta_D_nm"]))) > 1e-9:
            v.append(f"{k}: fixed_D != anchor_D + delta")
        if r["delta_D_nm"] not in (-5.0, 5.0):
            v.append(f"{k}: delta {r['delta_D_nm']}")
        starts = r["starts"]
        if len(starts) != 2:
            v.append(f"{k}: {len(starts)} starts")
        for s in starts:
            if s["state"] != "OPTIMIZER_RETURNED" or not s["success"]:
                v.append(f"{k}: start {s['index']} state {s['state']}")
            if s["actual_calls"] > 200:
                v.append(f"{k}: start {s['index']} calls {s['actual_calls']} > 200")
            if abs(s["final_objective"] - 2.0 * s["scipy_cost"]) > max(1e-12, 1e-9 * abs(s["final_objective"])):
                v.append(f"{k}: start {s['index']} S != 2*cost")
            _theta_checks(f"{k}: start {s['index']} final", s["final_theta"], fixed_D, v)
        if sum(s["actual_calls"] for s in starts) != r["actual_new_calls"]:
            v.append(f"{k}: actual_new_calls != sum(start calls)")
        if ledger_used.get(f"PROFILE_{r['group']}_{'m5' if r['delta_D_nm'] < 0 else 'p5'}_{r['design']}") != r["actual_new_calls"]:
            v.append(f"{k}: ledger used != actual_new_calls")
        if r["actual_new_calls"] > 400:
            v.append(f"{k}: task calls {r['actual_new_calls']} > 400")
        m = min(s["final_objective"] for s in starts)
        if abs(m - r["best"]["design_distance_squared"]) > max(1e-12, 1e-9 * abs(m)):
            v.append(f"{k}: best != min(start final_objective)")
        best_S = r["best"]["design_distance_squared"]
        wit_S = r["linear_witness"]["design_distance_squared"]
        if best_S > wit_S + max(1e-12, 1e-10 * abs(wit_S)):
            v.append(f"{k}: best S {best_S} > witness S {wit_S}")
        _theta_checks(f"{k}: best", r["best"]["theta"], fixed_D, v)
        _theta_checks(f"{k}: witness", r["linear_witness"]["theta"], fixed_D, v)
        for tag, row in (("best", r["best"]), ("witness", r["linear_witness"])):
            if abs(row["design_distance_squared"]
                   - row["image_distance_squared"]
                   - row["hypothetical_auxiliary_distance_squared"]) > max(1e-12, 1e-9 * abs(row["design_distance_squared"])):
                v.append(f"{k}: {tag} design != image + aux")
            if row["auxiliary_is_independent_measurement"] is not False:
                v.append(f"{k}: {tag} aux flagged independent")
            if row["reportable_D"] is not None:
                v.append(f"{k}: {tag} reportable_D not None")
            if row["interpretation"] != "CONDITIONAL_NOISE_FREE_MEAN_SEPARATION_NOT_REAL_HEIGHT_DATA":
                v.append(f"{k}: {tag} interpretation {row['interpretation']}")
        if r["design"] == "free_hxy" and r["best"]["hypothetical_auxiliary_distance_squared"] != 0.0:
            v.append(f"{k}: free_hxy has auxiliary term")
        if r["design"] == "exact_height":
            if r["best"]["theta"][1] != anchor[1] or r["linear_witness"]["theta"][1] != anchor[1]:
                v.append(f"{k}: exact_height h not pinned")
            if any(s["final_theta"][1] != anchor[1] for s in starts):
                v.append(f"{k}: exact_height start h not pinned")
        s_best.append(best_S)
    out["checks"]["no_violations"] = not v
    out["violations_sample"] = v[:20]
    out["violation_count"] = len(v)
    out["totals"] = {"best_S_min": min(s_best), "best_S_max": max(s_best)}
    return out


def section_pools(profiles: list) -> dict:
    pools = json.loads((OUT / "pooled_all.json").read_text(encoding="utf-8"))
    v: list = []
    out: dict = {"count": len(pools), "checks": {}, "monotonicity": []}
    if len(pools) != 6:
        v.append(f"pool count {len(pools)} != 6")
    prof_map = {(r["group"], round(r["fixed_D_nm"], 9), r["design"]): r["best"]["design_distance_squared"]
                for r in profiles}
    seen = set()
    for q in pools:
        k = (q["group"], round(q["fixed_D_nm"], 9))
        if k in seen:
            v.append(f"duplicate pool {k}")
        seen.add(k)
        if q["own_optimizer_results_preserved"] is not True:
            v.append(f"{k}: own results not preserved")
        if q["reportable_D"] is not None:
            v.append(f"{k}: reportable_D not None")
        if q["interpretation"] != "ATTAINABLE_COMMON_POOL_UPPER_BOUNDS_NOT_GLOBAL_MINIMA":
            v.append(f"{k}: pool interpretation {q['interpretation']}")
        if set(q["common_pool_minima"]) != set(DESIGNS):
            v.append(f"{k}: pool designs {sorted(q['common_pool_minima'])}")
        vals = []
        for design in DESIGNS:
            row = q["common_pool_minima"][design]
            vals.append(row["design_distance_squared"])
            if row["reportable_D"] is not None:
                v.append(f"{k}/{design}: reportable_D not None")
            if row["auxiliary_is_independent_measurement"] is not False:
                v.append(f"{k}/{design}: aux flagged independent")
            if row["source_design"] not in DESIGNS:
                v.append(f"{k}/{design}: source_design {row['source_design']}")
            pk = (q["group"], round(q["fixed_D_nm"], 9), design)
            if pk not in prof_map:
                v.append(f"{k}/{design}: no same-key profile")
            elif abs(row["design_distance_squared"] - prof_map[pk]) > max(1e-12, 1e-10 * abs(prof_map[pk])):
                v.append(f"{k}/{design}: pool {row['design_distance_squared']} != profile best {prof_map[pk]}")
        mono = all(a <= b + max(1e-10, 1e-8 * abs(b)) for a, b in zip(vals, vals[1:]))
        out["monotonicity"].append({"group": q["group"], "fixed_D_nm": q["fixed_D_nm"],
                                    "values": vals, "monotone": mono})
        if not mono:
            v.append(f"{k}: monotonicity violated")
    groups = {g for g, _ in seen}
    out["checks"]["six_pools_two_deltas_three_groups"] = (
        len(seen) == 6 and len(groups) == 3
        and all(sum(1 for g, _ in seen if g == grp) == 2 for grp in groups))
    out["checks"]["no_violations"] = not v
    out["violations_sample"] = v[:20]
    out["violation_count"] = len(v)
    return out


def section_status(profiles: list, pools: list, ledger: dict) -> dict:
    status = json.loads((OUT / "status.json").read_text(encoding="utf-8"))
    verification = json.loads((OUT / "verification.json").read_text(encoding="utf-8"))
    v: list = []
    out: dict = {"checks": {}, "status": status, "verification_status": verification["status"]}
    if status["profiles"] != len(profiles):
        v.append("status.profiles mismatch")
    if status["common_pools"] != len(pools):
        v.append("status.common_pools mismatch")
    if status["execution_state"] not in ("FINISHED", "FINISHED_WITH_PARTIAL_SEARCH"):
        v.append(f"execution_state {status['execution_state']}")
    if status["partial_search_tasks"] != 0 or status["execution_state"] != "FINISHED":
        v.append("partial search recorded but state is not plain FINISHED-with-0")
    for flag in ("globally_certified_minima", "calibrated_confidence_intervals"):
        if status[flag] is not False:
            v.append(f"status.{flag} not False")
    if status["all_reportable_D_null"] is not True or verification["all_reportable_D_null"] is not True:
        v.append("all_reportable_D_null not True")
    if status["EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED"] is not False:
        v.append("EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED not False")
    if status["no_experimental_height_observation"] is not True:
        v.append("no_experimental_height_observation not True")
    if verification["new_model_calls"] != 0:
        v.append("verification.new_model_calls != 0")
    if verification["ledger"]["total_used"] != ledger["attempt_count"]:
        v.append("verification total_used != ledger attempts")
    sum_actual = sum(status["actual_calls"].values())
    if sum_actual != ledger["attempt_count"]:
        v.append("status.actual_calls sum != ledger attempts")
    if status["actual_calls"] != {t["task"]: t["used"] for t in ledger["tasks"]}:
        v.append("status.actual_calls != ledger per-task used")
    out["checks"]["no_violations"] = not v
    out["violations_sample"] = v[:20]
    out["violation_count"] = len(v)
    return out


def section_tests() -> dict:
    base = OUT / "workstation_tests"
    outcomes = json.loads((base / "pytest_outcomes.json").read_text(encoding="utf-8"))
    receipt = json.loads((base / "test_receipt.json").read_text(encoding="utf-8"))
    out: dict = {"checks": {}, "collected": len(outcomes["collected"]),
                 "reports": len(outcomes["reports"]), "exitstatus": outcomes["exitstatus"],
                 "receipt_returncode": receipt["returncode"], "scope": receipt["scope"]}
    v: list = []
    nodeids = outcomes["collected"]
    if len(nodeids) != len(set(nodeids)):
        v.append("duplicate collected nodeids")
    if outcomes["collection_errors"]:
        v.append("collection errors present")
    if outcomes["exitstatus"] != 0 or receipt["returncode"] != 0:
        v.append("nonzero pytest exit status")
    if not all(r["outcome"] == "passed" for r in outcomes["reports"]):
        v.append("non-passed phase report present")
    if receipt["real_F2c_calls"] != 0:
        v.append("test receipt counted F2c calls")
    inv_path = pathlib.Path(r"C:\iscat\v164\tools\v164_bundle\test_inventory.json")
    if inv_path.is_file():
        inv = json.loads(inv_path.read_text(encoding="utf-8"))
        out["inventory_count"] = inv["count"]
        if set(inv["nodeids"]) != set(nodeids):
            v.append("collected nodeids != bundle test inventory")
    else:
        out["inventory_count"] = None
        v.append("test inventory file not found for cross-check")
    if receipt["before"] != receipt["hashes"]:
        v.append("receipt before != hashes (files changed during tests)")
    for fname, key in (("pytest_outcomes.json", "outcomes_sha256"),
                       ("test_output.txt", "output_sha256")):
        disk = sha256_bytes((base / fname).read_bytes())
        if disk != receipt[key]:
            v.append(f"{fname} sha256 != receipt.{key}")
    txt = (base / "test_output.txt").read_text(encoding="utf-8", errors="replace")
    out["passed_line_present"] = "65 passed" in txt
    if not out["passed_line_present"]:
        v.append("'65 passed' not found in test_output.txt")
    out["checks"]["no_violations"] = not v
    out["violations_sample"] = v[:20]
    out["violation_count"] = len(v)
    return out


def section_provenance() -> dict:
    dep = json.loads((OUT / "deployment" / "receipt.json").read_text(encoding="utf-8"))
    pre = json.loads((OUT / "preflight.json").read_text(encoding="utf-8"))
    hist = json.loads((OUT / "history_audit.json").read_text(encoding="utf-8"))
    out: dict = {"checks": {}, "deployment": {
        "parent": dep["parent"], "code_commit": dep["code_commit"],
        "source_repo": dep["source_repo"], "worktree": dep["worktree"],
        "model_calls": dep["model_calls"], "restored": dep["restored"]},
        "preflight": {"parent": pre["parent"], "execution_code_commit": pre["execution_code_commit"],
                      "model_calls": pre["model_calls"],
                      "runtime_pins_all_match": pre["runtime_pins"]["all_match"]},
        "history_audit": {"archive": hist["archive"], "old_designs": hist["old_designs"],
                          "old_probes": hist["old_probes"], "tests": hist["tests"],
                          "scope": hist["scope"]}}
    v: list = []
    if dep["parent"] != PARENT_PIN or pre["parent"] != PARENT_PIN:
        v.append("parent commit does not match contract pin")
    if dep["code_commit"] != pre["execution_code_commit"]:
        v.append("deployment/preflight code commit mismatch")
    if not dep["code_commit"].startswith("d802b9e"):
        v.append(f"unexpected code commit {dep['code_commit']}")
    if dep["model_calls"] != 0 or pre["model_calls"] != 0:
        v.append("deployment/preflight counted model calls")
    if pre["runtime_pins"]["all_match"] is not True:
        v.append("preflight runtime pins not all matching")
    lock_keys = ("config/v124_model_and_user_inputs.json", "config/v125_effective_config.json",
                 "config/v125_science_config.json")
    if not all(dep["source_lock"][k]["sha256"] == pre["source_lock"][k]["sha256"] for k in lock_keys):
        v.append("deployment/preflight source lock mismatch")
    if hist["archive"]["sha256"] != V163_ZIP_PIN or hist["archive"]["bytes"] != 2235181:
        v.append("history audit V163 pin mismatch")
    if hist["archive"]["crc_ok"] is not True:
        v.append("history audit V163 CRC not ok")
    if hist["old_designs"] != 1224 or hist["old_probes"] != 72:
        v.append("history audit old design/probe counts")
    if hist["ledger"]["scope"] != "READONLY_STORED_EVIDENCE_NOT_NEW_MODEL_REPLAY":
        v.append("history audit ledger scope unexpected")
    v163_zip = pathlib.Path(r"C:\iscat\v163\results\v163\iscat_v163_return.zip")
    if v163_zip.is_file():
        raw = v163_zip.read_bytes()
        out["v163_zip_rehashed"] = {"sha256": sha256_bytes(raw), "bytes": len(raw),
                                    "path": str(v163_zip)}
        if out["v163_zip_rehashed"]["sha256"] != V163_ZIP_PIN:
            v.append("V163 zip re-hash does not match contract pin")
    else:
        out["v163_zip_rehashed"] = None
        v.append("V163 zip not found for independent re-hash")
    out["checks"]["no_violations"] = not v
    out["violations_sample"] = v[:20]
    out["violation_count"] = len(v)
    return out


def main() -> int:
    archive = section_archive()
    ledger = section_ledger()
    ledger_used = {t["task"]: t["used"] for t in ledger["tasks"]}
    profiles = json.loads((OUT / "profiles_all.json").read_text(encoding="utf-8"))
    pools_raw = json.loads((OUT / "pooled_all.json").read_text(encoding="utf-8"))
    prof_section = section_profiles(ledger_used)
    pools_section = section_pools(profiles)
    status_section = section_status(profiles, pools_raw, ledger)
    tests = section_tests()
    prov = section_provenance()
    report.update({"archive": archive, "ledger": ledger, "profiles": prof_section,
                   "pools": pools_section, "status": status_section, "tests": tests,
                   "provenance": prov})
    all_checks = {}
    for name, sec in (("archive", archive), ("ledger", ledger), ("profiles", prof_section),
                      ("pools", pools_section), ("status", status_section),
                      ("tests", tests), ("provenance", prov)):
        all_checks[name] = sec["checks"]
    report["checks"] = all_checks
    report["all_checks_pass"] = all(
        val for sec in all_checks.values() for val in sec.values())
    report["verdict"] = "RE-DERIVED_OK" if report["all_checks_pass"] else "MISMATCH_FOUND"
    report["totals"] = {"attempts": ledger["attempt_count"],
                        "tasks": len(ledger["tasks"]),
                        "profiles": len(profiles), "pools": len(pools_raw),
                        "tests_collected": tests["collected"],
                        "test_phase_reports": tests["reports"]}
    jpath = OUT / "audit" / "independent_recheck_v164.json"
    jpath.write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    lines = ["# V164 independent recheck receipt (external, post-pack)", "",
             f"- verdict: **{report['verdict']}**",
             f"- scope: `{report['scope']}`",
             f"- zip sha256: `{archive['sha256']}` ({archive['bytes']} bytes, {archive['members']} members)",
             f"- ledger: {ledger['attempt_count']} attempts, {len(ledger['tasks'])} tasks, integrity `{ledger['integrity_check']}`",
             f"- profiles: {prof_section['count']} (violations {prof_section['violation_count']})",
             f"- pools: {pools_section['count']} (violations {pools_section['violation_count']})",
             f"- status/verification violations: {status_section['violation_count']}",
             f"- tests: {tests['collected']} collected / {tests['reports']} phase reports, exit {tests['exitstatus']}",
             f"- provenance violations: {prov['violation_count']}",
             f"- V163 zip re-hashed: {bool(prov['v163_zip_rehashed'])}", "",
             "Not established here: " + "; ".join(report["not_established_here"]) + "."]
    (OUT / "audit" / "independent_recheck_v164.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "all_checks_pass": report["all_checks_pass"],
                      "totals": report["totals"]}, indent=1))
    for name, sec in all_checks.items():
        failed = [k for k, ok in sec.items() if not ok]
        print(f"{name}: {'ok' if not failed else 'FAILED ' + ','.join(failed)}")
    return 0 if report["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
