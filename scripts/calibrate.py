#!/usr/bin/env python3
"""
calibrate.py - derive disease-model parameters from the JHU COVID-19 dataset.

For each country the script estimates, from the real time series:
  * r      early exponential growth rate of cumulative confirmed cases
  * gamma  recovery rate     (median of  new recoveries / active cases)
  * cfr    case fatality ratio (deaths / confirmed at the end of the data)
  * beta   transmission rate from the SEIR early-growth relation
               (r + sigma)(r + gamma) = sigma * beta
           with sigma = 1/5.2 (mean incubation period, literature value,
           NOT estimated from the data)
and writes   data/params_<country>.txt   (read by the C programs via --params)
             data/real_<country>.csv     (real curve, used for validation plots)
             data/calibration_summary.csv
"""
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

# Country populations (approx. 2020, millions) - not part of the dataset.
POP = {"India": 1380e6, "US": 331e6, "Italy": 60.4e6, "Brazil": 212e6}
SIGMA = 1.0 / 5.2
THRESH = 100        # day 0 = first day with >= THRESH confirmed cases
WINDOW = 21         # days used to fit the early exponential growth
DEFAULT_GAMMA = 0.10


def load_series(name, country):
    df = pd.read_csv(os.path.join(DATA, f"time_series_covid_19_{name}.csv"))
    sub = df[df["Country/Region"] == country]
    if sub.empty:
        raise ValueError(f"{country} not found in {name}")
    cols = sub.columns[4:]
    s = sub[cols].sum(axis=0).astype(float)
    s.index = pd.to_datetime(s.index, format="%m/%d/%y")
    return s


def calibrate(country):
    conf = load_series("confirmed", country)
    deaths = load_series("deaths", country)
    try:
        rec = load_series("recovered", country)
    except ValueError:
        rec = pd.Series(0.0, index=conf.index)

    start = int(np.argmax(conf.values >= THRESH))
    c = conf.values[start:]
    d = deaths.values[start:]
    r_ = rec.values[start:]

    # early exponential growth rate of cumulative confirmed cases
    t = np.arange(WINDOW)
    r_growth = float(np.polyfit(t, np.log(c[:WINDOW]), 1)[0])

    # recovery rate: new recoveries / active cases, only where recoveries are reported
    active = c - r_ - d
    new_rec = np.diff(r_)
    ratio = new_rec / np.maximum(active[:-1], 1.0)
    ok = (r_[1:] > 0) & (active[:-1] > 100) & (new_rec > 0)
    ratio = ratio[ok]
    ratio = ratio[(ratio > 0.0) & (ratio < 0.5)]
    gamma, gsrc = DEFAULT_GAMMA, "default 0.10 (recovery data unusable)"
    if len(ratio) >= 30:
        g = float(np.median(ratio))
        if 0.05 <= g <= 0.4:   # outside this range the series is dominated by reporting lag
            gamma, gsrc = g, "estimated from data"

    cfr = float(d[-1] / c[-1])
    beta = (r_growth + SIGMA) * (r_growth + gamma) / SIGMA
    return dict(country=country, population=POP[country], start_date=str(conf.index[start].date()),
                days_available=len(c), growth_rate_r=r_growth, sigma=SIGMA, gamma=gamma,
                gamma_source=gsrc, beta=beta, R0=beta / gamma, cfr=cfr,
                confirmed_final=c[-1], deaths_final=d[-1]), (c, d, r_)


def main():
    countries = sys.argv[1:] or list(POP)
    rows = []
    for ctry in countries:
        res, (c, d, r_) = calibrate(ctry)
        rows.append(res)
        with open(os.path.join(DATA, f"params_{ctry}.txt"), "w") as f:
            f.write(f"beta={res['beta']:.6f}\nsigma={res['sigma']:.6f}\n"
                    f"gamma={res['gamma']:.6f}\ncfr={res['cfr']:.6f}\ni0_frac=0.0001\n")
        pd.DataFrame({"day": np.arange(len(c)), "confirmed": c, "deaths": d, "recovered": r_}) \
            .to_csv(os.path.join(DATA, f"real_{ctry}.csv"), index=False)
        print(f"{ctry:7s} r={res['growth_rate_r']:.3f}  gamma={res['gamma']:.3f} ({res['gamma_source']})"
              f"  beta={res['beta']:.3f}  R0={res['R0']:.2f}  CFR={res['cfr']:.4f}")
    pd.DataFrame(rows).to_csv(os.path.join(DATA, "calibration_summary.csv"), index=False)


if __name__ == "__main__":
    main()
