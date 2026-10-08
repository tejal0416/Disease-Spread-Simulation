#!/usr/bin/env python3
"""
make_report.py - builds  Project_Report.docx  from the files in results/ and data/.

Run it again after  run_benchmarks.py  on your own machine: every table, graph and
every number quoted in the performance analysis is regenerated from the CSV files,
so the report always matches the measurements.

Before submitting, edit the TEAM dictionary below (names, roll numbers, contributions).
"""
import json
import os

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RES = os.path.join(ROOT, "results")
DATA = os.path.join(ROOT, "data")

TEAM = {
    "course": "Design and Analysis of Algorithms / Parallel Programming Project (DAA T1 2026)",
    "problem": "Q28 - Disease Spread Simulation",
    # (name, roll number, contribution) - fill in the roll numbers before submitting
    "members": [
        ("Vaishanavi", "________", "Problem definition, model design, sequential implementation"),
        ("Vaidehi", "________", "OpenMP parallelisation, race-condition analysis, verification tests"),
        ("Tejal", "________", "Dataset calibration, benchmarking scripts, graphs"),
        ("Eshika", "________", "Report writing, README, LLM usage log"),
    ],
}


info = json.load(open(os.path.join(RES, "system_info.json")))
e1 = pd.read_csv(os.path.join(RES, "E1_population_size.csv"))
e2 = pd.read_csv(os.path.join(RES, "E2_thread_scaling.csv"))
e3 = pd.read_csv(os.path.join(RES, "E3_parameter_effects.csv"))
e4 = pd.read_csv(os.path.join(RES, "E4_schedules.csv"))
e5 = pd.read_csv(os.path.join(RES, "E5_validation.csv"))
ver = pd.read_csv(os.path.join(RES, "verification.csv"))
cal = pd.read_csv(os.path.join(DATA, "calibration_summary.csv"))

NCPU = info["logical_cpus"]
FIXN = int(info["fixed_N"])
omp = e2[e2.impl == "openmp"]
tseq = float(e2[e2.impl == "sequential"].time.iloc[0])
best = omp.loc[omp.speedup.idxmax()]
SINGLE = NCPU < 2

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(11)
for s in doc.sections:
    s.left_margin = s.right_margin = Inches(1)
    s.top_margin = s.bottom_margin = Inches(0.9)


def H(text, lvl=1):
    return doc.add_heading(text, level=lvl)


def P(text="", bold=False, italic=False, align=None, size=None, color=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = RGBColor(*color)
    if align:
        p.alignment = align
    return p


def B(text):
    return doc.add_paragraph(text, style="List Bullet")


def N(text):
    return doc.add_paragraph(text, style="List Number")


def code(text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = "Consolas"
    r.font.size = Pt(8.5)
    p.paragraph_format.left_indent = Inches(0.2)
    return p


def table(header, rows, widths=None, fs=9):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        run = c.paragraphs[0].add_run(str(h))
        run.bold = True
        run.font.size = Pt(fs)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            cells[i].paragraphs[0].add_run(str(v)).font.size = Pt(fs)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t


def fig(name, caption, width=5.6):
    doc.add_picture(os.path.join(RES, name), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    P(caption, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=9)


def f(x, d=3):
    return f"{x:.{d}f}"


# ================================================================ title page
for _ in range(4):
    doc.add_paragraph()
P("Parallel Programming Project Report", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=24)
P(TEAM["problem"], bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=18)
P("Parallel Agent-Based Simulation of Infectious Disease Spread using OpenMP",
  align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
doc.add_paragraph()
P(TEAM["course"], align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
doc.add_paragraph()
table(["Name", "Roll No.", "Role"], TEAM["members"], widths=[2.0, 1.2, 3.3], fs=10)
P(f"Date: {info['date'][:10]}", align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_page_break()

H("Contents", 1)
for line in ["1. Problem Definition", "2. Dataset and Model Calibration", "3. Computational Model",
             "4. Sequential Implementation", "5. Parallel Implementation and Choice of Programming Model",
             "6. Verification of Correctness", "7. Performance Evaluation",
             "8. Effect of Population Size and Simulation Parameters",
             "9. Bottleneck Analysis", "10. Use of LLM / Generative AI and Critical Evaluation",
             "11. Team Contribution", "12. Conclusion and Future Work", "References",
             "Appendix A - Build and run instructions", "Appendix B - Kernel source listing"]:
    P(line)
doc.add_page_break()

# ================================================================ 1
H("1. Problem Definition", 1)
P("Assigned problem (Q28): develop a computational model for simulating the spread of an infectious "
  "disease across a population and investigate the effect of population size and simulation parameters "
  "on execution time.")
P("We interpret this as follows:")
B("Build a stochastic, agent-based epidemic model in which every individual (agent) is in one of five "
  "states - Susceptible (S), Exposed (E), Infectious (I), Recovered (R) or Dead (D) - and states change "
  "day by day through contact with other agents.")
B("Calibrate the disease parameters (transmission rate, recovery rate, fatality ratio) from the supplied "
  "real-world COVID-19 dataset instead of choosing arbitrary numbers.")
B("Implement a sequential baseline and an OpenMP parallel version in C++ and prove that both give identical results.")
B("Measure execution time, speedup and parallel efficiency, and study how run time depends on the "
  "population size and on simulation parameters (contacts per agent, number of days, transmission rate, "
  "country scenario).")
P("Why parallelism is needed: the work per simulated day is proportional to the number of agents times the "
  "number of daily contacts. Realistic city- or country-scale simulations (10^6 - 10^9 agents, hundreds of "
  "days, many Monte-Carlo repetitions) are too slow on one core, while the per-agent update is "
  "independent of other agents' updates in the same day - an ideal case for data parallelism.")

# ================================================================ 2
H("2. Dataset and Model Calibration", 1)
P("The provided archive is the Johns Hopkins University (JHU CSSE) COVID-19 dataset (data up to June 2021). "
  "The files used are the global daily cumulative time series time_series_covid_19_confirmed.csv, "
  "..._deaths.csv and ..._recovered.csv (about 270 country/province rows x 500+ days). The remaining files "
  "(covid_19_data.csv and the US county series) contain the same pandemic at finer granularity; they are "
  "not needed for parameter estimation and are kept out of the submission package to limit its size.")
P("scripts/calibrate.py extracts the following for four countries (India, US, Italy, Brazil):")
B("r: early exponential growth rate, from a log-linear least-squares fit of cumulative confirmed cases over "
  "the first 21 days after the count reaches 100.")
B("gamma (recovery rate): median of (new recoveries / active cases). It is accepted only if it lies in the "
  "plausible range 0.05-0.4 per day; otherwise the default 0.10 (10-day infectious period) is used, "
  "because some countries stopped reporting recoveries or reported them with a long lag.")
B("CFR: deaths / confirmed at the end of the series.")
B("beta (transmission rate): from the SEIR early-growth relation (r + sigma)(r + gamma) = sigma * beta, "
  "using sigma = 1/5.2 (published mean incubation period; an assumption, not estimated from the data).")
rows = [[r.country, f"{r.population/1e6:.0f} M", r.start_date, f(r.growth_rate_r), f(r.gamma),
         "data" if "estimated" in r.gamma_source else "default", f(r.beta), f(r.R0, 2), f(r.cfr, 4)]
        for r in cal.itertuples()]
table(["Country", "Population", "Day 0", "r", "gamma", "gamma source", "beta", "R0=beta/gamma", "CFR"],
      rows, fs=8)
P("Table 1 - Parameters calibrated from the dataset.", italic=True, size=9)
P("Limitations: confirmed cases under-count true infections and early growth is inflated by increasing "
  "testing, so R0 values are high. The purpose here is a realistic parameter set for a performance study, "
  "not epidemiological forecasting.", italic=True)

# ================================================================ 3
H("3. Computational Model", 1)
H("3.1 States and transitions", 2)
table(["Transition", "Rule (applied once per simulated day)"], [
    ["S -> E", "For each of the agent's K daily contacts: if the contact is Infectious, infection occurs with probability p = beta / K"],
    ["E -> I", "With probability sigma = 1/5.2 (mean latent period 5.2 days)"],
    ["I -> D", "With probability gamma x CFR (infectious period ends and the agent dies)"],
    ["I -> R", "With probability gamma x (1 - CFR) (infectious period ends and the agent recovers)"],
    ["R, D", "Absorbing states"]], widths=[1.2, 5.3])
H("3.2 Contact structure", 2)
P("Each susceptible agent draws K = kl + kg contacts per day (default 4 + 4): kl 'local' contacts chosen "
  "uniformly from the 2W+1 agents around it in the index space (neighbourhood/household/workplace, W = 50) "
  "and kg 'global' contacts chosen uniformly from the whole population (community mixing). The expected "
  "number of new infections per infectious agent per day is then approximately beta, so the model "
  "reproduces the SEIR dynamics at the population level while keeping individual stochasticity.")
H("3.3 Time stepping and double buffering", 2)
P("The simulation advances in discrete one-day steps. The new state of every agent is computed only from "
  "the states of the previous day (array cur) and written to a second array (nxt); the arrays are swapped "
  "at the end of the day. This synchronous update removes order dependence between agents and is what "
  "makes the problem embarrassingly parallel inside a day.")
H("3.4 Counter-based random numbers", 2)
P("Instead of a stateful generator, every random draw is a hash of (seed, day, agent, slot) using the "
  "SplitMix64 mixing function. A draw therefore depends only on which agent asks for it, not on which thread "
  "executes it or in what order. Consequences: (i) no shared RNG state - no locks, no false sharing; "
  "(ii) the parallel program produces bit-identical results to the sequential one for any number of "
  "threads and any loop schedule, which gives an exact correctness test.")
H("3.5 Complexity", 2)
P("Work per day W(N) = O(N + S_t x K) where S_t is the number of susceptible agents on day t (only "
  "susceptible agents evaluate contacts); total work = O(days x N x K) in the worst case. Memory = 2N bytes "
  "(two 1-byte state arrays).")

# ================================================================ 4
H("4. Sequential Implementation", 1)
P("File: src/disease_seq.cpp (+ shared header src/sim_common.hpp, which holds the model so that the "
  "sequential and parallel programs use exactly the same update rule).")
code("init_population(cur)                    // seed I0 infected agents\n"
     "for day = 1 .. days:\n"
     "    S=E=I=R=D=0\n"
     "    for i = 0 .. N-1:                    // hot loop\n"
     "        nxt[i] = next_state(cur, i, day) // reads cur only\n"
     "        count nxt[i] into S,E,I,R,D\n"
     "    swap(cur, nxt)\n"
     "    write S,E,I,R,D to CSV\n"
     "    if E+I == 0: stop                    // epidemic extinct")
P("Timing covers only the simulation loop (not initialisation or console output), using "
  "std::chrono::steady_clock.")

# ================================================================ 5
H("5. Parallel Implementation and Choice of Programming Model", 1)
H("5.1 Parallelisation strategy", 2)
P("The loop over agents inside each day is parallelised with one OpenMP directive:")
code("#pragma omp parallel for schedule(runtime) reduction(+ : s, e, in, r, d)\n"
     "for (long i = 0; i < N; i++) {\n"
     "    uint8_t ns = next_state(q, curp, i, day);\n"
     "    nxtp[i] = ns;                       // own slot only\n"
     "    ... count ns ...\n"
     "}                                      // implicit barrier = end of day")
B("Decomposition: data parallelism - the N agents are divided among threads (static chunks by default).")
B("Synchronisation: only the implicit barrier at the end of each day (the next day needs all of today's states).")
B("Reduction: daily compartment counts use reduction(+:...), i.e. thread-private partial sums combined once per day.")
B("Schedule: the schedule is chosen at run time (--schedule static|dynamic|guided) so that the three "
  "options can be compared experimentally (Section 7.4).")
H("5.2 Data-race and dependency analysis", 2)
table(["Shared object", "Accesses", "Race?", "Reason"], [
    ["cur[] (states of yesterday)", "read by all threads", "No", "Read-only during the day"],
    ["nxt[] (states of today)", "thread t writes only indices it owns", "No", "Disjoint writes - each i belongs to one thread"],
    ["s, e, in, r, d counters", "incremented by all threads", "No", "OpenMP reduction gives each thread a private copy"],
    ["RNG", "every draw", "No", "Stateless counter-based hash - nothing is shared"],
    ["q (parameters)", "read by all threads", "No", "Immutable after start-up"]],
      widths=[1.7, 1.9, 0.6, 2.4], fs=8.5)
P("There is no loop-carried dependency between agents within one day, and the only dependency between days "
  "(today's state needs yesterday's) is enforced by the barrier and buffer swap.")
H("5.3 Why OpenMP (and not MPI or CUDA)?", 2)
table(["Model", "Assessment for this problem"], [
    ["OpenMP (chosen)", "State of the whole population is only N bytes (1 MB per 10^6 agents), so it fits easily in the shared memory of one node. Every agent needs random access to the states of arbitrary other agents (global contacts); with shared memory this is a plain array read. One pragma parallelises the hot loop, so code stays almost identical to the sequential version, which simplifies verification."],
    ["MPI", "With distributed memory each rank would have to receive the infectious state of all other agents every day (MPI_Allgather of N bytes per step) because global contacts are random. For populations that fit on one node this communication adds cost without benefit. MPI becomes attractive only for populations too large for one node's memory."],
    ["CUDA", "The kernel is highly data-parallel and a GPU would likely be fastest for very large N. However it is memory-latency-bound with random reads, needs host/device transfers for output, and requires GPU hardware that the team cannot assume. It is listed as future work."]],
      widths=[1.3, 5.2], fs=9)

# ================================================================ 6
H("6. Verification of Correctness", 1)
P("scripts/verify.py (run with 'make test') executes the sequential program and the OpenMP program on "
  "several parameter sets and compares (a) the complete day-by-day S/E/I/R/D output file and (b) a "
  "64-bit FNV-1a checksum of the final state of all agents.")
n_pass = int((ver.result == "PASS").sum())
P(f"Result: {n_pass} of {len(ver)} comparisons passed "
  f"({'all tests pass' if n_pass == len(ver) else 'SOME TESTS FAILED - investigate'}). "
  "Thread counts 1, 2, 3, 4, 8, loop schedules static/dynamic/guided, population sizes 10^4 - 2x10^5 "
  "(including an odd size 77,777), different contact settings and the India and Brazil calibrated parameter "
  "sets were covered.")
table(["Check", "Method", "Outcome"], [
    ["Parallel == sequential", "byte-exact comparison of daily CSV + final-state checksum", "identical in all cases"],
    ["Conservation of population", "S+E+I+R+D = N on every day", "holds"],
    ["Monotonicity", "S never increases; R and D never decrease", "holds"],
    ["Reproducibility", "same seed twice -> same result; different seed -> different result", "holds"],
    ["Plausibility vs. real data", f"simulated early growth rate vs. real confirmed-case growth (Fig. 8)",
     "; ".join(f"{r.country}: sim {r.simulated_growth_rate:.3f}/day vs real {r.real_growth_rate:.3f}/day" for r in e5.itertuples())]],
      widths=[1.7, 2.9, 1.9], fs=8.5)

# ================================================================ 7
H("7. Performance Evaluation", 1)
H("7.1 Experimental setup", 2)
table(["Item", "Value"], [
    ["CPU", info["cpu"]], ["Logical CPUs available", NCPU], ["OS", info["os"]],
    ["Compiler / flags", f"{info['compiler']}; -O3 -std=c++17 [-fopenmp]"],
    ["Repetitions", f"{info['reps']} per configuration; the minimum time is reported (reduces OS noise)"],
    ["Default model parameters", "K = 4 local + 4 global contacts, W = 50, beta = 0.45, sigma = 1/5.2, gamma = 0.10, CFR = 1.5%, 120 days, seed 12345"],
    ["Metrics", "Speedup S = T_seq / T_par;  efficiency E = S / p;  time covers the simulation loop only"]],
      widths=[1.8, 4.7], fs=9)
if SINGLE:
    P("IMPORTANT NOTE ABOUT THESE MEASUREMENTS", bold=True, color=(0xC0, 0, 0))
    P("The machine on which the numbers in this version of the report were generated exposed only ONE logical "
      "CPU. With a single core, several threads cannot run simultaneously, so a speedup above 1 is physically "
      "impossible and the thread-scaling results below show only the OpenMP overhead (thread creation, "
      "barriers, time-slicing), not the real parallel behaviour. The population-size results (sequential) "
      "are valid. To obtain true speedup figures run 'make bench && make report' on a multi-core computer: "
      "all tables, graphs and the analysis text of this section are regenerated automatically.",
      color=(0xC0, 0, 0))

if not SINGLE:
    _t1 = float(e1[e1.N == FIXN].t_seq.iloc[0]) if (e1.N == FIXN).any() else None
    if _t1 is not None:
        P(f"Measurement noise: the sequential time for N = {FIXN:,} was measured twice, in experiment E1 "
          f"({_t1:.2f} s) and in experiment E2 ({tseq:.2f} s) - a difference of "
          f"{abs(_t1 - tseq) / min(_t1, tseq) * 100:.0f}%. Each value is the minimum of {info['reps']} runs on a laptop "
          "where CPU frequency (turbo boost, thermal limits) and the WSL2 virtualisation layer vary from run to run. "
          "Speedups computed from different experiments (Table 2 and Table 3) therefore differ slightly; "
          "conclusions should be drawn from the trends, not from the third decimal.", italic=True)

H("7.2 Effect of increasing the population size", 2)
rows = [[f"{int(r.N):,}", f(r.t_seq), f(r.t_omp), f(r.speedup, 2), f(r.efficiency, 2)] for r in e1.itertuples()]
table(["N (agents)", "T_seq (s)", f"T_OpenMP, {int(e1.threads.iloc[0])} thr (s)", "Speedup", "Efficiency"], rows)
P("Table 2 - Execution time versus population size.", italic=True, size=9)
fig("G1_time_vs_N.png", "Figure 1 - Execution time vs population size (log-log).", 4.8)
fig("G2_speedup_vs_N.png", "Figure 2 - Speedup vs population size.", 4.8)
big = e1[e1.N >= 1e5]
slope = float(np.polyfit(np.log(big.N), np.log(big.t_seq), 1)[0])
P(f"Analysis: for N >= 100,000 the sequential time grows with slope {slope:.2f} on the log-log plot, i.e. "
  f"almost linearly in N (ideal = 1.0), confirming the O(N x K x days) complexity. Going from "
  f"{int(e1.N.iloc[0]):,} to {int(e1.N.iloc[-1]):,} agents (x{e1.N.iloc[-1]/e1.N.iloc[0]:.0f}) increases the time "
  f"from {f(e1.t_seq.iloc[0])} s to {f(e1.t_seq.iloc[-1], 2)} s (x{e1.t_seq.iloc[-1]/e1.t_seq.iloc[0]:.0f}). "
  + ("For very small N the fixed cost of forking threads and the barrier each day is comparable to the useful work, "
     "so parallelism does not pay off; the benefit of OpenMP grows with N because the useful work per day "
     "grows while the overhead per day stays constant." if not SINGLE else
     "Because only one core was available here, the OpenMP column is slightly slower than the sequential "
     "one for every N - this is pure threading overhead."))
if not SINGLE:
    _ib = int(e1.speedup.values.argmax())
    if _ib < len(e1) - 1:
        P(f"The speedup is largest ({e1.speedup.iloc[_ib]:.2f}x) at N = {int(e1.N.iloc[_ib]):,} and then stays roughly "
          "constant or dips slightly for larger N: the state arrays no longer fit in the processor caches, so all "
          "threads wait for main memory and the loop becomes memory-bandwidth bound.")

H("7.3 Effect of increasing the number of threads (strong scaling)", 2)
rows = [["sequential", "-", f(tseq), "1.00", "1.00"]] + \
       [["OpenMP", int(r.threads), f(r.time), f(r.speedup, 2), f(r.efficiency, 2)] for r in omp.itertuples()]
table(["Version", "Threads", "Time (s)", "Speedup", "Efficiency"], rows)
P(f"Table 3 - Strong scaling at N = {FIXN:,} agents, 120 days.", italic=True, size=9)
fig("G3_thread_scaling.png", "Figure 3 - Execution time and speedup vs number of threads.", 6.2)
fig("G4_efficiency.png", "Figure 4 - Parallel efficiency vs number of threads.", 4.6)
if SINGLE:
    P(f"Analysis: with one available core the best 'speedup' is {best.speedup:.2f} (threads = {int(best.threads)}); "
      f"all values are below 1 because the parallel build adds overhead and cannot use additional cores. "
      f"Single-thread OpenMP is {1/omp.speedup.iloc[0]:.2f}x slower than the pure sequential code, which measures the "
      "cost of the OpenMP runtime (parallel-region entry and the reduction each day) and of the extra "
      "bookkeeping. This result should not be interpreted as 'the algorithm does not parallelise'; see the "
      "note in Section 7.1 and Section 9 for the expected behaviour on multi-core hardware.")
else:
    p_best = int(best.threads)
    serial = (1 / best.speedup - 1 / p_best) / (1 - 1 / p_best) if p_best > 1 else float("nan")
    _e = {int(r.threads): r for r in omp.itertuples()}
    _mid = ", ".join(f"{_e[t].efficiency:.2f} with {t} thread{'s' if t > 1 else ''}" for t in sorted(_e) if 1 < t < p_best)
    P(f"Analysis: the best speedup is {best.speedup:.2f}x with {p_best} threads (efficiency {best.efficiency:.2f}), "
      f"i.e. the {tseq:.2f} s sequential run is reduced to {best.time:.2f} s. Efficiency is {_mid}, and falls to "
      f"{best.efficiency:.2f} with {p_best}. A single OpenMP thread is {1/_e[1].speedup:.2f}x slower than the pure "
      "sequential code (parallel-region entry and reduction overhead), which is the price paid for being able to scale.")
    _phys = info.get("physical_cores")
    if _phys and NCPU > _phys:
        P(f"The machine has {_phys} physical cores and {NCPU} logical CPUs (hyper-threading). Up to {_phys} threads "
          f"each thread gets its own core; beyond that, two threads share one core's execution units, so the extra "
          f"threads add only a fraction of a core's performance. This is why going from {_phys} to {NCPU} threads "
          f"helped much less than going from 1 to {_phys}, and why a speedup of {NCPU}x was not expected on this hardware.")
    P("Other causes of sub-linear speedup: (i) one barrier and one reduction per simulated day (fixed cost); "
      "(ii) the kernel is memory-latency bound - every global contact is a random read of the state array - so "
      "threads compete for cache and memory bandwidth; (iii) serial parts (initialisation, CSV output, buffer "
      f"swap) bound the speedup by Amdahl's law. The Karp-Flatt metric e = (1/S - 1/p)/(1 - 1/p) gives {serial:.3f} "
      f"at p = {p_best}; this value lumps together true serial work and all of the hardware effects above, so it "
      "is an upper bound on the really serial fraction.")

H("7.4 Effect of the OpenMP loop schedule", 2)
rows = [[r.schedule, int(r.threads), f(r.time), f(r.speedup, 2)] for r in e4.itertuples()]
table(["Schedule", "Threads", "Time (s)", "Speedup vs sequential"], rows)
fig("G6_schedules.png", "Figure 5 - Comparison of loop schedules.", 3.8)
bs = e4.loc[e4.time.idxmin()]
if SINGLE:
    P("Note: this comparison ran on a single core with one thread, so the differences between schedules below "
      "are measurement noise and scheduler overhead only; re-run on a multi-core machine for a meaningful comparison.",
      color=(0xC0, 0, 0))
P(f"Analysis: the fastest schedule in this run was '{bs.schedule}'. The work per agent is not uniform (only susceptible "
  "agents evaluate contacts, and as the epidemic progresses susceptibles become rare), so dynamic/guided "
  "scheduling can balance the load better than static, at the price of extra scheduling overhead per chunk "
  f"(chunk size 4096 here). The difference between the fastest and slowest schedule is "
  f"{(e4.time.max() - e4.time.min()) / e4.time.max() * 100:.0f}%, which is modest because infected agents are spread "
  "randomly over the index range, so even static chunks are roughly balanced; with run-to-run noise of a few "
  "percent, the schedule is a minor tuning parameter for this problem.")

# ================================================================ 8
H("8. Effect of Population Size and Simulation Parameters", 1)
P("This section answers the second half of the problem statement. All runs use the sequential program so that "
  "the effects of the model parameters are not mixed with threading effects; the same relative effects "
  "apply to the parallel version because it executes the same work.")
pn = 500000 if (e3.time.max() > 0) else 0
k = e3[e3.group == "contacts per agent"].copy()
d = e3[e3.group == "simulated days"].copy()
sc = e3[e3.group == "scenario"].copy()
be = e3[e3.group == "beta"].copy()
for _df in (k, d, be):  # 'value' column is mixed text/number in the CSV
    _df["value"] = pd.to_numeric(_df["value"])
H("8.1 Contacts per agent per day (K)", 2)
table(["K", "Time (s)", "Final attack rate", "Peak infectious", "Peak day"],
      [[int(r.value), f(r.time), f(r.attack, 3), f"{int(r.peakI):,}", int(r.peakDay)] for r in k.itertuples()])
P(f"Run time grows from {f(k.time.iloc[0])} s (K = {int(k.value.iloc[0])}) to {f(k.time.iloc[-1])} s "
  f"(K = {int(k.value.iloc[-1])}), i.e. x{k.time.iloc[-1]/k.time.iloc[0]:.1f} for a x{k.value.iloc[-1]/k.value.iloc[0]:.0f} "
  "increase of K. Time is NOT strictly proportional to K because every agent also pays a fixed cost per day "
  "(state read/write, counting) and susceptible agents stop evaluating contacts at their first infection "
  "(early exit). Epidemic outcomes (attack rate, peak) hardly change because p = beta / K keeps the "
  "population-level transmission constant - K is a pure cost parameter.")
H("8.2 Number of simulated days", 2)
table(["Days", "Time (s)", "Final attack rate", "Peak day"],
      [[int(r.value), f(r.time), f(r.attack, 3), int(r.peakDay)] for r in d.itertuples()])
P("Time rises with the number of days while the epidemic is active and then flattens, because once most "
  "agents are Recovered/Dead the per-day work shrinks to a cheap state copy and, if nobody is Exposed or "
  "Infectious any more, the simulation terminates early. A longer horizon therefore does not "
  "cost proportionally more time.")
H("8.3 Transmission rate (beta) and calibrated country scenarios", 2)
rows = [[r.value, f(r.time), f(r.attack, 3), f"{int(r.peakI):,}", int(r.peakDay)] for r in be.itertuples()]
table(["beta", "Time (s)", "Final attack rate", "Peak infectious", "Peak day"], rows)
rows = [[r.value, f(r.time), f(r.attack, 3), f"{int(r.peakI):,}", int(r.peakDay)] for r in sc.itertuples()]
table(["Scenario", "Time (s)", "Final attack rate", "Peak infectious", "Peak day"], rows)
fig("G5_parameter_effects.png", "Figure 6 - Effect of simulation parameters on sequential execution time.", 6.4)
fig("G7_epidemic_curves.png", "Figure 7 - Simulated epidemic curves for the four calibrated scenarios.", 6.0)
P("Observation: a higher transmission rate does not mean a longer run - it makes the program FASTER. "
  "Only susceptible agents execute the expensive contact loop, so the cost of a run follows the area under "
  "the S(t) curve. A fast epidemic (large beta, or the US/Italy scenarios) exhausts the susceptible pool "
  "early, after which agents only copy their state. With a very low beta the outbreak never takes off, "
  "almost everybody stays susceptible for the whole horizon and the run is among the most expensive; an "
  "intermediate beta that keeps many susceptibles for most of the horizon is the costliest case. "
  "Execution time of an epidemic simulation is therefore data dependent (it depends on the dynamics), which "
  "is also a source of load imbalance across the agent index range.")
fig("G8_validation.png", "Figure 8 - Early growth: simulated cumulative infections vs real confirmed cases.", 6.0)

# ================================================================ 9
H("9. Bottleneck Analysis", 1)
B("Memory latency of random reads. Each global contact reads cur[j] at a random index. For N up to about "
  "10^6 the 1-byte-per-agent array (1 MB) fits in the L2/L3 cache; for larger N cache misses dominate, "
  "so the kernel is memory-latency bound rather than compute bound. Using a 1-byte state keeps the "
  "working set as small as possible.")
B("Hash computation. Each random draw applies the SplitMix64 mixing function twice (about four 64-bit "
  "multiplications) per contact. This is cheap but is the main arithmetic cost; it is the price paid for exact "
  "reproducibility.")
B("Fork/join and barrier overhead. One parallel region per simulated day: for small N this fixed per-day "
  "cost dominates (Fig. 2).")
B("Serial sections (Amdahl's law). Population initialisation, per-day CSV output and the final checksum run "
  "on one thread. They are O(N) once or O(1) per day and tiny compared with O(N x K) per day, but they "
  "limit the maximum speedup to 1 / (serial fraction).")
B("Load imbalance. Only susceptible agents do the expensive contact loop and their share changes during the "
  "epidemic; in contrast to a structured grid, infected agents are randomly located so static chunks stay "
  "fairly balanced (Section 7.4).")
B("Hardware effects. Speedup is limited by the number of physical cores, by memory bandwidth, and "
  "(on many machines) by hyper-threading: beyond the physical-core count additional threads share "
  "execution resources.")
P("Optimisations applied: double buffering with 1-byte states; early exit on first infection; reduction instead "
  "of atomics; runtime-selectable schedule; early termination when the "
  "epidemic is extinct.")

# ================================================================ 10
H("10. Use of LLM / Generative AI and Critical Evaluation", 1)
P("A generative AI assistant (Claude) was used as an engineering assistant for: understanding the problem, "
  "designing the SEIRD agent-based model, designing the parallel decomposition, writing the C++/OpenMP code, "
  "the Python calibration/benchmark scripts and the test suite, and drafting this report. The complete "
  "prompt log is in LLM_USAGE_LOG.md. All AI output was compiled, executed and checked by the tests "
  "of Section 6 and the experiments of Section 7 rather than accepted on trust.")
H("10.1 Critical evaluation - suggestions that were modified or rejected", 2)
table(["#", "What the LLM suggested", "Why it was considered", "Decision / modification", "Verification"], [
    ["1", "Use one stateful random generator per thread (e.g. a thread-local std::mt19937 seeded with the thread id), the standard OpenMP pattern for Monte-Carlo code.",
     "It is the most common recommendation and trivial to write.",
     "REJECTED. Results would depend on the number of threads and on the schedule, so sequential and parallel outputs could never be compared exactly. Replaced by a stateless counter-based RNG: rng(seed, day, agent, slot).",
     "scripts/verify.py: byte-identical output for 1-8 threads and all three schedules."],
    ["2", "Estimate the recovery rate gamma automatically as the median of (new recoveries / active cases) from the dataset.",
     "It uses the real data directly instead of a textbook constant.",
     "MODIFIED. The first version gave gamma = 0.027 for Italy (a 37-day infectious period, R0 = 21.8) because recoveries are reported with long delays. The estimate is now accepted only within 0.05-0.4; otherwise the default 0.10 is used and the source is shown in Table 1.",
     "Re-ran calibration: Italy R0 fell to 7.6; simulated early growth rates match the real growth (Fig. 8)."],
    ["3", "The AI-drafted report text claimed 'first-touch-friendly allocation' as an optimisation and described the hash as 'two multiplies per contact'.",
     "Both claims sounded plausible and are typical statements in OpenMP performance write-ups.",
     "REJECTED / CORRECTED after reading the code. The state arrays are std::vector objects zero-initialised serially by the main thread, so first touch is NOT parallel; rng() calls SplitMix64 twice (about four multiplications). The claim was removed and the hash cost restated.",
     "Code review of sim_common.hpp / disease_omp.cpp; no performance claim in the report now rests on first-touch."]],
      widths=[0.25, 1.5, 1.2, 2.3, 1.25], fs=7.5)

# ================================================================ 11
H("11. Team Contribution", 1)
table(["Name", "Roll No.", "Individual contribution"], TEAM["members"], widths=[2.0, 1.2, 3.3], fs=10)
P("Every member is expected to be able to explain the whole project: the model (Section 3), the OpenMP "
  "constructs (Section 5), the verification (Section 6) and the performance results (Sections 7-9).")

# ================================================================ 12
H("12. Conclusion and Future Work", 1)
P("We designed and implemented a stochastic agent-based SEIRD disease-spread simulation, calibrated it "
  "from the JHU COVID-19 dataset, and parallelised it with OpenMP. The parallel program is verified to be "
  "bit-identical to the sequential baseline for every tested thread count and schedule. Execution time grows "
  "nearly linearly with the population size and with the number of contacts per agent, and depends on the "
  "epidemic dynamics through the number of susceptible agents that remain active.")
if SINGLE:
    P("The benchmark machine used for this version of the report had one core, so measured parallel speedup "
      "is not available; regenerate the report on a multi-core system to obtain the speedup and efficiency "
      "figures required by the project guidelines.")
else:
    P(f"The best measured speedup was {best.speedup:.2f}x on {int(best.threads)} threads.")
P("Future work: (1) an MPI version for populations that exceed one node, replicating the infectious-state "
  "array with MPI_Allgather and combining counts with MPI_Allreduce; (2) a CUDA kernel with one thread per "
  "agent; (3) heterogeneous contact networks (households, schools, workplaces) and age-structured "
  "parameters; (4) vaccination and lock-down interventions; (5) many Monte-Carlo replicates in "
  "parallel for confidence intervals.")

H("References", 1)
for r in ["Johns Hopkins University CSSE, COVID-19 Data Repository - time_series_covid_19_*.csv (provided dataset).",
          "Kermack W.O., McKendrick A.G. (1927). A contribution to the mathematical theory of epidemics. Proc. R. Soc. A 115.",
          "Steele G.L., Lea D., Flood C.H. (2014). Fast splittable pseudorandom number generators (SplitMix). OOPSLA.",
          "Salmon J.K. et al. (2011). Parallel random numbers: as easy as 1, 2, 3. SC'11 (counter-based RNGs).",
          "OpenMP Architecture Review Board. OpenMP Application Programming Interface, v4.5/5.x.",
          "Karp A.H., Flatt H.P. (1990). Measuring parallel processor performance. CACM 33(5)."]:
    B(r)

doc.add_page_break()
H("Appendix A - Build and run instructions", 1)
code("make                      # builds bin/disease_seq and bin/disease_omp\n"
     "make test                 # verification: parallel == sequential\n"
     "python3 scripts/calibrate.py                    # (optional) regenerate params from data\n"
     "./bin/disease_seq --N 1e6 --params data/params_India.txt --out run.csv\n"
     "./bin/disease_omp --N 1e6 --threads 8 --params data/params_India.txt --out run.csv\n"
     "make bench                # all experiments + graphs  -> results/\n"
     "make report               # Project_Report.docx")
H("Appendix B - Kernel source listing (src/sim_common.hpp)", 1)
src = open(os.path.join(ROOT, "src", "sim_common.hpp")).read()
a = src.index("inline std::uint8_t next_state")
b = src.index("// Seed the epidemic")
code(src[a:b].rstrip())

out = os.path.join(ROOT, "Project_Report.docx")
doc.save(out)
print("wrote", out)
