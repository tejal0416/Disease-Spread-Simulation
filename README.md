# Q28 – Disease Spread Simulation (Sequential + OpenMP, C++17)

Agent-based stochastic **SEIRD** epidemic model, calibrated from the provided JHU COVID-19 dataset,
with a sequential baseline and an OpenMP parallel version that produce **bit-identical** results.

## Folder layout

| Path | Content |
|---|---|
| `src/sim_common.hpp` | Model, counter-based RNG, argument parsing (shared by both programs) |
| `src/disease_seq.cpp` | Sequential implementation |
| `src/disease_omp.cpp` | OpenMP implementation |
| `scripts/calibrate.py` | Estimates beta, gamma, CFR from the dataset → `data/params_<country>.txt` |
| `scripts/verify.py` | Correctness tests (parallel == sequential, conservation, reproducibility) |
| `scripts/run_benchmarks.py` | All performance experiments, tables (CSV) and graphs (PNG) → `results/` |
| `scripts/make_report.py` | Builds `Project_Report.docx` from `results/` (roll numbers in the `TEAM` block must be filled in) |
| `data/` | Dataset files used (`time_series_covid_19_{confirmed,deaths,recovered}.csv`), calibrated parameters |
| `results/` | CSV tables, graphs, verification result, benchmark log |
| `LLM_USAGE_LOG.md`, `CONTRIBUTIONS.md` | Required project documents (LLM log: add your own prompts; contributions: add roll numbers) |

## Requirements

* g++ with C++17 and OpenMP (Linux/macOS with `brew install gcc`, Windows via MSYS2/WSL)
* Python 3 with `numpy pandas matplotlib python-docx` (`pip install numpy pandas matplotlib python-docx`)

## Build and test

```bash
make            # builds bin/disease_seq and bin/disease_omp
make test       # runs scripts/verify.py  -> "ALL TESTS PASSED"
```

## Run

```bash
./bin/disease_seq --N 1e6 --params data/params_India.txt --out run_seq.csv
./bin/disease_omp --N 1e6 --params data/params_India.txt --threads 8 --schedule static --out run_omp.csv
cmp run_seq.csv run_omp.csv && echo identical
```

Options (both programs): `--N` population, `--days`, `--kl` local contacts, `--kg` global contacts,
`--window` local neighbourhood half-width, `--beta --sigma --gamma --cfr --i0frac`, `--seed`,
`--params file`, `--out file.csv`. OpenMP only: `--threads`, `--schedule static|dynamic|guided`.

Each program prints a machine-readable line to stdout:
`RESULT,impl,N,contacts,days,threads,time_s,checksum,peakI,peakDay,attackRate`
and a human-readable summary to stderr.

## Reproduce the experiments and the report

```bash
python3 scripts/calibrate.py          # optional: regenerate parameters from the data
make bench                            # tests + experiments E1–E5, graphs -> results/ (a few minutes)
python3 scripts/make_report.py        # -> Project_Report.docx
```

**Measurement environment:** the results shipped in this package (`results/`) and quoted in the report were
measured on the team's laptop (Intel Core i5-1135G7, 4 physical cores / 8 logical CPUs, WSL2, g++ 15.2, `-O3`),
each value being the minimum of 3 runs. Absolute times and speedups depend on the machine, so re-run
`make bench && python3 scripts/make_report.py` on the machine you will present on if you want fresh numbers;
all tables, graphs and the analysis text are regenerated from the measurements.
Use `--maxn 1e7` for larger populations if your machine has enough time/memory.

## Parallel design in brief

* Data parallelism over agents; double-buffered synchronous daily update → no data races.
* Counter-based RNG (`rng(seed, day, agent, slot)`) → results independent of thread count / schedule.
* `reduction(+:...)` for the daily S/E/I/R/D totals; implicit barrier ends each simulated day.
* OpenMP chosen over MPI/CUDA because the whole state (N bytes) fits in shared memory and contacts are
  random-access (see report Section 5.3).
