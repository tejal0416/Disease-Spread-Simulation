// disease_omp.cpp - OpenMP parallel version of the disease spread simulation.
//
// Parallelisation strategy (data parallelism over agents):
//  - Each day, the loop over all N agents is split among threads.
//  - Agents only READ yesterday's array `cur` and WRITE their own slot of
//    `nxt` (double buffering) -> no data race, no locks, no atomics.
//  - Randomness is counter-based (see sim_common.hpp) -> the result is identical
//    for any thread count and any schedule.
//  - Daily S/E/I/R/D totals use an OpenMP reduction (thread-private partial
//    sums combined once per day).
//  - The loop schedule can be chosen at run time (--schedule static|dynamic|guided).
#include "sim_common.hpp"
#include <omp.h>

int main(int argc, char **argv) {
    try {
        sim::Options opt = sim::parse_args(argc, argv);
        const sim::Params &q = opt.q;

        const int threads = opt.threads > 0 ? opt.threads : omp_get_max_threads();
        omp_set_num_threads(threads);
        if (opt.schedule == "dynamic") omp_set_schedule(omp_sched_dynamic, 4096);
        else if (opt.schedule == "guided") omp_set_schedule(omp_sched_guided, 4096);
        else omp_set_schedule(omp_sched_static, 0);

        std::vector<std::uint8_t> cur, nxt(static_cast<std::size_t>(q.N));
        sim::init_population(q, cur);

        std::FILE *fo = opt.out.empty() ? nullptr : std::fopen(opt.out.c_str(), "w");
        if (fo) std::fprintf(fo, "day,S,E,I,R,D\n");

        sim::Counts cnt{};
        for (std::uint8_t s : cur) cnt[s]++;
        if (fo) std::fprintf(fo, "0,%ld,%ld,%ld,%ld,%ld\n", cnt[0], cnt[1], cnt[2], cnt[3], cnt[4]);
        long peakI = cnt[sim::I];
        int peakDay = 0, daysRun = 0;

        std::uint8_t *curp = cur.data(), *nxtp = nxt.data();
        const long N = q.N;

        const double t0 = omp_get_wtime();
        for (int day = 1; day <= q.days; day++) {
            long s = 0, e = 0, in = 0, r = 0, d = 0;
            #pragma omp parallel for schedule(runtime) reduction(+ : s, e, in, r, d)
            for (long i = 0; i < N; i++) {
                const std::uint8_t ns = sim::next_state(q, curp, i, day);
                nxtp[i] = ns;  // each thread writes only its own slots
                switch (ns) {
                case sim::S: s++; break;
                case sim::E: e++; break;
                case sim::I: in++; break;
                case sim::R: r++; break;
                default: d++; break;
                }
            }  // implicit barrier: the day is finished before buffers are swapped
            std::swap(curp, nxtp);
            daysRun = day;
            if (in > peakI) { peakI = in; peakDay = day; }
            cnt = {s, e, in, r, d};
            if (fo) std::fprintf(fo, "%d,%ld,%ld,%ld,%ld,%ld\n", day, s, e, in, r, d);
            if (e + in == 0) break;
        }
        const double t1 = omp_get_wtime();

        if (fo) std::fclose(fo);
        if (curp != cur.data()) cur.swap(nxt);  // make `cur` hold the final state
        sim::report_run("omp", q, threads, t1 - t0, daysRun, cur, peakI, peakDay, cnt[0]);
    } catch (const std::exception &ex) {
        std::fprintf(stderr, "error: %s\n", ex.what());
        return 1;
    }
    return 0;
}
