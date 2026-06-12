"""
Backtest: slår norske innsidekjøp indeksen? (fase 2)

Likevektet event-studie: for hvert innsidekjøp måles aksjens avkastning
1/3/6/12 måneder fra første handelsdag ETTER publisering (ingen look-ahead),
minus benchmarkens avkastning i samme vindu. Segmentert på cluster-kjøp og
rolle (CEO/CFO/styreleder).

Bruk: python3 backtest.py            (krever data/transactions.ndjson)

Ærlige forbehold som følger med resultatene:
- yfinance mangler delistede selskaper -> overlevelsesskjevhet. Skriptet
  teller og rapporterer hvor mange events som mangler prisdata.
- Overlappende vinduer og klyngede events gjør naive t-verdier for
  optimistiske; tolk hit-rate og median, ikke bare snitt.
- Benchmark er prisindeks/ETF fra Yahoo — ikke identisk med OSEBX
  totalavkastning. Til artikkelen: bruk TITLON/Ødegaard-data.
"""

import bisect
import csv
import json
import os
import statistics
import sys
import time

import newsweb
from pipeline import dedupe

HORIZONS = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}  # handelsdager
BENCH_CANDIDATES = ["^OSEAX", "OBXEDNB.OL", "^OBX"]
CACHE_DIR = "data/prices"
THROTTLE = 0.4


def get_history(symbol):
    """Justert sluttkurs per handelsdag, cachet lokalt som JSON."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, symbol.replace("^", "_") + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    import yfinance as yf
    time.sleep(THROTTLE)
    try:
        h = yf.Ticker(symbol).history(period="max", auto_adjust=True)
        prices = {d.strftime("%Y-%m-%d"): float(c)
                  for d, c in h["Close"].items() if c == c}
    except Exception:
        prices = {}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(prices, f)
    return prices


def event_return(prices, dates, pub_date, horizon):
    """Avkastning fra første handelsdag etter pub_date, `horizon` dager frem."""
    i = bisect.bisect_right(dates, pub_date)
    j = i + horizon
    if i >= len(dates) or j >= len(dates):
        return None
    return prices[dates[j]] / prices[dates[i]] - 1


def mark_clusters(buys):
    """Cluster = minst ett annet kjøp i samme selskap innen ±14 dager."""
    by_tk = {}
    for b in buys:
        by_tk.setdefault(b["ticker"], []).append(b["published"][:10])
    for b in buys:
        d = b["published"][:10]
        others = [x for x in by_tk[b["ticker"]] if x != d or
                  by_tk[b["ticker"]].count(d) > 1]
        b["cluster"] = any(abs((_days(x) - _days(d))) <= 14 for x in others)
    return buys


def _days(iso):
    from datetime import date
    y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    return date(y, m, d).toordinal()


def summarize(rows, label, horizon):
    vals = [r[f"excess_{horizon}"] for r in rows
            if r.get(f"excess_{horizon}") is not None]
    if not vals:
        return None
    return {
        "segment": label, "horisont": horizon, "n": len(vals),
        "snitt": statistics.mean(vals),
        "median": statistics.median(vals),
        "hit_rate": sum(1 for v in vals if v > 0) / len(vals),
    }


def main():
    buys = dedupe([r for r in newsweb.load_transactions().values()
                   if r["type"] == "KJØP" and r["ticker"]])
    buys = mark_clusters(buys)
    print(f"{len(buys)} innsidekjøp i basen "
          f"({min(b['published'][:10] for b in buys)} – "
          f"{max(b['published'][:10] for b in buys)})")

    bench = None
    for cand in BENCH_CANDIDATES:
        p = get_history(cand)
        if len(p) > 500:
            bench, bench_name = p, cand
            break
    if not bench:
        sys.exit("Fant ingen brukbar benchmark hos Yahoo")
    bench_dates = sorted(bench)
    print(f"Benchmark: {bench_name} ({len(bench)} handelsdager)")

    rows, missing = [], 0
    tickers = sorted({b["ticker"] for b in buys})
    cache = {}
    for tk in tickers:
        cache[tk] = get_history(f"{tk}.OL")
    for b in buys:
        prices = cache[b["ticker"]]
        if not prices:
            missing += 1
            continue
        dates = sorted(prices)
        row = {"ticker": b["ticker"], "published": b["published"][:10],
               "cluster": b["cluster"], "role": b.get("role"),
               "amount": b.get("amount")}
        any_h = False
        pub = b["published"][:10]
        for h, days in HORIZONS.items():
            sr = event_return(prices, dates, pub, days)
            br = event_return(bench, bench_dates, pub, days)
            row[f"excess_{h}"] = (sr - br) if (sr is not None and
                                               br is not None) else None
            any_h = any_h or row[f"excess_{h}"] is not None
        if any_h:
            rows.append(row)

    print(f"{len(rows)} events med prisdata · {missing} events manglet "
          f"prisdata hos Yahoo (overlevelsesskjevhet — rapporter dette!)\n")

    segments = {
        "Alle kjøp": rows,
        "Cluster-kjøp": [r for r in rows if r["cluster"]],
        "CEO/CFO/styreleder": [r for r in rows
                               if r.get("role") in ("CEO", "CFO", "Styreleder")],
    }
    results = []
    print(f"{'Segment':22s} {'Hor.':5s} {'N':>4s} {'Snitt':>8s} "
          f"{'Median':>8s} {'Hit':>6s}")
    for label, seg in segments.items():
        for h in HORIZONS:
            s = summarize(seg, label, h)
            if s:
                results.append(s)
                print(f"{label:22s} {h:5s} {s['n']:>4d} "
                      f"{s['snitt']*100:>+7.1f}% {s['median']*100:>+7.1f}% "
                      f"{s['hit_rate']*100:>5.0f}%")

    with open("backtest_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["segment", "horisont", "n",
                                          "snitt", "median", "hit_rate"])
        w.writeheader()
        w.writerows(results)
    from datetime import date
    meta = {
        "run_date": date.today().isoformat(),
        "period_from": min(b["published"][:10] for b in buys),
        "period_to": max(b["published"][:10] for b in buys),
        "n_buys": len(buys),
        "n_events": len(rows),
        "n_missing_prices": missing,
        "benchmark": bench_name,
    }
    with open("backtest_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("\nSkrev backtest_results.csv + backtest_meta.json."
          "\nHusk forbeholdene i docstringen før publisering.")


if __name__ == "__main__":
    main()
