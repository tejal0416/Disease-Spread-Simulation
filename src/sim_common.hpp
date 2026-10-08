/*
 * sim_common.hpp - shared model definition for the Disease Spread Simulation
 * (Q28).  Used by BOTH the sequential and the OpenMP implementation so that
 * the two programs execute exactly the same per-agent update rule.
 *
 * Model: stochastic, discrete-time (1 step = 1 day), agent-based SEIRD model.
 *   S -> E  : susceptible agent meets an infectious agent (per-contact prob. p)
 *   E -> I  : latent agent becomes infectious        (prob. sigma per day)
 *   I -> R/D: infectious agent resolves              (prob. gamma per day);
 *             dies with probability cfr, otherwise recovers
 *
 * Contact structure: every susceptible agent has
 *   kl "local" contacts  : random agents inside +-window indices (neighbourhood)
 *   kg "global" contacts : uniformly random agents in the whole population
 *
 * KEY DESIGN DECISION (determinism): random numbers come from a counter-based
 * generator  rng(seed, day, agent, slot)  = hash of its arguments.  There is no
 * shared generator state, so the result does not depend on how agents are
 * split between threads.  Sequential and parallel runs therefore give
 * bit-identical results, which makes verification exact.
 */
#pragma once

#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace sim {

enum State : std::uint8_t { S = 0, E = 1, I = 2, R = 3, D = 4 };

struct Params {
    long          N        = 1000000;  // population size
    int           days     = 120;      // maximum number of simulated days
    int           kl       = 4;        // local contacts per susceptible agent per day
    int           kg       = 4;        // global contacts per susceptible agent per day
    long          window   = 50;       // half-width of the local neighbourhood
    double        beta     = 0.45;     // transmission rate (infections / infectious / day)
    double        sigma    = 1.0 / 5.2;// 1 / latent period
    double        gamma    = 0.10;     // 1 / infectious period
    double        cfr      = 0.015;    // P(death | infectious period ends)
    double        i0_frac  = 1e-4;     // fraction initially infected
    long          i0_min   = 10;       // lower bound on initially infected agents
    std::uint64_t seed     = 12345ULL;
    // derived (see finalize)
    double        p        = 0.0;      // per-contact infection probability
    std::uint32_t p_thr = 0, sigma_thr = 0, gamma_thr = 0, cfr_thr = 0;  // 24-bit thresholds

    void finalize() {
        constexpr double U24 = 16777216.0;  // 2^24
        p = beta / static_cast<double>(kl + kg);
        if (p > 1.0) p = 1.0;
        p_thr     = static_cast<std::uint32_t>(p * U24);
        sigma_thr = static_cast<std::uint32_t>(sigma * U24);
        gamma_thr = static_cast<std::uint32_t>(gamma * U24);
        cfr_thr   = static_cast<std::uint32_t>(cfr * U24);
    }
};

// ---------------- counter-based random number generator ----------------
inline std::uint64_t splitmix64(std::uint64_t x) {
    x += 0x9E3779B97F4A7C15ULL;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ULL;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBULL;
    return x ^ (x >> 31);
}

// Stateless: the same (seed, day, agent, slot) always yields the same 64 bits.
inline std::uint64_t rng(std::uint64_t seed, std::uint64_t day, std::uint64_t agent,
                         std::uint64_t slot) {
    return splitmix64(splitmix64(seed + day * 0xD1B54A32D192ED03ULL) ^ (agent * 64ULL + slot));
}

/*
 * Per-agent update rule.  Reads ONLY from `cur` (yesterday's states) and
 * returns the new state of agent i.  Because no agent writes anything except
 * its own slot of the `next` array, all agents can be updated in parallel
 * without locks or atomics (no data races).
 */
inline std::uint8_t next_state(const Params &q, const std::uint8_t *cur, long i, int day) {
    const std::uint8_t st = cur[i];
    const auto d64 = static_cast<std::uint64_t>(day);
    const auto i64 = static_cast<std::uint64_t>(i);
    switch (st) {
    case S: {
        const long N = q.N, W = q.window;
        std::uint64_t slot = 0;
        for (int k = 0; k < q.kl; k++, slot++) {
            std::uint64_t h = rng(q.seed, d64, i64, slot);
            long j = i - W + static_cast<long>(static_cast<std::uint32_t>(h) %
                                               static_cast<std::uint32_t>(2 * W + 1));
            if (j < 0) j += N; else if (j >= N) j -= N;
            if (cur[j] == I && static_cast<std::uint32_t>(h >> 40) < q.p_thr) return E;
        }
        for (int k = 0; k < q.kg; k++, slot++) {
            std::uint64_t h = rng(q.seed, d64, i64, slot);
            long j = static_cast<long>(static_cast<std::uint32_t>(h) % static_cast<std::uint32_t>(N));
            if (cur[j] == I && static_cast<std::uint32_t>(h >> 40) < q.p_thr) return E;
        }
        return S;
    }
    case E: {
        std::uint64_t h = rng(q.seed, d64, i64, 62);
        return (static_cast<std::uint32_t>(h >> 40) < q.sigma_thr) ? I : E;
    }
    case I: {
        std::uint64_t h = rng(q.seed, d64, i64, 62);
        if (static_cast<std::uint32_t>(h >> 40) < q.gamma_thr) {
            std::uint64_t h2 = rng(q.seed, d64, i64, 63);
            return (static_cast<std::uint32_t>(h2 >> 40) < q.cfr_thr) ? D : R;
        }
        return I;
    }
    default:
        return st;  // R and D are absorbing
    }
}

// Seed the epidemic: deterministic, independent of thread count.
inline long init_population(const Params &q, std::vector<std::uint8_t> &state) {
    state.assign(static_cast<std::size_t>(q.N), S);
    long want = static_cast<long>(q.i0_frac * static_cast<double>(q.N));
    if (want < q.i0_min) want = q.i0_min;
    if (want > q.N) want = q.N;
    long got = 0;
    for (std::uint64_t k = 0; got < want; k++) {
        auto a = static_cast<std::size_t>(rng(q.seed, 0xFFFFFFFFULL, k, 0) %
                                          static_cast<std::uint64_t>(q.N));
        if (state[a] == S) { state[a] = I; got++; }
    }
    return got;
}

inline std::uint64_t fnv1a(const std::vector<std::uint8_t> &a) {
    std::uint64_t h = 1469598103934665603ULL;
    for (std::uint8_t b : a) { h ^= b; h *= 1099511628211ULL; }
    return h;
}

inline double wall_time() {
    using clk = std::chrono::steady_clock;
    return std::chrono::duration<double>(clk::now().time_since_epoch()).count();
}

// Tally of the five compartments.
using Counts = std::array<long, 5>;

// --------------------- parameter file + command line ---------------------
inline void load_param_file(Params &q, const std::string &fn) {
    std::ifstream f(fn);
    if (!f) throw std::runtime_error("cannot open params file " + fn);
    std::string line;
    while (std::getline(f, line)) {
        auto eq = line.find('=');
        if (eq == std::string::npos) continue;
        std::string key = line.substr(0, eq);
        double v = std::stod(line.substr(eq + 1));
        if (key == "beta") q.beta = v;
        else if (key == "sigma") q.sigma = v;
        else if (key == "gamma") q.gamma = v;
        else if (key == "cfr") q.cfr = v;
        else if (key == "i0_frac") q.i0_frac = v;
    }
}

struct Options {
    Params      q;
    std::string out;                 // optional per-day CSV path
    int         threads  = 0;        // 0 = OpenMP default (only used by the OpenMP build)
    std::string schedule = "static"; // static | dynamic | guided (OpenMP build)
};

inline Options parse_args(int argc, char **argv) {
    Options o;
    for (int a = 1; a + 1 < argc; a++)
        if (std::string(argv[a]) == "--params") load_param_file(o.q, argv[a + 1]);
    for (int a = 1; a < argc; a++) {
        const std::string k = argv[a];
        auto next = [&]() -> std::string {
            if (a + 1 >= argc) throw std::runtime_error("missing value for " + k);
            return argv[++a];
        };
        if (k == "--N") o.q.N = static_cast<long>(std::stod(next()));
        else if (k == "--days") o.q.days = std::stoi(next());
        else if (k == "--kl") o.q.kl = std::stoi(next());
        else if (k == "--kg") o.q.kg = std::stoi(next());
        else if (k == "--window") o.q.window = std::stol(next());
        else if (k == "--beta") o.q.beta = std::stod(next());
        else if (k == "--sigma") o.q.sigma = std::stod(next());
        else if (k == "--gamma") o.q.gamma = std::stod(next());
        else if (k == "--cfr") o.q.cfr = std::stod(next());
        else if (k == "--i0frac") o.q.i0_frac = std::stod(next());
        else if (k == "--seed") o.q.seed = std::stoull(next());
        else if (k == "--out") o.out = next();
        else if (k == "--threads") o.threads = std::stoi(next());
        else if (k == "--schedule") o.schedule = next();
        else if (k == "--params") next();
        else throw std::runtime_error("unknown option " + k);
    }
    Params &q = o.q;
    if (q.N < 4) throw std::runtime_error("N too small");
    if (q.N < 2 * q.window + 2) q.window = (q.N - 2) / 2;
    if (q.kl + q.kg > 40) throw std::runtime_error("kl+kg must be <= 40");
    if (q.kl + q.kg < 1) throw std::runtime_error("need at least one contact");
    q.finalize();
    return o;
}

// Console summary shared by both programs (machine-readable RESULT line on stdout).
inline void report_run(const char *impl, const Params &q, int threads, double secs, int days_run,
                       const std::vector<std::uint8_t> &state, long peak_I, int peak_day,
                       long final_S) {
    const double attack = 1.0 - static_cast<double>(final_S) / static_cast<double>(q.N);
    std::printf("RESULT,%s,%ld,%d,%d,%d,%.6f,%016llx,%ld,%d,%.6f\n", impl, q.N, q.kl + q.kg, q.days,
                threads, secs, static_cast<unsigned long long>(fnv1a(state)), peak_I, peak_day, attack);
    std::fprintf(stderr, "[%s] N=%ld days_run=%d threads=%d time=%.4fs peakI=%ld (day %d) attack=%.4f\n",
                 impl, q.N, days_run, threads, secs, peak_I, peak_day, attack);
}

}  // namespace sim
