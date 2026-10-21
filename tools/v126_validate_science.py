"""V126 science validator: replay physics and blind inversion FROM the ZIP."""
import argparse, csv, hashlib, io, json, os, sys, tempfile, zipfile
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v126_forward_model as fm
import v126_invert_particle as vin

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default="results/v126")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    zip_path = os.path.join(args.out, "iscat_v126_return.zip")
    checks = []
    def add(name, ok, detail=""):
        checks.append(dict(check=name, passed=bool(ok), detail=str(detail)))
        print(("PASS" if ok else "FAIL"), name, detail[:90])
    with zipfile.ZipFile(zip_path) as z:
        add("zip_crc", z.testzip() is None)
        names = z.namelist()
        add("members_unique", len(names) == len(set(names)), f"{len(names)} members")
        man = {r["member"]: r["sha256"] for r in
               csv.DictReader(io.TextIOWrapper(z.open("manifest_sha256.csv"), encoding="utf-8"))}
        bad = [m for m, s in man.items() if hashlib.sha256(z.read(m)).hexdigest() != s]
        add("manifest_sha256_all_match", not bad, f"{len(man)} checked, bad={bad}")
        with tempfile.TemporaryDirectory() as td:
            z.extract("library/v126_Dh_train_fields.h5", td)
            h5p = os.path.join(td, "library", "v126_Dh_train_fields.h5")
            with h5py.File(h5p, "r") as h:
                for node, expect_new in (("D100_h450", False), ("D160_h425", True)):
                    if node not in h:
                        add(f"replay_{node}", False, "missing"); continue
                    g = h[node]
                    Eref, Esca = g["Eref"][()], g["Esca"][()]
                    I0 = fm._pixel_mean(np.sum(np.abs(Eref) ** 2, 2), 5)
                    It = fm._pixel_mean(np.sum(np.abs(Eref + Esca) ** 2, 2), 5)
                    Crep = (It - I0) / I0
                    err = float(np.max(np.abs(Crep - g["C"][()])))
                    add(f"replay_er_es_to_C_{node}", err < 1e-12, f"err={err:.3g} new_node={expect_new}")
            z.extract("validation/new_holdout_images.h5", td)
            lib = fm.CanonicalModel(h5p)
            with h5py.File(os.path.join(td, "validation", "new_holdout_images.h5"), "r") as h:
                Cobs = h["J03"]["at_offset/C"][()][2:15, 2:15]
                best = vin.fit_joint(Cobs, lib, "I1",
                                     scan_offsets=((0, 0), (56, -84), (-112, 56), (112, 112), (-84, -84)))
                shipped = list(csv.DictReader(io.TextIOWrapper(
                    z.open("validation/holdout_per_particle.csv"), encoding="utf-8")))
                ref = next(r0 for r0 in shipped if r0["case"] == "J03")
                dD = abs(best["theta"][0] - float(ref["D_est_nm"]))
                add("replay_blind_inversion_J03", dD < 1.0,
                    f"checker D={best['theta'][0]:.6f} shipped={ref['D_est_nm']} diff={dD:.3g} (tolerance 1nm for optimizer restart variance)")
            lib.close()
    receipt = dict(schema="iscat126.science_validation.1",
                   verdict="PASS" if all(c["passed"] for c in checks) else "FAIL", checks=checks)
    out = os.path.join(os.path.dirname(os.path.abspath(args.out)), "v126_science_validation.json")
    json.dump(receipt, open(out, "w", encoding="utf-8"), indent=1)
    print("verdict:", receipt["verdict"], "->", out)

if __name__ == "__main__":
    main()
