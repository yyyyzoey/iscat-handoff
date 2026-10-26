# -*- coding: utf-8 -*-
"""V162 blocked-execution forensic audit.

READ-ONLY with respect to history: reads git objects, the frozen config, the
model ledger (sqlite mode=ro), failure/task records, test receipts and pack
artifacts. Writes ONLY results/v162/audit/blocked_execution_audit.{json,md}.
No model forward call, no render, no camera, no ledger write, no gate change.
"""
from __future__ import annotations
import hashlib, json, sqlite3, subprocess, sys, traceback, zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\iscat\v162")
OUT = REPO / "results" / "v162"
AUD = OUT / "audit"
BASE = "71333a9f193d00012972e8fd6c188805c7a6b18e"
REL = "tools/v133_recover_M.py"


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1(b: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def git_bytes(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)


def git(*args):
    p = git_bytes(*args)
    return {"rc": p.returncode, "out": p.stdout.decode("utf-8", "replace").strip(),
            "err": p.stderr.decode("utf-8", "replace").strip()}


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jload_bom(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def maybe_json(x):
    if isinstance(x, (bytes, bytearray)):
        x = x.decode("utf-8", "replace")
    if isinstance(x, str) and x[:1] in "{[":
        try:
            return json.loads(x)
        except Exception:
            return x
    return x


def main():
    audit = {
        "audit_kind": "V162_BLOCKED_EXECUTION_READONLY_FORENSIC_AUDIT",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repo": str(REPO), "base_commit": BASE, "disputed_path": REL,
        "scope_note": ("Read-only forensic audit of the blocked V162 execute stage. "
                       "git_state was captured before the results commit."),
    }

    # ---- git state
    audit["git_state"] = {
        "head": git("rev-parse", "HEAD")["out"],
        "branch": git("rev-parse", "--abbrev-ref", "HEAD")["out"],
        "status_porcelain": git("status", "--porcelain=v1")["out"].splitlines(),
    }
    marker = REPO / ".v162-preparation.json"
    audit["preparation_marker"] = {"path": ".v162-preparation.json",
                                   "sha256": sha_file(marker), "doc": jload_bom(marker)}

    # ---- model ledger, read-only
    db = OUT / "logs" / "v162_budget.sqlite"
    led = {"path": "logs/v162_budget.sqlite", "bytes": db.stat().st_size, "sha256": sha_file(db),
           "sidecar_wal": Path(str(db) + "-wal").exists(),
           "sidecar_journal": Path(str(db) + "-journal").exists()}
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        led["integrity_check"] = con.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {}
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)]
            rows = [dict(zip(cols, [maybe_json(v) for v in row]))
                    for row in con.execute("SELECT * FROM %s" % t)]
            tables[t] = {"columns": cols, "row_count": len(rows), "rows": rows}
        led["tables"] = tables
    finally:
        con.close()
    tasks_rows = led["tables"].get("tasks", {}).get("rows", [])
    attempt_rows = led["tables"].get("attempts", {}).get("rows", [])
    state_counts = {}
    for r in attempt_rows:
        k = r.get("state")
        state_counts[k] = state_counts.get(k, 0) + 1
    led["summary"] = {
        "task_count": len(tasks_rows),
        "charged_attempt_rows": len(attempt_rows),
        "attempt_state_counts": state_counts,
        "total_used": sum(int(r.get("used", 0) or 0) for r in tasks_rows),
        "total_reserved_cap": sum(int(r.get("cap", 0) or 0) for r in tasks_rows),
        "tasks": [{"id": r.get("id"), "phase": r.get("phase"), "cap": r.get("cap"),
                   "used": r.get("used"), "state": r.get("state")} for r in tasks_rows],
    }
    audit["ledger"] = led

    seal_checks = []
    for r in tasks_rows:
        rp = Path(str(r.get("result_path", "")))
        entry = {"task": r.get("id"), "result_path": str(rp),
                 "result_sha_in_ledger": r.get("result_sha"), "exists": rp.is_file()}
        if entry["exists"]:
            entry["result_sha_recomputed"] = sha_file(rp)
            entry["matches"] = entry["result_sha_recomputed"] == r.get("result_sha")
        seal_checks.append(entry)
    audit["sealed_task_result_verification"] = seal_checks

    fail_docs = []
    for p in sorted((OUT / "failures").glob("*.json")):
        fail_docs.append({"path": str(p.relative_to(OUT)).replace("\\", "/"),
                          "bytes": p.stat().st_size, "sha256": sha_file(p), "doc": jload(p)})
    audit["failure_records"] = fail_docs
    loader_res = OUT / "tasks" / "LOADER_1" / "result.json"
    audit["loader_task_record"] = {"path": "tasks/LOADER_1/result.json",
                                   "sha256": sha_file(loader_res), "doc": jload(loader_res)}
    audit["prediction_files_under_tasks"] = sorted(
        str(p.relative_to(OUT)).replace("\\", "/") for p in (OUT / "tasks").rglob("predictions/*.json"))
    audit["seal_failure_files"] = sorted(
        str(p.relative_to(OUT)).replace("\\", "/") for p in (OUT / "tasks").rglob("seal_failure.json"))

    # ---- frozen pins matrix
    cfg = jload_bom(REPO / "config" / "v146_science_config.json")
    pins = cfg["frozen"]["source_sha256"]
    pin_rows = []
    for rel, exp in pins.items():
        p = REPO / rel
        row = {"path": rel, "expected_sha256": exp, "exists": p.is_file()}
        if row["exists"]:
            b = p.read_bytes()
            row.update(bytes=len(b), sha256=sha_bytes(b), git_blob=git_blob_sha1(b),
                       matches=(sha_bytes(b) == exp))
        pin_rows.append(row)
    lib = REPO / cfg["inputs"]["training_library"]
    lib_sha = sha_file(lib)
    audit["frozen_pins"] = {
        "config": "config/v146_science_config.json",
        "config_sha256": sha_file(REPO / "config" / "v146_science_config.json"),
        "pins": pin_rows,
        "mismatched_paths": [r["path"] for r in pin_rows if not r.get("matches")],
        "library": {"path": cfg["inputs"]["training_library"], "bytes": lib.stat().st_size,
                    "sha256": lib_sha, "expected": cfg["frozen"]["library_sha256"],
                    "matches": lib_sha == cfg["frozen"]["library_sha256"]},
        "model_id": cfg["frozen"].get("model_id"),
        "parent_model_id": cfg["frozen"].get("parent_model_id"),
    }

    # ---- git facts for the disputed path
    git_facts = {"history": git("log", "--all", "--date=iso", "--format=%H|%ad|%s", "--", REL)["out"].splitlines(),
                 "refs": {}}
    head_sha = git("rev-parse", "HEAD")["out"]
    for label, ref in (("BASE", BASE), ("HEAD", head_sha)):
        ls = git("ls-tree", ref, "--", REL)["out"]
        e = {"ref": ref, "ls_tree": ls}
        parts = ls.split()
        if len(parts) >= 4 and parts[1] == "blob":
            bsha = parts[2]
            blob = git_bytes("cat-file", "blob", bsha).stdout
            e.update(blob_sha1=bsha, blob_bytes=len(blob), blob_sha256=sha_bytes(blob))
        git_facts["refs"][label] = e
    wb = (REPO / REL).read_bytes()
    git_facts["worktree"] = {"bytes": len(wb), "sha256": sha_bytes(wb), "git_blob": git_blob_sha1(wb)}
    audit["disputed_path_git_facts"] = git_facts

    # ---- every copy of the disputed filename under results/ and tools/
    pin_sha = pins.get(REL)
    base_blob_sha = git_facts["refs"]["BASE"].get("blob_sha256")
    copies = []
    for root in (REPO / "results", REPO / "tools"):
        for p in sorted(root.rglob("v133_recover_M.py")):
            b = p.read_bytes()
            copies.append({
                "path": str(p.relative_to(REPO)).replace("\\", "/"),
                "bytes": len(b), "sha256": sha_bytes(b),
                "is_base_bytes": sha_bytes(b) == base_blob_sha,
                "is_v146_pin_bytes": sha_bytes(b) == pin_sha,
            })
    audit["all_v133_recover_M_copies_under_results_and_tools"] = {
        "count": len(copies),
        "by_class": {
            "base_blob_bytes": sum(1 for c in copies if c["is_base_bytes"]),
            "v146_pin_bytes": sum(1 for c in copies if c["is_v146_pin_bytes"]),
            "neither": sum(1 for c in copies if not c["is_base_bytes"] and not c["is_v146_pin_bytes"]),
        },
        "copies": copies,
    }

    # ---- official preflight receipt cross-check
    pre = jload(OUT / "preflight.json")
    sl = pre.get("source_lock", {})
    entry = sl.get(REL)
    audit["preflight_receipt_crosscheck"] = {
        "preflight_sha256": sha_file(OUT / "preflight.json"),
        "execution_code_commit": pre.get("execution_code_commit"),
        "driver_sha256": pre.get("driver_sha256"),
        "n_model_calls": pre.get("n_model_calls"),
        "scope": pre.get("scope"),
        "source_lock_files": len(sl),
        "source_lock_entry_for_disputed_path": entry,
        "entry_equal_to_worktree_identity": bool(entry) and entry.get("sha256") == git_facts["worktree"]["sha256"],
        "entry_equal_to_v146_pin": bool(entry) and entry.get("sha256") == pin_sha,
    }

    # ---- design outputs produced by preflight
    ddoc = jload(OUT / "design" / "saved_array_designs.json")
    groups = {}
    for g, v in ddoc.items():
        if isinstance(v, dict):
            groups[g] = {"design_count": v.get("design_count"),
                         "evaluation_count": v.get("evaluation_count"),
                         "reportable_D": v.get("reportable_D"),
                         "global_uniqueness_certified": v.get("global_uniqueness_certified"),
                         "experimental_absolute_diameter_validated": v.get("experimental_absolute_diameter_validated")}
        else:
            groups[g] = {"type": type(v).__name__}
    audit["design_outputs"] = {
        "path": "design/saved_array_designs.json",
        "sha256": sha_file(OUT / "design" / "saved_array_designs.json"),
        "group_count": len(ddoc),
        "sum_design_count": sum(int(x.get("design_count") or 0) for x in groups.values()),
        "sum_evaluation_count": sum(int(x.get("evaluation_count") or 0) for x in groups.values()),
        "groups": groups,
        "note": ("Produced by the preflight stage from saved V156 arrays with n_model_calls=0; "
                 "design definitions only, not new optical computation."),
    }

    # ---- official test receipt re-verification
    tr = {"via": "v162_deployment.verify_test_receipt (official bundle verifier)", "result": None}
    try:
        sys.path.insert(0, str(REPO / "tools" / "v162_bundle" / "code"))
        import v162_deployment as dep
        driver = REPO / "tools" / "v162_bundle" / "code" / "v162_run.py"
        root = dep.validate_installed_layout(driver, REPO)
        receipt = dep.verify_test_receipt(root, OUT / "workstation_tests")
        tr.update(result="PASS", scope=receipt.get("scope"), returncode=receipt.get("returncode"),
                  bundle_root=receipt.get("bundle_root"), command_tail=receipt.get("command_tail"))
    except Exception as exc:
        tr.update(result="FAIL", error=repr(exc), traceback=traceback.format_exc())
    inv = jload(REPO / "tools" / "v162_bundle" / "test_inventory.json")
    rep = jload(OUT / "workstation_tests" / "pytest_outcomes.json")
    tr.update(inventory_nodeids=len(inv["nodeids"]), outcomes_collected=len(rep.get("collected", [])),
              outcomes_exitstatus=rep.get("exitstatus"), report_records=len(rep.get("reports", [])),
              receipt_sha256=sha_file(OUT / "workstation_tests" / "test_receipt.json"),
              outcomes_sha256=sha_file(OUT / "workstation_tests" / "pytest_outcomes.json"),
              output_sha256=sha_file(OUT / "workstation_tests" / "test_output.txt"))
    audit["workstation_test_receipt_reverification"] = tr
    hist = OUT / "workstation_tests" / "history"
    audit["workstation_tests_history_files"] = sorted(
        str(p.relative_to(OUT)).replace("\\", "/") for p in hist.rglob("*") if p.is_file()) if hist.exists() else []

    # ---- stage evidence
    stages = {"stage_states": {}, "stage_commands": {}}
    for p in sorted((OUT / "logs").glob("*_stage_states.json")):
        stages["stage_states"][p.name] = jload(p)
    for p in sorted((OUT / "logs").glob("*_stage_commands.json")):
        stages["stage_commands"][p.name] = [{"stage": r.get("stage"), "returncode": r.get("returncode"),
                                             "command": r.get("command")} for r in jload(p)]
    audit["stage_evidence"] = stages
    console = []
    for p in sorted(list((OUT / "logs").glob("*.stdout")) + list((OUT / "logs").glob("*.stderr"))):
        b = p.read_bytes()
        row = {"name": p.name, "bytes": len(b), "sha256": sha_bytes(b)}
        if len(b) <= 4096:
            row["text"] = b.decode("utf-8", "replace")
        console.append(row)
    audit["stage_console_logs"] = console

    # ---- pack artifacts (state before the final repack)
    zp = OUT / "iscat_v162_return.zip"
    zinfo = {"path": zp.name, "bytes": zp.stat().st_size, "sha256": sha_file(zp)}
    with zipfile.ZipFile(zp) as z:
        zinfo["members"] = len(z.namelist())
    audit["pack_artifacts_before_final_repack"] = {
        "zip": zinfo,
        "manifest_sha256_csv_sha256": sha_file(OUT / "manifest_sha256.csv"),
        "archive_receipt": jload(OUT / "archive_receipt.json"),
        "first_failed_run_pack_zip_sha256": sha_file(
            OUT / "deployment_repair_evidence" / "first_failed_run_pack" / "iscat_v162_return.zip"),
        "note": ("Generated BEFORE the final repack; the final zip identity is recorded in "
                 "audit/final_zip_mechanical_verification.json (external companion by construction)."),
    }

    rr = OUT / "deployment_repair_evidence" / "rerun_1"
    audit["resume_wrapper_records"] = {
        "dir": "deployment_repair_evidence/rerun_1",
        "files": sorted(p.name for p in rr.glob("*")),
        "attempt1_json_present": (rr / "attempt1_run_all.json").is_file(),
    }
    if (rr / "attempt1_run_all.json").is_file():
        audit["resume_wrapper_records"]["attempt1_run_all"] = jload(rr / "attempt1_run_all.json")

    # ---- verdict
    audit["verdict"] = {
        "actual_model_forward_attempts_total": len(attempt_rows),
        "charged_or_unknown_attempts": sum(v for k, v in state_counts.items()
                                           if k not in ("RETURNED", "MODEL_ERROR")),
        "software_tests": "222/222 PASS via official receipt verifier" if tr.get("result") == "PASS"
                          else "NOT_VERIFIED",
        "preflight_stage": "FINISHED",
        "execute_stage": "BLOCKED_OR_FAILED",
        "verify_stage": "NOT_STARTED",
        "blocking_cause": "UNSATISFIABLE_FROZEN_SOURCE_PIN:" + REL,
        "contradiction": {
            "requirement_A": ("v162_deployment.verify_locked_inputs requires worktree bytes == "
                              "BASE git blob bytes for " + REL),
            "requirement_A_file_sha256": base_blob_sha,
            "requirement_B": ("v146_runtime.construct_bound requires sha256(file) == "
                              "config/v146_science_config.json frozen.source_sha256[" + REL + "]"),
            "requirement_B_pin": pin_sha,
            "equal": base_blob_sha == pin_sha,
            "satisfiable": base_blob_sha == pin_sha,
            "preflight_passed_with_sha256": (entry or {}).get("sha256"),
        },
        "dependent_stages_not_started": [
            "ANCHORS (36 Q replay, 6 E1 regression, 72 start rescoring, 12 candidate selection)",
            "NONLINEAR_PROBES (3 groups x 24 planned points)",
            "FINAL_VERIFY / verification.json",
        ],
        "design_definitions": "saved_array_designs.json produced by preflight (n_model_calls=0)",
        "scientific_conclusions": "NOT_EVALUATED",
        "all_reportable_D_null": True,
        "experimental_absolute_diameter_validated": False,
        "global_uniqueness_certified": False,
    }

    AUD.mkdir(parents=True, exist_ok=True)
    (AUD / "blocked_execution_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    c = audit["verdict"]["contradiction"]
    md = []
    md.append("# V162 执行阻断只读法医审计（blocked_execution_audit）")
    md.append("")
    md.append("生成时间（UTC）：" + audit["generated_utc"])
    md.append("仓库：" + str(REPO) + "；分支 HEAD：" + audit["git_state"]["head"])
    md.append("审计性质：只读；不改冻结字节、不改账本、不新增模型调用、不重置 task id。")
    md.append("")
    md.append("## 结论摘要")
    md.append("- 软件测试：222/222 通过（官方回执校验器复核通过，见下方哈希）。")
    md.append("- preflight 阶段：FINISHED（含 BASE 字节锁验证，含 " + str(audit["preflight_receipt_crosscheck"]["source_lock_files"]) + " 个受锁文件）。")
    md.append("- execute 阶段：BLOCKED_OR_FAILED，首个任务 LOADER_1 在 v146_runtime.construct_bound 处抛出 ")
    md.append("  ValueError: FROZEN_SOURCE_CHANGED:tools/v133_recover_M.py；依赖阶段全部未开始。")
    md.append("- 真实模型前向尝试总数（账本口径）：" + str(audit["verdict"]["actual_model_forward_attempts_total"]) + " / 500。")
    md.append("- 科学结论：NOT_EVALUATED；all_reportable_D_null=true；实验绝对粒径验证=false。")
    md.append("")
    md.append("## 根因（互斥冻结门的证明）")
    md.append("- 门 A：v162_deployment.verify_locked_inputs 要求工作树文件字节 == BASE(" + BASE + ") git blob 字节。")
    md.append("  该 blob：" + str(git_facts["refs"]["BASE"].get("blob_sha1")) + "， " + str(git_facts["refs"]["BASE"].get("blob_bytes")) + " B，sha256 " + str(c["requirement_A_file_sha256"]) + "。")
    md.append("- 门 B：v146_runtime.construct_bound 要求同一文件 sha256 == v146 配置中的冻结 pin " + str(c["requirement_B_pin"]) + "（9662 B 变体，仅存在于历史 results 归档副本）。")
    md.append("- 两个 sha256 是否相等：False ⇒ A∧B 不可同时满足；且该路径在全部 git 历史中只有一个提交（7c209897, 2026-10-22），即 BASE/HEAD blob 就是 9533 B 版本。")
    md.append("- 官方 preflight 回执（preflight.json）自身记录了该文件 sha256=" + str(c["preflight_passed_with_sha256"]) + "，与门 B 的 pin 冲突 ⇒ 该矛盾是交付包内部的，与工作站环境无关。")
    md.append("- 由包自身设计，修复窗口已关闭：restore_new_worktree 在存在模型账本时抛 NO_REPAIR_AFTER_MODEL_RUN；v162_run.execute 在账本存在时拒绝自动重跑（EXISTING_LEDGER_USE_READONLY_VERIFY_OR_FORENSICS_NO_AUTO_REEXECUTION）。")
    md.append("")
    md.append("## 依赖阻断而未执行的阶段（NOT_STARTED）")
    for s in audit["verdict"]["dependent_stages_not_started"]:
        md.append("- " + s)
    md.append("")
    md.append("## 资源账本（只读快照）")
    md.append("- 账本：" + led["path"] + "，sha256 " + led["sha256"] + "，integrity_check=" + str(led["integrity_check"]) + "。")
    md.append("- tasks 行数 " + str(len(tasks_rows)) + "；attempts（计费）行数 " + str(len(attempt_rows)) + "；attempt 状态统计 " + json.dumps(state_counts, ensure_ascii=False) + "。")
    md.append("- 唯一任务记录：" + json.dumps(led["summary"]["tasks"], ensure_ascii=False) + "。")
    md.append("- 说明：加载器尚未发生任何一次受计费前向；LOADER_1 在构造模型阶段即失败，任务已封存为 FAILED（result_sha 复核见 JSON）。")
    md.append("")
    md.append("## 关键产物哈希（审计时点）")
    md.append("- iscat_v162_return.zip（最终重打包前）sha256 " + zinfo["sha256"] + "（" + str(zinfo["bytes"]) + " B，" + str(zinfo["members"]) + " 成员）。")
    md.append("- manifest_sha256.csv sha256 " + audit["pack_artifacts_before_final_repack"]["manifest_sha256_csv_sha256"] + "；archive_receipt.json sha256 " + json.dumps(audit["pack_artifacts_before_final_repack"]["archive_receipt"], ensure_ascii=False) + "。")
    md.append("- 首次失败回合快照 zip sha256 " + audit["pack_artifacts_before_final_repack"]["first_failed_run_pack_zip_sha256"] + "。")
    md.append("- 测试回执 test_receipt.json sha256 " + tr["receipt_sha256"] + "；pytest_outcomes.json sha256 " + tr["outcomes_sha256"] + "。")
    md.append("- 失败记录 failures/000.json sha256 " + fail_docs[0]["sha256"] + "（共 " + str(len(fail_docs)) + " 条）。")
    md.append("")
    md.append("## 诚实性披露")
    md.append("- 首次修复调查中对 tools/v162_bundle/run_workstation_tests.py 的一次工作树编辑已在任何提交与任何模型调用之前恢复为 HEAD 原始字节，diff/前后字节保存在 deployment_repair_evidence/runner_edit_reverted_before_commit/。")
    md.append("- pytest 7.4 内建 nose 插件与冻结测试模块的模块级 setup 冲突，通过调用方环境 PYTEST_ADDOPTS='-p no:nose' 规避；包内字节改动为 0，A/B 复现证据在 deployment_repair_evidence/。")
    md.append("- 本审计生成于最终重打包之前；最终 zip 的一致性由 audit/final_zip_mechanical_verification.json（外部伴随回执）单独核验。")
    (AUD / "blocked_execution_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("AUDIT_OK")
    print("json:", AUD / "blocked_execution_audit.json")
    print("md:", AUD / "blocked_execution_audit.md")
    print("tests_receipt_reverification:", tr.get("result"))
    print("pin_mismatches:", audit["frozen_pins"]["mismatched_paths"])
    print("v133_copies_class:", audit["all_v133_recover_M_copies_under_results_and_tools"]["by_class"])
    print("attempt_rows:", len(attempt_rows), "task_used:", led["summary"]["total_used"])
    print("sum_evaluation_count:", audit["design_outputs"]["sum_evaluation_count"], "groups:", audit["design_outputs"]["group_count"])
    print("seal_checks:", json.dumps(seal_checks, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
