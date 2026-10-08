#!/usr/bin/env python3
"""
run_benchmarks.py - performance experiments + graphs for the report.

Experiments (all results -> results/*.csv, graphs -> results/*.png):
  E1  execution time vs population size        (sequential and OpenMP)
  E2  strong scaling: time/speedup/efficiency vs number of threads (fixed N)
  E3  effect of simulation parameters on sequential time
        (contacts per agent, number of days, country-calibrated scenarios)
  E4  OpenMP loop schedule comparison (static / dynamic / guided)
  E5  epidemic curves + validation against the real COVID-19 growth

Usage:  python3 scripts/run_benchmarks.py [--quick] [--reps 3] [--maxn 4e6]
Re-run this script on your own multi-core machine, then run make_report.py.
"""
import argparse
import csv
import json
import os
import platform
import subprocess
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SEQ = os.path.join(ROOT, "bin", "disease_seq")
OMP = os.path.join(ROOT, "bin", "disease_omp")
RES = os.path.join(ROOT, "results")
DATA = os.path.join(ROOT, "data")
os.makedirs(RES, exist_ok=True)

ap = argparse.ArgumentParser()
ap.add_argument("--quick", action="store_true", help="small sizes, 1 repetition (smoke test)")
ap.add_argument("--reps", type=int, default=3)
ap.add_argument("--maxn", type=float, default=4e6, help="largest population for E1")
ap.add_argument("--fixn", type=float, default=1e6, help="population for E2/E4")
args = ap.parse_args()
REPS = 1 if args.quick else args.reps
NCPU = os.cpu_count() or 1


def run(exe, extra, out=None):
    cmd = [exe, *[str(x) for x in extra]]
    if out:
        cmd += ["--out", out]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    f = [l for l in r.stdout.splitlines() if l.startswith("RESULT")][0].split(",")
    return dict(impl=f[1], N=int(f[2]), contacts=int(f[3]), days=int(f[4]), threads=int(f[5]),
                time=float(f[6]), checksum=f[7], peakI=int(f[8]), peakDay=int(f[9]), attack=float(f[10]))


def best(exe, extra):
    """min of REPS runs (the usual way to reduce OS noise) + all samples"""
    runs = [run(exe, extra) for _ in range(REPS)]
    b = min(runs, key=lambda r: r["time"])
    b["median"] = float(np.median([r["time"] for r in runs]))
    return b


# ---------------------------------------------------------------- system info
def cpu_model():
    try:
        for l in open("/proc/cpuinfo"):
            if l.startswith("model name"):
                return l.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


gxx = subprocess.run(["g++", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
def physical_cores():
    try:
        out = subprocess.run(["lscpu", "-p=CORE,SOCKET"], capture_output=True, text=True).stdout
        return len({l for l in out.splitlines() if l and not l.startswith("#")}) or None
    except Exception:
        return None


info = dict(date=time.strftime("%Y-%m-%d %H:%M"), cpu=cpu_model(), logical_cpus=NCPU, physical_cores=physical_cores(),
            os=platform.platform(), compiler=gxx, reps=REPS, fixed_N=args.fixn)
json.dump(info, open(os.path.join(RES, "system_info.json"), "w"), indent=2)
print("system:", info)

thread_list = [t for t in (1, 2, 4, 8, 16, 32) if t <= max(8, NCPU)]
if NCPU not in thread_list and NCPU <= 64:
    thread_list = sorted(thread_list + [NCPU])
TMAX = max(NCPU, 1)  # thread count used for "parallel" runs in E1/E3/E4
fixn = int(args.fixn)

# ------------------------------------------------------------------ E1: size
sizes = [1e4, 5e4, 1e5, 5e5, 1e6, 2e6, 4e6]
sizes = [s for s in sizes if s <= args.maxn]
if args.quick:
    sizes = [1e4, 1e5, 5e5]
rows = []
for n in sizes:
    s = best(SEQ, ["--N", int(n)])
    p = best(OMP, ["--N", int(n), "--threads", TMAX])
    assert s["checksum"] == p["checksum"], "checksum mismatch!"
    rows.append(dict(N=int(n), t_seq=s["time"], t_omp=p["time"], threads=TMAX,
                     speedup=s["time"] / p["time"], efficiency=s["time"] / p["time"] / TMAX,
                     attack=s["attack"], peakI=s["peakI"], peakDay=s["peakDay"]))
    print(f"E1 N={int(n):>8d}  seq={s['time']:.3f}s  omp({TMAX})={p['time']:.3f}s")
e1 = pd.DataFrame(rows)
e1.to_csv(os.path.join(RES, "E1_population_size.csv"), index=False)

# ------------------------------------------------------------ E2: threads
tseq = best(SEQ, ["--N", fixn])
rows = [dict(threads=0, impl="sequential", time=tseq["time"], speedup=1.0, efficiency=1.0)]
for t in thread_list:
    p = best(OMP, ["--N", fixn, "--threads", t])
    assert p["checksum"] == tseq["checksum"], "checksum mismatch!"
    sp = tseq["time"] / p["time"]
    rows.append(dict(threads=t, impl="openmp", time=p["time"], speedup=sp, efficiency=sp / t))
    print(f"E2 threads={t:>2d}  time={p['time']:.3f}s  speedup={sp:.2f}")
e2 = pd.DataFrame(rows)
e2.to_csv(os.path.join(RES, "E2_thread_scaling.csv"), index=False)

# ------------------------------------------------------------ E3: parameters
pn = int(5e5) if not args.quick else int(1e5)
rows = []
for k in (2, 4, 8, 16, 32):                       # contacts per agent per day
    r = best(SEQ, ["--N", pn, "--kl", k // 2, "--kg", k - k // 2])
    rows.append(dict(group="contacts per agent", value=k, time=r["time"], attack=r["attack"],
                     peakI=r["peakI"], peakDay=r["peakDay"]))
for d in (30, 60, 120, 240):                       # simulated days
    r = best(SEQ, ["--N", pn, "--days", d])
    rows.append(dict(group="simulated days", value=d, time=r["time"], attack=r["attack"],
                     peakI=r["peakI"], peakDay=r["peakDay"]))
for c in ("India", "US", "Italy", "Brazil"):       # calibrated scenarios
    r = best(SEQ, ["--N", pn, "--params", os.path.join(DATA, f"params_{c}.txt")])
    rows.append(dict(group="scenario", value=c, time=r["time"], attack=r["attack"],
                     peakI=r["peakI"], peakDay=r["peakDay"]))
for b in (0.15, 0.3, 0.6, 1.2):                    # transmission rate
    r = best(SEQ, ["--N", pn, "--beta", b])
    rows.append(dict(group="beta", value=b, time=r["time"], attack=r["attack"],
                     peakI=r["peakI"], peakDay=r["peakDay"]))
e3 = pd.DataFrame(rows)
e3.to_csv(os.path.join(RES, "E3_parameter_effects.csv"), index=False)
print(e3.to_string(index=False))

# ------------------------------------------------------------ E4: schedules
rows = []
for sch in ("static", "dynamic", "guided"):
    p = best(OMP, ["--N", fixn, "--threads", TMAX, "--schedule", sch])
    rows.append(dict(schedule=sch, threads=TMAX, time=p["time"], speedup=tseq["time"] / p["time"]))
    print(f"E4 {sch:8s} time={p['time']:.3f}s")
pd.DataFrame(rows).to_csv(os.path.join(RES, "E4_schedules.csv"), index=False)
e4 = pd.DataFrame(rows)

# ----------------------------------------- E5: curves + validation (graphs only)
os.makedirs(os.path.join(RES, "curves"), exist_ok=True)
curve_n = int(1e6) if not args.quick else int(1e5)
curves = {}
for c in ("India", "US", "Italy", "Brazil"):
    out = os.path.join(RES, "curves", f"curve_{c}.csv")
    run(SEQ, ["--N", curve_n, "--params", os.path.join(DATA, f"params_{c}.txt"), "--days", 150], out)
    curves[c] = pd.read_csv(out)

# ----------------------------------------------------------------- plotting
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True, "grid.alpha": 0.3})

# G1: time vs N
fig, ax = plt.subplots(figsize=(5.2, 3.6))
ax.loglog(e1.N, e1.t_seq, "o-", label="Sequential")
ax.loglog(e1.N, e1.t_omp, "s-", label=f"OpenMP ({TMAX} threads)")
ax.set_xlabel("Population size N (agents)"); ax.set_ylabel("Execution time (s)")
ax.set_title("Execution time vs population size"); ax.legend()
fig.tight_layout(); fig.savefig(os.path.join(RES, "G1_time_vs_N.png")); plt.close(fig)

# G2: speedup vs N
fig, ax = plt.subplots(figsize=(5.2, 3.6))
ax.semilogx(e1.N, e1.speedup, "o-", label="Measured speedup")
ax.axhline(TMAX, ls="--", c="gray", label=f"Ideal ({TMAX})")
ax.set_xlabel("Population size N"); ax.set_ylabel("Speedup  Tseq / Tomp")
ax.set_title(f"Speedup vs population size ({TMAX} threads)"); ax.legend()
fig.tight_layout(); fig.savefig(os.path.join(RES, "G2_speedup_vs_N.png")); plt.close(fig)

# G3: time + speedup vs threads
omp = e2[e2.impl == "openmp"]
fig, axs = plt.subplots(1, 2, figsize=(9, 3.6))
axs[0].plot(omp.threads, omp.time, "o-", label="OpenMP")
axs[0].axhline(tseq["time"], ls="--", c="gray", label="Sequential")
axs[0].set_xlabel("Threads"); axs[0].set_ylabel("Execution time (s)")
axs[0].set_title(f"Time vs threads (N={fixn:,})"); axs[0].legend()
axs[1].plot(omp.threads, omp.speedup, "o-", label="Measured")
axs[1].plot(omp.threads, omp.threads, "--", c="gray", label="Ideal (linear)")
axs[1].set_xlabel("Threads"); axs[1].set_ylabel("Speedup")
axs[1].set_title("Speedup vs threads"); axs[1].legend()
fig.tight_layout(); fig.savefig(os.path.join(RES, "G3_thread_scaling.png")); plt.close(fig)

# G4: efficiency
fig, ax = plt.subplots(figsize=(5.2, 3.6))
ax.plot(omp.threads, omp.efficiency, "o-")
ax.axhline(1.0, ls="--", c="gray")
ax.set_xlabel("Threads"); ax.set_ylabel("Parallel efficiency  S/p")
ax.set_title("Parallel efficiency vs threads"); ax.set_ylim(0, 1.15)
fig.tight_layout(); fig.savefig(os.path.join(RES, "G4_efficiency.png")); plt.close(fig)

# G5: parameter effects
fig, axs = plt.subplots(1, 4, figsize=(13, 3.3))
for ax, g, xl in zip(axs, ("contacts per agent", "simulated days", "scenario", "beta"),
                     ("Contacts per agent per day", "Simulated days", "Calibrated scenario", "beta")):
    d = e3[e3.group == g]
    ax.bar(d.value.astype(str), d.time, color="#4c72b0")
    ax.set_xlabel(xl); ax.set_ylabel("Sequential time (s)"); ax.set_title(f"N={pn:,}")
fig.tight_layout(); fig.savefig(os.path.join(RES, "G5_parameter_effects.png")); plt.close(fig)

# G6: schedules
fig, ax = plt.subplots(figsize=(4.6, 3.4))
ax.bar(e4.schedule, e4.time, color=["#4c72b0", "#dd8452", "#55a868"])
ax.set_ylabel("Execution time (s)"); ax.set_title(f"Loop schedule ({TMAX} threads, N={fixn:,})")
fig.tight_layout(); fig.savefig(os.path.join(RES, "G6_schedules.png")); plt.close(fig)

# G7: epidemic curves
fig, axs = plt.subplots(2, 2, figsize=(9, 6), sharex=True)
for ax, (c, df) in zip(axs.flat, curves.items()):
    for comp, col in zip("SEIRD", ("#4c72b0", "#dd8452", "#c44e52", "#55a868", "#333333")):
        ax.plot(df.day, df[comp] / curve_n, label=comp, color=col)
    ax.set_title(f"{c} parameters (N={curve_n:,})"); ax.set_ylabel("Fraction of population")
axs[0, 0].legend(ncol=5, fontsize=8); axs[1, 0].set_xlabel("Day"); axs[1, 1].set_xlabel("Day")
fig.tight_layout(); fig.savefig(os.path.join(RES, "G7_epidemic_curves.png")); plt.close(fig)

# G8: validation vs real data (growth multiples in the first 21 days)
fig, axs = plt.subplots(1, 2, figsize=(9, 3.6))
val = []
for ax, c in zip(axs, ("India", "Brazil")):
    real = pd.read_csv(os.path.join(DATA, f"real_{c}.csv"))
    sim = curves[c]
    sim_cum = curve_n - sim.S                                   # ever infected
    w = 40
    r_real = real.confirmed[:w] / real.confirmed[0]
    # sim: start the clock when cumulative infections are 10x the seed, to skip the latent transient
    start = int(np.argmax(sim_cum.values >= 10 * sim_cum.values[0]))
    r_sim = sim_cum[start:start + w].values / sim_cum.values[start]
    ax.semilogy(np.arange(w), r_real, "o-", ms=3, label="Real confirmed (JHU)")
    ax.semilogy(np.arange(len(r_sim)), r_sim, "s-", ms=3, label="Simulated cumulative infections")
    ax.set_xlabel("Days"); ax.set_ylabel("Growth multiple vs day 0"); ax.set_title(f"{c}: early growth"); ax.legend(fontsize=7)
    fit_real = np.polyfit(np.arange(21), np.log(real.confirmed[:21]), 1)[0]
    fit_sim = np.polyfit(np.arange(min(21, len(r_sim))), np.log(r_sim[:21]), 1)[0]
    val.append(dict(country=c, real_growth_rate=fit_real, simulated_growth_rate=fit_sim))
fig.tight_layout(); fig.savefig(os.path.join(RES, "G8_validation.png")); plt.close(fig)
pd.DataFrame(val).to_csv(os.path.join(RES, "E5_validation.csv"), index=False)
print(pd.DataFrame(val))
print("done -> results/")
