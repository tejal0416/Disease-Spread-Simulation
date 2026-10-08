# LLM Usage Log – Q28 Disease Spread Simulation

> **Instruction from the course PDF:** record the *actual* prompts your group used while developing the
> project. The entries below document how the AI assistant (Claude) was used to produce the first version
> of this package. **Add your own prompts and verification notes** (rows 6 onward) as you read, run,
> modify and extend the project – you must be able to explain each row in the viva.

| Sr. | Purpose | Prompt used | How the response was used | Modification / verification |
|---|---|---|---|---|
| 1 | Project generation | "i have provided you my dataset my problem statement and instruction of my project pdf which my teacher provided me build me a complete working project file accordingly and also prepare a report as mentioned in the pdf" | Assistant analysed the dataset, designed the SEIRD agent-based model, implemented sequential + OpenMP code, scripts, report | All code compiled and run; `make test` compares parallel vs sequential output byte-for-byte |
| 2 | Language choice | "write code in c++" | Original C prototype was rewritten in C++17 (`sim_common.hpp`, `disease_seq.cpp`, `disease_omp.cpp`) | Re-ran comparison: sequential and 4-thread outputs identical after the port |
| 3 | Parallelisation design | (part of prompt 1) Choose between OpenMP / MPI / CUDA | OpenMP selected: state fits in shared memory, random-access contacts | Reasoning in report §5.3; verified by tests and timing |
| 4 | Debugging / design check | *(no separate prompt recorded – assistant's own analysis during prompt 1; replace with your actual prompt if you asked this separately)* Race-condition analysis of the update loop | Double buffering + reduction + stateless RNG → no shared writes | Verified experimentally: identical output for 1–8 threads, 3 schedules |
| 5 | Calibration sanity | *(no separate prompt recorded – assistant's own check during prompt 1; replace with your actual prompt if you asked this separately)* Italy gamma = 0.027, R0 = 21.8 looked unrealistic | Added acceptance range 0.05–0.4 with default fallback | Re-ran `calibrate.py`; Italy R0 = 7.6; validation plot (report Fig. 8) |
| 6 | Final review against the course PDF | "make any change required according to the instructions also explain in detail in extreme detail what is the project about explain in a way we are able to explain any question with any difficulty" (with the instruction PDF, project zip and report PDF attached) | Review found: report generator mis-built the team table (roll-no. column held the role); two unsupported claims in the report ("first-touch-friendly allocation", "two multiplies per hash"); stale single-core notes in README / LLM log; hand edits to the PDF missing from `make_report.py`. All fixed, report regenerated. | Re-ran `make test` (55/55 pass); regenerated report and diffed its text against the previous PDF; checked the first-touch and hash claims against `sim_common.hpp` / `disease_omp.cpp` |
| 7 | *(your prompt)* | | | |

## Critical evaluation of LLM output (required: at least one case)

**Case 1 – per-thread random generators (rejected).**
*Suggested:* give each OpenMP thread its own `std::mt19937` seeded with the thread id (the usual pattern).
*Why considered:* common recommendation, easy to implement.
*Decision:* rejected – results would change with the number of threads and the loop schedule, so the
parallel program could never be compared exactly with the sequential one. Replaced with a stateless
counter-based RNG `rng(seed, day, agent, slot)`.
*Verification:* `scripts/verify.py` shows byte-identical daily output for 1, 2, 3, 4, 8 threads and
static/dynamic/guided schedules.

**Case 2 – automatic estimate of the recovery rate (modified).**
*Suggested:* gamma = median(new recoveries / active cases) from the dataset.
*Problem found:* Italy gave gamma = 0.027 (37-day infectious period) and R0 = 21.8, because recoveries are
reported with long delays.
*Modification:* accept the estimate only inside 0.05–0.4, otherwise use 0.10 and label it "default" in the report.
*Verification:* recalibrated (Italy R0 = 7.6); simulated early growth rates (0.151 India, 0.188 Brazil) are close to the
real ones (0.168, 0.214).

**Case 3 – unsupported performance claims in the AI-drafted report (corrected).**
*Suggested:* the drafted report listed "first-touch-friendly allocation" as an optimisation and said the hash costs
"two multiplies per contact".
*Why considered:* both are plausible, typical statements in OpenMP performance write-ups.
*Problem found on code review:* `nxt` and `cur` are `std::vector<uint8_t>` objects zero-initialised serially by the main
thread, so first touch is not parallel; `rng()` calls `splitmix64` twice (about four 64-bit multiplications).
*Decision:* claim removed, hash cost restated; no result in the report depends on first-touch.
*Verification:* read `sim_common.hpp` and `disease_omp.cpp`; regenerated report.
