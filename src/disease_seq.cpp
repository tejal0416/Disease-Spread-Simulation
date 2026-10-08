// disease_seq.cpp - SEQUENTIAL baseline of the disease spread simulation.
#include "sim_common.hpp"

int main(int argc, char **argv) {
    try {
        sim::Options opt = sim::parse_args(argc, argv);
        const sim::Params &q = opt.q;

        std::vector<std::uint8_t> cur, nxt(static_cast<std::size_t>(q.N));
        sim::init_population(q, cur);

        std::FILE *fo = opt.out.empty() ? nullptr : std::fopen(opt.out.c_str(), "w");
        if (fo) std::fprintf(fo, "day,S,E,I,R,D\n");

        sim::Counts cnt{};
        for (std::uint8_t s : cur) cnt[s]++;
        if (fo) std::fprintf(fo, "0,%ld,%ld,%ld,%ld,%ld\n", cnt[0], cnt[1], cnt[2], cnt[3], cnt[4]);
        long peakI = cnt[sim::I];
        int peakDay = 0, daysRun = 0;

        const double t0 = sim::wall_time();
        for (int day = 1; day <= q.days; day++) {
            long s = 0, e = 0, in = 0, r = 0, d = 0;
            for (long i = 0; i < q.N; i++) {  // <-- the hot loop
                const std::uint8_t ns = sim::next_state(q, cur.data(), i, day);
                nxt[static_cast<std::size_t>(i)] = ns;
                switch (ns) {
                case sim::S: s++; break;
                case sim::E: e++; break;
                case sim::I: in++; break;
                case sim::R: r++; break;
                default: d++; break;
                }
            }
            cur.swap(nxt);  // double-buffer swap
            daysRun = day;
            if (in > peakI) { peakI = in; peakDay = day; }
            cnt = {s, e, in, r, d};
            if (fo) std::fprintf(fo, "%d,%ld,%ld,%ld,%ld,%ld\n", day, s, e, in, r, d);
            if (e + in == 0) break;  // epidemic extinct
        }
        const double t1 = sim::wall_time();

        if (fo) std::fclose(fo);
        sim::report_run("seq", q, 1, t1 - t0, daysRun, cur, peakI, peakDay, cnt[0]);
    } catch (const std::exception &ex) {
        std::fprintf(stderr, "error: %s\n", ex.what());
        return 1;
    }
    return 0;
}
