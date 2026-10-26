"""Independent read-only recheck of the V163 return evidence.

Sections
  A archive : CRC, member set == manifest rows + the manifest itself, 1:1
              re-hash of every member, manifest row order, on-disk identity.
  B ledger  : read-only SQLite re-derivation of caps, used counts, attempt
              states, phase reservations and per-task sealing hashes.
  C tests   : re-derivation of the 247-node / 741-report all-passed receipt.
  D probes  : pure-algebra recomputation of all 72 recorded identities from the
              raw stored arrays (frame_Y, frame_V, raw_J_fine,
              whitened_J_fine and the anchor model output C).

No import from tools/v163_bundle and no import of the packer. No model forward
call is made and the SQLite file is opened read-only. This script only
reconstructs structure and numbers; it is NOT physical or experimental
validation and it cannot certify a reportable particle diameter.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sqlite3
import zipfile
from pathlib import Path

import numpy as np

MEMBER_EXCLUDED = {"iscat_v163_return.zip", "manifest_sha256.csv", "archive_receipt.json"}
PROBE_GROUPS = ("100000_ANON_02", "100000_ANON_03", "100000_ANON_04")
ATOL = 1e-9
RTOL = 1e-8


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def err(actual, expected):
    """Absolute and relative deviation of two scalars/arrays."""
    a = np.asarray(actual, dtype=float)
    b = np.asarray(expected, dtype=float)
    if a.shape != b.shape:
        return float("inf"), float("inf")
    if a.size == 0:
        return 0.0, 0.0
    absolute = float(np.max(np.abs(a - b)))
    scale = float(np.max(np.abs(b))) or 1.0
    return absolute, absolute / scale


def section_archive(o: Path):
    zip_path = o / "iscat_v163_return.zip"
    manifest_path = o / "manifest_sha256.csv"
    out = {
        "zip_path": str(zip_path),
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": sha256_bytes(zip_path.read_bytes()),
        "manifest_path": str(manifest_path),
        "checks": {},
    }
    rows = list(csv.DictReader(io.StringIO(manifest_path.read_text(encoding="utf-8"))))
    out["manifest_rows"] = len(rows)
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        out["checks"]["crc_testzip_none"] = archive.testzip() is None
        out["checks"]["no_duplicate_members"] = len(names) == len(set(names))
        manifest_paths = {r["path"] for r in rows}
        out["checks"]["member_set_equals_manifest_plus_manifest_file"] = (
            set(names) == manifest_paths | {"manifest_sha256.csv"}
        )
        bad_hash = []
        bad_size = []
        for row in rows:
            data = archive.read(row["path"])
            if sha256_bytes(data) != row["sha256"]:
                bad_hash.append(row["path"])
            if len(data) != int(row["bytes"]):
                bad_size.append(row["path"])
        out["checks"]["every_member_matches_manifest_sha256"] = not bad_hash
        out["checks"]["every_member_matches_manifest_bytes"] = not bad_size
        out["checks"]["manifest_row_order_matches_member_order"] = [
            r["path"] for r in rows
        ] == [n for n in names if n != "manifest_sha256.csv"]
        out["manifest_sha256_mismatches"] = bad_hash
        out["manifest_bytes_mismatches"] = bad_size
        out["member_count"] = len(names)
        members = {n: archive.read(n) for n in names if n != "manifest_sha256.csv"}
    out["facts"] = {
        "zip_contains_self_digest": "iscat_v163_return.zip" in names,
        "zip_contains_archive_receipt": "archive_receipt.json" in names,
        "note": "a ZIP cannot carry its own digest, so the digest lives in the"
        " external archive_receipt.json next to it",
    }
    missing = [p for p, data in members.items() if not (o / p).is_file() or (o / p).read_bytes() != data]
    out["checks"]["every_member_matches_disk_bytes"] = not missing
    out["disk_member_mismatches"] = missing
    on_disk = {
        p.relative_to(o).as_posix()
        for p in o.rglob("*")
        if p.is_file() and p.relative_to(o).as_posix() not in MEMBER_EXCLUDED
    }
    out["external_disk_files_not_in_zip"] = sorted(on_disk - set(members))
    out["checks"]["no_member_missing_from_disk"] = not (set(members) - on_disk)
    return out


def section_ledger(o: Path):
    db = o / "logs" / "v163_budget.sqlite"
    out = {"db_path": str(db), "checks": {}, "tasks": []}
    out["checks"]["no_live_wal_or_journal"] = not any(
        Path(str(db) + suffix).exists() for suffix in ("-wal", "-journal")
    )
    uri = "file:" + db.as_posix() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as con:
        out["integrity_check"] = con.execute("PRAGMA integrity_check").fetchone()[0]
        out["checks"]["integrity_check_ok"] = out["integrity_check"] == "ok"
        metadata = json.loads(con.execute("select value from metadata where id=1").fetchone()[0])
        out["plan"] = metadata
        rows = list(
            con.execute("select id,phase,cap,used,state,result_path,result_sha from tasks order by phase,id")
        )
        attempts = list(con.execute("select task,state,theta from attempts"))
    out["checks"]["used_never_exceeds_cap"] = all(used <= cap for _, _, cap, used, *_ in rows)
    out["checks"]["plan_total_respected"] = sum(r[3] for r in rows) <= metadata["total"]
    per_phase_cap: dict[str, int] = {}
    for _, phase, cap, *_ in rows:
        per_phase_cap[phase] = per_phase_cap.get(phase, 0) + cap
    out["phase_reserved"] = per_phase_cap
    out["checks"]["phase_reservations_within_plan"] = all(
        reserved <= metadata["phases"].get(phase, 0) for phase, reserved in per_phase_cap.items()
    )
    attempt_states: dict[str, int] = {}
    per_task_attempts: dict[str, int] = {}
    for task, state, _ in attempts:
        attempt_states[state] = attempt_states.get(state, 0) + 1
        per_task_attempts[task] = per_task_attempts.get(task, 0) + 1
    out["attempt_states"] = attempt_states
    out["attempts_total"] = len(attempts)
    out["checks"]["all_attempts_returned"] = set(attempt_states) <= {"RETURNED"}
    out["checks"]["attempt_rows_equal_used_counts"] = all(
        per_task_attempts.get(task_id, 0) == used for task_id, _, _, used, *_ in rows
    )
    out["total_used"] = sum(r[3] for r in rows)
    seal_ok = True
    state_ok = True
    used_ok = True
    for task_id, _, cap, used, state, result_path, result_sha in rows:
        path = Path(result_path)
        digest = sha256_bytes(path.read_bytes()) if path.is_file() else None
        result = read_json(path) if path.is_file() else {}
        sealed = bool(digest) and digest == result_sha
        attempted = result.get("actual_model_forward_attempts")
        seal_ok &= sealed
        state_ok &= state == "FINISHED" and result.get("execution_state") == "FINISHED"
        used_ok &= attempted == used
        out["tasks"].append(
            {
                "task_id": task_id,
                "cap": cap,
                "used": used,
                "state": state,
                "result_sha256_matches_ledger": sealed,
                "recorded_forward_attempts": attempted,
            }
        )
    out["checks"]["task_result_sha256_matches_ledger"] = seal_ok
    out["checks"]["task_states_finished"] = state_ok
    out["checks"]["recorded_attempts_equal_used"] = used_ok
    return out


def section_tests(o: Path):
    base = o / "workstation_tests"
    receipt = read_json(base / "test_receipt.json")
    outcomes = read_json(base / "pytest_outcomes.json")
    reports = outcomes["reports"]
    nodeids = {r["nodeid"] for r in reports}
    out = {
        "command": receipt["command"],
        "pytest_version": receipt["pytest_version"],
        "returncode": receipt["returncode"],
        "scope": receipt["scope"],
        "real_F2c_calls": receipt["real_F2c_calls"],
        "collected": len(outcomes["collected"]),
        "unique_nodeids_in_reports": len(nodeids),
        "phase_reports": len(reports),
        "report_outcomes": {},
        "collection_errors": len(outcomes["collection_errors"]),
        "checks": {},
    }
    for r in reports:
        out["report_outcomes"][r["outcome"]] = out["report_outcomes"].get(r["outcome"], 0) + 1
    out["checks"]["receipt_returncode_zero"] = receipt["returncode"] == 0
    out["checks"]["files_unchanged_by_tests"] = receipt["files_unchanged"] is True
    out["checks"]["no_model_forward_during_tests"] = receipt["real_F2c_calls"] == 0
    out["checks"]["collected_equals_unique_nodeids"] = len(outcomes["collected"]) == len(nodeids)
    out["checks"]["all_phase_reports_passed"] = set(out["report_outcomes"]) == {"passed"}
    out["checks"]["no_collection_errors"] = not outcomes["collection_errors"]
    out["checks"]["pytest_exitstatus_zero"] = outcomes["exitstatus"] == 0
    out["checks"]["output_sha256_matches_receipt"] = (
        sha256_bytes((base / "test_output.txt").read_bytes()) == receipt["output_sha256"]
    )
    out["checks"]["outcomes_sha256_matches_receipt"] = (
        sha256_bytes((base / "pytest_outcomes.json").read_bytes()) == receipt["outcomes_sha256"]
    )
    out["checks"]["scope_disclaims_physical_validation"] = (
        "NOT_PHYSICAL_VALIDATION" in receipt["scope"]
    )
    return out


def section_probes(o: Path):
    anchors = read_json(o / "tasks" / "ANCHORS" / "result.json")["payload"]
    selected = anchors["selected"]
    out = {"groups": {}, "checks": {}, "identities": {}}
    maxima: dict[str, list[float]] = {}
    per_group_stats = {}
    reportable_null = True
    states = set()
    domain_ok = True
    for group in PROBE_GROUPS:
        context = read_json(o / "source_context" / "v156" / f"{group}.json")["diagnostic"]
        frame_v = np.asarray(context["frame_V"], dtype=float)
        frame_y = np.asarray(context["frame_Y"], dtype=float)
        raw_j = np.asarray(context["raw_J_fine"], dtype=float)
        whitened_j = np.asarray(context["whitened_J_fine"], dtype=float)
        variances = 1.0 / np.sum(1.0 / frame_v, axis=0)
        mean_y = (variances * np.sum(frame_y / frame_v, axis=0)).reshape(-1)
        variances = variances.reshape(-1)
        weights = variances ** -0.5
        anchor = selected[group]
        anchor_theta = np.asarray(anchor["theta"], dtype=float)
        anchor_c = np.asarray(anchor["C"], dtype=float).reshape(-1)
        residual0 = weights * (anchor_c - mean_y)
        group_rows = []
        for path in sorted((o / "probes" / group).glob("[0-9][0-9].json")):
            row = read_json(path)
            theta = np.asarray(row["theta"], dtype=float)
            c_now = np.asarray(row["C"], dtype=float).reshape(-1)
            z = weights * (c_now - anchor_c)
            direction = np.asarray(row["direction_nm_per_nm"], dtype=float)
            z_lin = whitened_j @ (theta - anchor_theta)
            dq = 2.0 * float(residual0 @ z) + float(z @ z)
            record = {
                "relative_linearization_error": float(row["relative_linearization_error"]),
                "image_distance_squared": float(row["image_distance_squared"]),
                "predicted_image_distance_squared": float(row["predicted_image_distance_squared"]),
                "observed_Q_change": float(row["observed_Q_change"]),
                "observed_Q_cross_term": float(row["observed_Q_cross_term"]),
                "Q_model_at_proposal": float(row["score_at_proposal"]["Q_model"]),
                "Q_joint_at_proposal": float(row["score_at_proposal"]["Q_joint"]),
                "K_at_proposal": float(row["score_at_proposal"]["K"]),
                "state": row["state"],
                "path": row["path"],
                "delta_D_nm": float(row["delta_D_nm"]),
            }
            pairs = {
                "whitened_jacobian_reconstruction": err(whitened_j, raw_j * weights.reshape(-1, 1)),
                "anchor_theta_matches_selected_anchor": err(anchor_theta, row["anchor_theta"]),
                "theta_equals_anchor_plus_step": err(
                    theta, anchor_theta + row["delta_D_nm"] * direction
                ),
                "image_distance_squared": err(float(z @ z), row["image_distance_squared"]),
                "predicted_image_distance_squared": err(
                    float(z_lin @ z_lin), row["predicted_image_distance_squared"]
                ),
                "relative_linearization_error": err(
                    float(np.linalg.norm(z - z_lin) / np.linalg.norm(z)),
                    row["relative_linearization_error"],
                ),
                "Q_cross_term": err(2.0 * float(residual0 @ z), row["observed_Q_cross_term"]),
                "Q_change_identity": err(dq, row["observed_Q_change"]),
                "Q_model_at_proposal": err(
                    float(np.sum((c_now - mean_y) ** 2 / variances)), row["score_at_proposal"]["Q_model"]
                ),
                "Q_joint_equals_Q_model_plus_K": err(
                    row["score_at_proposal"]["Q_model"] + row["score_at_proposal"]["K"],
                    row["score_at_proposal"]["Q_joint"],
                ),
            }
            for name, (absolute, relative) in pairs.items():
                maxima.setdefault(name, [0.0, 0.0])
                maxima[name][0] = max(maxima[name][0], absolute)
                maxima[name][1] = max(maxima[name][1], relative)
            group_rows.append(record)
            reportable_null &= row["reportable_D"] is None
            states.add(row["state"])
            domain_ok &= (
                30.0 <= theta[0] <= 200.0
                and 350.0 <= theta[1] <= 550.0
                and abs(theta[2]) <= 500.0
                and abs(theta[3]) <= 500.0
            )
        anchor_pairs = {
            "anchor_Q_model": err(
                float(np.sum((anchor_c - mean_y) ** 2 / variances)), anchor["Q_model"]
            ),
            "anchor_Q_joint": err(anchor["Q_model"] + anchor["K"], anchor["Q_joint"]),
        }
        for name, (absolute, relative) in anchor_pairs.items():
            maxima.setdefault(name, [0.0, 0.0])
            maxima[name][0] = max(maxima[name][0], absolute)
            maxima[name][1] = max(maxima[name][1], relative)
        errors = sorted(r["relative_linearization_error"] for r in group_rows)
        per_group_stats[group] = {
            "points": len(errors),
            "min": errors[0],
            "median": float(np.median(errors)),
            "max": errors[-1],
            "points_at_or_below_0.05_diagnostic": sum(1 for e in errors if e <= 0.05),
            "per_path": {},
        }
        for name in ("exact_height", "free_hxy", "height_sigma10"):
            values = sorted(r["relative_linearization_error"] for r in group_rows if r["path"] == name)
            per_group_stats[group]["per_path"][name] = {
                "points": len(values),
                "min": values[0],
                "median": float(np.median(values)),
                "max": values[-1],
            }
        out["groups"][group] = group_rows
    out["identities"] = {k: {"max_abs": v[0], "max_rel": v[1]} for k, v in maxima.items()}
    out["checks"]["every_identity_within_tolerance"] = all(
        absolute <= ATOL or relative <= RTOL for absolute, relative in maxima.values()
    )
    out["checks"]["72_points_evaluated"] = sum(
        len(g) for g in out["groups"].values()
    ) == 72 and states == {"EVALUATED"}
    out["checks"]["all_reportable_D_null"] = bool(reportable_null)
    out["checks"]["all_theta_inside_contract_domain"] = bool(domain_ok)
    out["per_group_stats"] = per_group_stats
    out["checks"]["diagnostic_points_counts_linearly"] = {
        g: per_group_stats[g]["points_at_or_below_0.05_diagnostic"] for g in PROBE_GROUPS
    }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    results = args.results.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "artifact": "iscat_v163_return.zip",
        "results_dir": str(results),
        "method": "independent raw re-parse and pure-algebra recomputation (no bundle/packer import)",
        "scope": "STRUCTURAL_AND_NUMERIC_RECONSTRUCTION_ONLY_NOT_SCIENTIFIC_ACCEPTANCE",
        "archive": section_archive(results),
        "ledger": section_ledger(results),
        "tests": section_tests(results),
        "probes": section_probes(results),
    }
    status = read_json(results / "status.json")
    verification = read_json(results / "verification.json")
    report["declared_status"] = {
        "execution_state": status.get("execution_state"),
        "all_reportable_D_null": status.get("all_reportable_D_null"),
        "EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED": status.get("EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED"),
        "global_uniqueness_certified": status.get("global_uniqueness_certified"),
        "verification_status": verification.get("status"),
        "verification_new_model_calls": verification.get("new_model_calls"),
    }
    report["checks_ok"] = (
        all(report["archive"]["checks"].values())
        and all(report["ledger"]["checks"].values())
        and all(report["tests"]["checks"].values())
        and all(report["probes"]["checks"].values())
        and status.get("all_reportable_D_null") is True
        and status.get("EXPERIMENTAL_ABSOLUTE_DIAMETER_VALIDATED") is False
        and verification.get("new_model_calls") == 0
    )
    failed = [
        f"{section}.{name}"
        for section in ("archive", "ledger", "tests", "probes")
        for name, ok in report[section]["checks"].items()
        if not ok
    ]
    report["failed_checks"] = failed
    report["verdict"] = (
        "MECHANICALLY_AND_NUMERICALLY_RECONSISTENT"
        if report["checks_ok"]
        else "RECONSTRUCTION_FAILED_SEE_FAILED_CHECKS"
    )
    (out_dir / "independent_recheck_v163.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# V163 independent recheck (read-only)",
        "",
        f"- verdict: `{report['verdict']}`",
        f"- zip: `{report['archive']['zip_path']}`",
        f"- zip sha256: `{report['archive']['zip_sha256']}` ({report['archive']['zip_bytes']} bytes)",
        f"- members: {report['archive']['member_count']}, manifest rows: {report['archive']['manifest_rows']}",
        f"- failed checks: {failed if failed else 'none'}",
        f"- scope: {report['scope']}",
        "",
        "## Ledger (read-only re-derivation)",
        "",
        f"- integrity_check: `{report['ledger']['integrity_check']}`",
        f"- total used: {report['ledger']['total_used']} / {report['ledger']['plan']['total']}",
        f"- reserved per phase: {report['ledger']['phase_reserved']}",
        f"- attempts by state: {report['ledger']['attempt_states']}",
        "",
        "| task | cap | used | state | sealed |",
        "|---|---:|---:|---|---|",
    ]
    for task in report["ledger"]["tasks"]:
        lines.append(
            f"| {task['task_id']} | {task['cap']} | {task['used']} | {task['state']} |"
            f" {task['result_sha256_matches_ledger']} |"
        )
    lines += [
        "",
        "## Tests",
        "",
        f"- collected nodes: {report['tests']['collected']}, phase reports: {report['tests']['phase_reports']}",
        f"- report outcomes: {report['tests']['report_outcomes']}",
        f"- collection errors: {report['tests']['collection_errors']}, scope: `{report['tests']['scope']}`",
        "",
        "## Probes",
        "",
    ]
    for group, stats in report["probes"]["per_group_stats"].items():
        lines.append(
            f"- {group}: n={stats['points']} min={stats['min']:.6g} median={stats['median']:.6g}"
            f" max={stats['max']:.6g} <=0.05(diagnostic)={stats['points_at_or_below_0.05_diagnostic']}"
        )
    lines += ["", "max reconstruction deviations:", ""]
    for name, dev in sorted(report["probes"]["identities"].items()):
        lines.append(f"- {name}: max_abs={dev['max_abs']:.3g} max_rel={dev['max_rel']:.3g}")
    lines += ["", f"declared status: `{json.dumps(report['declared_status'], sort_keys=True)}`", ""]
    (out_dir / "independent_recheck_v163.md").write_text("\n".join(lines), encoding="utf-8")
    print(report["verdict"])
    if failed:
        print("failed checks:", failed)
    return 0 if report["checks_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
