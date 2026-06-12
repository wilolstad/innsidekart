"""
Innsidekart — pipeline
Henter meldepliktige handler (primærinnsidere) fra Newsweb (Oslo Børs),
parser kjøp/salg/volum/beløp/rolle per melding (se newsweb.py), kobler på
markedsdata via yfinance, og regner ut hvilken FCF-vekst markedet priser
inn (reverse-DCF mot enterprise value, to-stegs modell).

Output: data.json + index.html (statisk side) + data/transactions.ndjson
(append-only transaksjonsbase som GitHub-runneren committer tilbake).
Kjøres hver natt via GitHub Actions (se .github/workflows/nightly.yml).
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone

import newsweb

# Reverse-DCF-antagelser (to-stegs modell)
WACC = 0.09            # flat diskonteringsrente for alle selskaper (v1)
TERMINAL_G = 0.025     # evig vekst etter år 10 (~nominell BNP)
STAGE1_YEARS = 10

WINDOW_DAYS = 14       # aktivitetsvindu for siden og cluster-flagget
MAX_TICKERS = 15       # hvor mange selskaper som berikes med verdsettelse


def dcf_value(fcf0, g1, wacc=WACC, g2=TERMINAL_G, years=STAGE1_YEARS):
    """Nåverdi av FCF: vekst g1 i `years` år, deretter Gordon-vekst g2."""
    pv = 0.0
    fcf = fcf0
    for t in range(1, years + 1):
        fcf = fcf * (1 + g1)
        pv += fcf / (1 + wacc) ** t
    terminal = fcf * (1 + g2) / (wacc - g2)
    pv += terminal / (1 + wacc) ** years
    return pv


def implied_growth(fcf0, target_value, lo=-0.50, hi=1.50, tol=1e-5):
    """Bisection: finn g1 slik at DCF-verdi = target_value.

    target_value skal være enterprise value: FCF-en fra Yahoo er
    kontantstrøm til hele firmaet, så sammenligningsgrunnlaget må
    inkludere netto gjeld.
    """
    if fcf0 is None or target_value is None or fcf0 <= 0 or target_value <= 0:
        return None
    f_lo = dcf_value(fcf0, lo) - target_value
    f_hi = dcf_value(fcf0, hi) - target_value
    if f_lo * f_hi > 0:
        return None  # utenfor søkeintervallet
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = dcf_value(fcf0, mid) - target_value
        if abs(f_mid) < tol * target_value:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def fetch_fundamentals(osl_ticker):
    """Henter market cap, EV, FCF og historisk FCF-vekst via yfinance."""
    import yfinance as yf
    t = yf.Ticker(osl_ticker)
    info = t.info or {}
    mcap = info.get("marketCap")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    shares = info.get("sharesOutstanding")
    if mcap is None and price and shares:
        mcap = price * shares
    # EV = egenkapital + gjeld - kontanter; mangler feltene antar vi 0
    ev = None
    if mcap is not None:
        ev = mcap + (info.get("totalDebt") or 0) - (info.get("totalCash") or 0)
    fcf = info.get("freeCashflow")
    hist_g = None
    try:
        cf = t.cashflow
        if cf is not None and "Free Cash Flow" in cf.index:
            row = cf.loc["Free Cash Flow"].dropna()
            if len(row) >= 2:
                newest, oldest = float(row.iloc[0]), float(row.iloc[-1])
                n = len(row) - 1
                if oldest > 0 and newest > 0:
                    hist_g = (newest / oldest) ** (1 / n) - 1
            if fcf is None and len(row) >= 1:
                fcf = float(row.iloc[0])
    except Exception:
        pass
    return {
        "name": info.get("longName") or info.get("shortName"),
        "price": price,
        "currency": info.get("currency"),
        "sector": info.get("sector"),
        "market_cap": mcap,
        "ev": ev,
        "fcf": fcf,
        "hist_fcf_growth": hist_g,
    }


def dedupe(records):
    """Fjerner språk-dubletter: Newsweb publiserer ofte samme handel som
    egen norsk og engelsk melding. Samme ticker+type+volum+dato = én handel."""
    seen, out = set(), []
    for r in sorted(records, key=lambda r: r["published"]):
        key = (r["ticker"], r["type"], r.get("volume"), r["published"][:10])
        if r.get("volume") and key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def aggregate(records):
    """Aktivitet per selskap: antall kjøp/salg, beløp, navn, cluster-flagg."""
    agg = {}
    for r in records:
        tk = r["ticker"]
        if not tk:
            continue
        a = agg.setdefault(tk, {
            "issuer": r["issuer"], "n_buy": 0, "n_sell": 0, "n_program": 0,
            "n_unknown": 0, "buy_amount": 0.0, "buy_vol_noamt": 0,
            "sell_amount": 0.0, "sell_vol_noamt": 0,
            "buyers": [], "roles": [],
        })
        kind = r["type"]
        if kind == "KJØP":
            a["n_buy"] += 1
            if r.get("amount"):
                a["buy_amount"] += r["amount"]
            elif r.get("volume"):
                # beløp ukjent men volum kjent: estimeres i render
                # som volum x dagens kurs (merkes med tilnærmet-tegn)
                a["buy_vol_noamt"] += r["volume"]
            if r.get("name") and r["name"] not in a["buyers"]:
                a["buyers"].append(r["name"])
            if r.get("role"):
                a["roles"].append(r["role"])
        elif kind == "SALG":
            a["n_sell"] += 1
            if r.get("amount"):
                a["sell_amount"] += r["amount"]
            elif r.get("volume"):
                a["sell_vol_noamt"] += r["volume"]
        elif kind == "PROGRAM":
            a["n_program"] += 1
        else:
            a["n_unknown"] += 1
    for tk, a in agg.items():
        distinct_buyers = len(a["buyers"])
        a["cluster"] = a["n_buy"] >= 2 or distinct_buyers >= 2
        a["top_role"] = next((r for r in ["CEO", "CFO", "Styreleder", "Styre",
                                          "Ledelse"] if r in a["roles"]), None)
    return agg


def build_dataset():
    today = datetime.now(timezone.utc).date()
    cutoff = (today - timedelta(days=WINDOW_DAYS)).isoformat()
    msgs = newsweb.fetch_list(cutoff, (today + timedelta(days=1)).isoformat())
    print(f"Hentet {len(msgs)} innsidemeldinger fra Newsweb")

    db = newsweb.load_transactions()
    new = 0
    for m in msgs:
        if m["messageId"] in db:
            continue
        try:
            db[m["messageId"]] = newsweb.parse_message(m)
            new += 1
        except Exception as e:
            print(f"  parse feilet {m['messageId']}: {e}", file=sys.stderr)
        time.sleep(newsweb.THROTTLE)
    if new:
        newsweb.save_transactions(db)
    print(f"Parset {new} nye meldinger ({len(db)} totalt i basen)")

    recent = dedupe([r for r in db.values() if r["published"][:10] >= cutoff])
    recent.sort(key=lambda r: r["published"], reverse=True)
    agg = aggregate(recent)

    # hovedtabellen viser kun selskaper med ekte kjøp/salg — selskaper som
    # bare har program-/ukjent-meldinger er støy og holdes utenfor
    ranked = sorted(
        (tk for tk in agg if agg[tk]["n_buy"] or agg[tk]["n_sell"]),
        key=lambda tk: (-agg[tk]["n_buy"], -agg[tk]["buy_amount"],
                        -agg[tk]["n_sell"]))
    companies = {}
    for tk in ranked:
        comp = {"issuer": agg[tk]["issuer"], **{k: v for k, v in agg[tk].items()
                                                if k != "issuer"}}
        if len(companies) < MAX_TICKERS:
            try:
                f = fetch_fundamentals(f"{tk}.OL")
                if f.get("sector") == "Financial Services":
                    g = None  # bank/forsikring: FCF-DCF gir ikke mening
                else:
                    g = implied_growth(f["fcf"], f["ev"])
                f["implied_growth"] = g
                comp.update(f)
                ig = f"{g*100:+.1f}%" if g is not None else "n/a"
                print(f"  {tk}.OL: kjøp={comp['n_buy']} salg={comp['n_sell']} "
                      f"implied={ig}")
            except Exception as e:
                print(f"  {tk}.OL: verdsettelse feilet ({e})", file=sys.stderr)
            time.sleep(0.4)  # vær grei mot Yahoo
        companies[tk] = comp

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "window_days": WINDOW_DAYS,
        "base_total": len(db),
        "assumptions": {"wacc": WACC, "terminal_g": TERMINAL_G,
                        "stage1_years": STAGE1_YEARS},
        "messages": recent,
        "companies": companies,
    }


def main():
    data = build_dataset()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    from render import render_site, render_article
    render_site(data, "index.html")
    render_article(data, "analyse.html")
    print("Skrev data.json, index.html og analyse.html")


if __name__ == "__main__":
    main()
