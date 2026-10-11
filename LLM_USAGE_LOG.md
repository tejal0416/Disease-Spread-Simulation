I have attached my DAA project instructions PDF, the Q28 Disease Spread Simulation problem statement, and the JHU COVID-19 time-series dataset containing confirmed cases, deaths, and recovered cases.
Build a complete working project based strictly on these attached materials. The project must include:
A sequential version of the Disease Spread Simulation.
An OpenMP parallel version.
Correctness tests to verify that the sequential and parallel versions produce correct and consistent results.
Performance experiments to investigate the effect of population size and simulation parameters on execution time.
Graphs for the performance experiments.
A complete report following exactly the format and requirements specified in the attached DAA project instructions PDF.
Use the provided JHU COVID-19 dataset where required by the project instructions/problem statement. Keep the implementation simple, readable, and explainable in a viva.

Write all the code in C++17 instead of C. Put the model in a shared header so the sequential and OpenMP programs use exactly the same update rule. 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------

Use a stochastic agent-based SEIRD model with S→E→I→R/D. Each susceptible agent has kl local contacts within ±window indices and kg global random contacts. The per-contact infection probability is β/(kl+kg). Latent, infectious and death rates come from σ, γ and CFR. 

-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Make the daily update synchronous. next_state() must read only yesterday's array and return the new state of one agent. Use two buffers and swap them at the end of each day, so no agent ever sees a half-updated day 

-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Compare OpenMP, MPI and CUDA for this problem. Which one fits when the whole state is N bytes and contacts are random-access? Justify the choice for the report 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Parallelize the agent loop with #pragma omp parallel for and reduction(+: s,e,in,r,d) for the daily S/E/I/R/D totals. Let me pick the schedule at run time (static, dynamic or guided) and the thread count from the command line. 

-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Review the OpenMP loop for data races. Which variables are shared and which are private? Prove that each thread writes only its own slot of nxt, and explain what the implicit barrier does before the buffer swap. 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------

Give each OpenMP thread its own std::mt19937 seeded with the thread id. Will the parallel result match the sequential one? Show what goes wrong when I change the thread count or the schedule. 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Replace the per-thread generators with a stateless counter-based RNG, rng(seed, day, agent, slot), built from SplitMix64. The random number for an agent must not depend on which thread runs it. Also make the initial infected placement deterministic. 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Write calibrate.py to read the JHU confirmed, deaths and recovered files for India, US, Italy and Brazil. Align day 0 at 100 cases and fit the early exponential growth rate over 21 days. Estimate γ from recoveries/active cases and CFR from deaths/confirmed. Get β from (r+σ)(r+γ) = σβ with σ = 1/5.2. Write params_<country>.txt files that the C++ programs can load with --params 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Italy's γ comes out as 0.027 and R0 as 21.8, which looks unrealistic. Add an acceptance range for γ and fall back to a default when the estimate is outside it. Label the fallback clearly as 'default' in the outputs. 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Write verify.py with three tests. (1) The OpenMP daily CSV and final checksum must be identical to the sequential run for several thread counts, schedules, population sizes and parameter sets. (2) Population must be conserved every day, and R and D must never decrease. (3) The same seed must give the same result and a different seed a different result. Save the outcome to verification.csv. 
-------------------------------------------------------------------------------------------------------------------------------------------------------------------
Write run_benchmarks.py for five experiments: E1 time vs population size, E2 strong scaling with speedup and efficiency, E3 effect of contacts, days and country parameters, E4 static vs dynamic vs guided, E5 epidemic curves validated against real growth rates. Take the best of several repetitions, record the machine info, and save CSVs and graphs G1–G8 
