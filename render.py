"""Renderer data.json til en statisk index.html."""

from datetime import datetime

CSS = """
:root{
  --bg:#F6F8FA; --ink:#0A2540; --steel:#5B7083; --faint:#8CA3B5;
  --line:#E3E8EE; --track:#EAEEF2; --tick:#C7D0D9;
  --green:#0E6F5C; --rust:#B23A2E; --card:#FFFFFF;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);
  font-family:'IBM Plex Sans',sans-serif;line-height:1.55;
  padding:40px 20px 80px;max-width:880px;margin:0 auto}
h1{font-family:'Sora',sans-serif;font-weight:700;font-size:clamp(30px,5vw,46px);
  letter-spacing:-0.025em}
.sub{color:var(--steel);margin-top:6px;max-width:62ch;font-size:15px}
.meta{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--faint);
  margin-top:14px;text-transform:uppercase;letter-spacing:0.08em}
h2{font-family:'Sora',sans-serif;font-size:18px;font-weight:600;margin:44px 0 6px}
.legend{font-size:12.5px;color:var(--steel);margin-bottom:14px}
.legend .sw{display:inline-block;width:18px;height:8px;border-radius:4px;
  background:var(--faint);margin-right:5px}
.legend .dt{display:inline-block;width:9px;height:9px;border-radius:50%;
  background:var(--green);margin:0 5px 0 14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:16px 18px;margin-bottom:10px}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  flex-wrap:wrap}
.tick{font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:15px}
.name{color:var(--steel);font-size:12.5px;margin-left:6px}
.sm{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--steel);
  margin-top:2px}
.big{font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:18px;
  font-variant-numeric:tabular-nums;text-align:right}
.biglbl{font-size:10px;color:var(--faint);text-transform:uppercase;
  letter-spacing:0.07em;text-align:right}
.cheap{color:var(--green)} .rich{color:var(--rust)} .neutral{color:var(--steel)}
.axis{position:relative;height:10px;background:var(--track);border-radius:5px;
  margin-top:14px}
.axis .zero{position:absolute;top:-2px;width:2px;height:14px;background:var(--tick)}
.axis .fill{position:absolute;top:0;height:10px;border-radius:5px}
.fill.cheap{background:var(--green)} .fill.rich{background:var(--rust)}
.fill.neutral{background:var(--faint)}
.axis .hist{position:absolute;top:1px;width:8px;height:8px;border-radius:50%;
  background:var(--green);border:2px solid #fff;transform:translateX(-50%)}
.scale{position:relative;height:15px;margin-top:5px;
  font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--faint)}
.scale span{position:absolute;top:0}
.na{color:var(--steel);font-size:12.5px;margin-top:8px}
.msgs{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:4px 18px}
.msg{display:flex;align-items:baseline;gap:10px;padding:11px 0;
  border-bottom:1px solid var(--line);text-decoration:none;color:inherit}
.msg:last-child{border-bottom:none}
.msg:hover .t{text-decoration:underline}
.msg .d{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--faint);
  flex:none;width:40px}
.msg .chip{font-family:'IBM Plex Mono',monospace;font-size:11px;
  background:var(--track);border-radius:4px;padding:1px 6px;flex:none;
  min-width:52px;text-align:center}
.msg .t{font-size:14px}
.foot{margin-top:52px;font-size:12.5px;color:var(--steel);max-width:72ch}
.stale{background:#FBEAE8;border:1px solid var(--rust);color:var(--rust);
  padding:10px 14px;border-radius:8px;margin-top:14px;font-size:14px}
"""

AXIS_MIN, AXIS_MAX = -0.15, 0.30  # -15% til +30% CAGR


def pos(g):
    g = max(AXIS_MIN, min(AXIS_MAX, g))
    return (g - AXIS_MIN) / (AXIS_MAX - AXIS_MIN) * 100


def fmt_pct(g):
    return f"{g*100:+.1f}%" if g is not None else "n/a"


def fmt_mcap(v, cur):
    if not v:
        return "n/a"
    if v >= 1e9:
        return f"{v/1e9:.1f} mrd {cur or ''}".strip()
    return f"{v/1e6:.0f} mill {cur or ''}".strip()


def company_card(tk, c):
    ig, hg = c.get("implied_growth"), c.get("hist_fcf_growth")
    sub = (f"{c.get('price') or '–'} {c.get('currency') or ''} · "
           f"{fmt_mcap(c.get('market_cap'), c.get('currency'))}")
    head_left = f"""<div><span class="tick">{tk}</span>
        <span class="name">{c.get('name') or ''}</span>
        <div class="sm">{sub}</div></div>"""
    if ig is None:
        return f"""<div class="card"><div class="row">{head_left}</div>
        <div class="na">Reverse-DCF ikke meningsfull her — negativ eller
        manglende fri kontantstrøm, eller finansforetak.</div></div>"""
    cls = "neutral" if hg is None else ("cheap" if ig < hg else "rich")
    left, right = pos(min(ig, 0)), pos(max(ig, 0))
    hist = (f"""<div class="hist" style="left:{pos(hg):.1f}%"
            title="Historisk FCF-vekst {fmt_pct(hg)}"></div>"""
            if hg is not None else "")
    return f"""<div class="card">
    <div class="row">{head_left}
      <div><div class="big {cls}">{fmt_pct(ig)}</div>
           <div class="biglbl">priset inn / år</div></div>
    </div>
    <div class="axis">
      <div class="zero" style="left:{pos(0):.1f}%"></div>
      <div class="fill {cls}" style="left:{left:.1f}%;width:{max(right - left, 0.8):.1f}%"></div>
      {hist}
    </div>
    <div class="scale">
      <span style="left:0">−15 %</span>
      <span style="left:{pos(0):.1f}%;transform:translateX(-50%)">0</span>
      <span style="right:0">+30 %</span>
    </div></div>"""


def render_site(data, path):
    a = data["assumptions"]
    gen = datetime.fromisoformat(data["generated"]).strftime("%d.%m.%Y %H:%M UTC")

    comps = sorted(data["companies"].items(),
                   key=lambda kv: kv[1].get("implied_growth") is None)
    cards = "".join(company_card(tk, c) for tk, c in comps)
    msgs = "".join(
        f"""<a class="msg" href="{m['url']}" target="_blank" rel="noopener">
            <span class="d">{m['published'][8:10]}.{m['published'][5:7]}</span>
            <span class="chip">{m['ticker'] or '–'}</span>
            <span class="t">{m['title']}</span></a>"""
        for m in data["messages"][:30]
    )

    html = f"""<!doctype html>
<html lang="no"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Innsidekart — innsidehandler og hva som er priset inn, Oslo Børs</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@600;700&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>

<h1>Innsidekart</h1>
<p class="sub">Ferske meldepliktige handler fra primærinnsidere på Oslo Børs —
og hvilken FCF-vekst markedet priser inn i hvert selskap (reverse-DCF).</p>
<div class="meta">Oppdatert {gen} · WACC {a['wacc']*100:.0f}% ·
terminalvekst {a['terminal_g']*100:.1f}% · {a['stage1_years']} års horisont</div>
<div class="stale" id="stale" hidden>Dataene er over to døgn gamle —
den nattlige oppdateringen har trolig feilet.</div>

<h2>Selskaper med fersk innsideaktivitet</h2>
<div class="legend"><span class="sw"></span>vekst markedet priser inn (10 år)
<span class="dt"></span>historisk levert · grønn bar = levert mer enn kravet,
rust = mindre, grå = mangler historikk</div>
{cards}

<h2>Siste meldinger</h2>
<div class="msgs">{msgs}</div>

<p class="foot">Reverse-DCF løser for den 10-årige FCF-veksten som gjør at
nåverdien av fremtidige kontantstrømmer er lik dagens selskapsverdi
(enterprise value = markedsverdi + gjeld − kontanter; to-stegs modell,
Gordon-vekst i terminalen). Datakilder: Newsweb (Euronext Oslo) og
Yahoo Finance. Dette er et analyseverktøy, ikke investeringsråd.</p>

<script>
if (Date.now() - new Date("{data['generated']}").getTime() > 48*3600*1000)
  document.getElementById("stale").hidden = false;
</script>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
