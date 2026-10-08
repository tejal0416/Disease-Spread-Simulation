#!/usr/bin/env python3
"""
verify.py - correctness tests for the OpenMP version.

Test 1: the daily S/E/I/R/D CSV and the final-state checksum of the OpenMP run
        must be IDENTICAL to the sequential run for several thread counts,
        schedules, population sizes and parameter sets.
Test 2: population is conserved every day (S+E+I+R+D == N) and R, D never decrease.
Test 3: reproducibility: same seed -> same result; different seed -> different result.
Writes results/verification.csv.
"""
import csv
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SEQ = os.path.join(ROOT, "bin", "disease_seq")
OMP = os.path.join(ROOT, "bin", "disease_omp")
TMP = os.path.join(ROOT, "results", "_tmp")
os.makedirs(TMP, exist_ok=True)


def run(exe, args, out):
    r = subprocess.run([exe, *args, "--out", out], capture_output=True, text=True, check=True)
    line = [l for l in r.stdout.splitlines() if l.startswith("RESULT")][0].split(",")
    return line[7]  # checksum


def read(path):
    with open(path) as f:
        return f.read()


def check_conservation(path, n):
    prev = None
    with open(path) as f:
        for row in csv.DictReader(f):
            v = [int(row[k]) for k in "SEIRD"]
            assert sum(v) == n, f"population not conserved: {row}"
            if prev:
                assert v[3] >= prev[3] and v[4] >= prev[4], "R/D decreased"
                assert v[0] <= prev[0], "S increased"
            prev = v


cases = [
    ("N=1e4 default", ["--N", "1e4"]),
    ("N=2e5 default", ["--N", "2e5"]),
    ("N=2e5 high kl", ["--N", "2e5", "--kl", "12", "--kg", "2", "--seed", "7"]),
    ("N=1e5 India params", ["--N", "1e5", "--params", os.path.join(ROOT, "data", "params_India.txt")]),
    ("N=1e5 Brazil params", ["--N", "1e5", "--params", os.path.join(ROOT, "data", "params_Brazil.txt"), "--days", "80"]),
    ("N=77777 odd size", ["--N", "77777", "--window", "30"]),
]
threads = [1, 2, 3, 4, 8]
schedules = ["static", "dynamic", "guided"]

rows, ok_all = [], True
for name, args in cases:
    seq_out = os.path.join(TMP, "seq.csv")
    cs_seq = run(SEQ, args, seq_out)
    n = int(float(args[args.index("--N") + 1]))
    check_conservation(seq_out, n)
    ref = read(seq_out)
    for t in threads:
        for sch in schedules if t in (2, 4) else ["static"]:
            out = os.path.join(TMP, "omp.csv")
            cs = run(OMP, [*args, "--threads", str(t), "--schedule", sch], out)
            same = (read(out) == ref) and (cs == cs_seq)
            ok_all &= same
            rows.append([name, t, sch, cs_seq, cs, "PASS" if same else "FAIL"])
            print(f"{name:22s} threads={t} sched={sch:8s} {'PASS' if same else 'FAIL'}")

# reproducibility / seed sensitivity
a = run(SEQ, ["--N", "5e4", "--seed", "1"], os.path.join(TMP, "a.csv"))
b = run(SEQ, ["--N", "5e4", "--seed", "1"], os.path.join(TMP, "b.csv"))
c = run(SEQ, ["--N", "5e4", "--seed", "2"], os.path.join(TMP, "c.csv"))
rep = (a == b) and (a != c)
ok_all &= rep
rows.append(["reproducibility (seed 1 twice, seed 2 differs)", 1, "-", a, c, "PASS" if rep else "FAIL"])
print("reproducibility:", "PASS" if rep else "FAIL")

with open(os.path.join(ROOT, "results", "verification.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["case", "threads", "schedule", "seq_checksum", "omp_checksum", "result"])
    w.writerows(rows)

for fn in os.listdir(TMP):
    os.remove(os.path.join(TMP, fn))
os.rmdir(TMP)
print("\nALL TESTS PASSED" if ok_all else "\nSOME TESTS FAILED")
sys.exit(0 if ok_all else 1)
