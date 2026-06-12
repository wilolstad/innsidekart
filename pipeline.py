"""
Innsidekart — pipeline
Henter meldepliktige handler (primærinnsidere) fra Newsweb (Oslo Børs),
kobler på markedsdata via yfinance, og regner ut hvilken FCF-vekst
markedet priser inn (reverse-DCF, to-stegs modell).

Output: data.json + index.html (statisk side).
Kjøres på nytt hver natt via GitHub Actions (se .github/workflows/nightly.yml).
"""

import json
import math
import sys
import time
from datetime import datetime, timezone

import requests

NEWSWEB_API = "https://api3.oslo.oslobors.no/v1/newsreader/list"
CATEGORY_INSIDER = 1102  # MELDEPLIKTIG HANDEL FOR PRIMÆRINNSIDERE
MESSAGE_URL = "https://newsweb.oslobors.no/message/{id}"

# Reverse-DCF-antagelser (to-stegs modell)
WACC = 0.09            # flat diskonteringsrente for alle selskaper (forenkling, v1)
TERMINAL_G = 0.025     # evig vekst etter år 10 (~nominell BNP)
STAGE1_YEARS = 10

MAX_MESSAGES = 60      # hvor mange meldinger vi henter per kjøring
MAX_TICKERS = 15       # hvor mange unike selskaper vi beriker med verdsettelse


def fetch_insider_messages(days=14):
    """Henter meldepliktige handler siste `days` dager fra Newsweb."""
    from datetime import timedelta
    today = datetime.now(timezone.utc).date()
    params = {
        "category": CATEGORY_INSIDER,
        "fromDate": (today - timedelta(days=days)).isoformat(),
        "toDate": (today + timedelta(days=1)).isoformat(),
    }
    r = requests.get(NEWSWEB_API, params=params, timeout=30,
                     headers={"Accept": "application/json"})
    r.raise_for_status()
    messages = r.json()["data"]["messages"]
    out = []
    for m in messages:
        if m.get("test"):
            continue
        out.append({
            "messageId": m["messageId"],
            "ticker": m.get("issuerSign", ""),
            "issuer": m.get("issuerName", ""),
            "title": m.get("title", ""),
            "published": m.get("publishedTime", ""),
            "markets": m.get("markets", []),
            "url": MESSAGE_URL.format(id=m["messageId"]),
        })
    return out


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
    """Bisection: finn g1 slik at DCF-verdi = target_value ("hva er priset inn").

    target_value skal være enterprise value, ikke market cap: FCF-en fra
    Yahoo er kontantstrøm til hele firmaet, så nåverdien må sammenlignes
    med EV = market cap + gjeld - kontanter.
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
    """Henter market cap, FCF og historisk FCF-vekst via yfinance (.OL)."""
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
        "pe": info.get("trailingPE"),
    }


def build_dataset():
    msgs = fetch_insider_messages()
    print(f"Hentet {len(msgs)} innsidemeldinger fra Newsweb")

    tickers, seen = [], set()
    for m in msgs:
        tk = m["ticker"]
        if tk and tk not in seen:
            seen.add(tk)
            tickers.append(tk)
        if len(tickers) >= MAX_TICKERS:
            break

    companies = {}
    for tk in tickers:
        osl = f"{tk}.OL"
        try:
            f = fetch_fundamentals(osl)
            if f.get("sector") == "Financial Services":
                # banker/forsikring: gjeld er innsatsfaktor, EV og FCF-DCF
                # gir ikke mening — README har alltid lovet dette filteret
                g = None
            else:
                g = implied_growth(f["fcf"], f["ev"])
            f["implied_growth"] = g
            companies[tk] = f
            ig = f"{g*100:.1f}%" if g is not None else "n/a"
            print(f"  {osl}: ev={f['ev']}, fcf={f['fcf']}, implied g={ig}")
        except Exception as e:
            print(f"  {osl}: feilet ({e})", file=sys.stderr)
        time.sleep(0.4)  # vær grei mot Yahoo

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "assumptions": {"wacc": WACC, "terminal_g": TERMINAL_G,
                        "stage1_years": STAGE1_YEARS},
        "messages": msgs,
        "companies": companies,
    }


def main():
    data = build_dataset()
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    from render import render_site
    render_site(data, "index.html")
    print("Skrev data.json og index.html")


if __name__ == "__main__":
    main()
