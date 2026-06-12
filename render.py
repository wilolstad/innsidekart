"""Renderer data.json til en statisk index.html."""

from datetime import datetime

CSS = """
:root{
  --bg:#F3F5F7; --ink:#15202B; --steel:#5A6B7B; --line:#D7DEE4;
  --green:#0E6F5C; --rust:#B23A2E; --card:#FFFFFF;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);
  font-family:'IBM Plex Sans',sans-serif;line-height:1.55;
  padding:40px 20px 80px;max-width:880px;margin:0 auto}
h1{font-family:'Sora',sans-serif;font-weight:700;font-size:clamp(28px,5vw,44px);
  letter-spacing:-0.02em}
.sub{color:var(--steel);margin-top:6px;max-width:60ch}
.meta{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--steel);
  margin-top:14px;text-transform:uppercase;letter-spacing:0.08em}
h2{font-family:'Sora',sans-serif;font-size:20px;margin:48px 0 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:18px 20px;margin-bottom:14px}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  flex-wrap:wrap}
.tick{font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:17px}
.name{color:var(--steel);font-size:14px}
.num{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;
  font-size:14px}
.axis{position:relative;height:34px;margin-top:14px;border-bottom:1px solid var(--line)}
.axis .zero{position:absolute;top:0;bottom:0;width:1px;background:var(--line)}
.dot{position:absolute;top:9px;width:11px;height:11px;border-radius:50%;
  transform:translateX(-50%)}
.dot.market{background:var(--rust)}
.dot.hist{background:var(--green)}
.dot.market.cheap{background:var(--green)}
.lbl{position:absolute;top:-8px;transform:translateX(-50%);
  font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--steel)}
.legend{display:flex;gap:18px;margin-top:8px;font-size:12px;color:var(--steel)}
.legend span::before{content:'';display:inline-block;width:9px;height:9px;
  border-radius:50%;margin-right:6px}
.legend .m::before{background:var(--rust)}
.legend .h::before{background:var(--green)}
.msg{display:block;padding:12px 0;border-bottom:1px solid var(--line);
  text-decoration:none;color:inherit}
.msg:hover .t{text-decoration:underline}
.msg .d{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--steel)}
.msg .t{font-size:15px;margin-top:2px}
.foot{margin-top:56px;font-size:13px;color:var(--steel);max-width:70ch}
.na{color:var(--steel);font-size:13px;margin-top:10px}
.stale{background:#FBEAE8;border:1px solid var(--rust);color:var(--rust);
  padding:10px 14px;border-radius:8px;margin-top:14px;font-size:14px}
"""

AXIS_MIN, AXIS_MAX = -0.10, 0.30  # -10% til +30% CAGR


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
    head = f"""
    <div class="row">
      <div><span class="tick">{tk}</span>
           <span class="name">{c.get('name') or ''}</span></div>
      <div class="num">{c.get('price') or '–'} {c.get('currency') or ''}
           &nbsp;·&nbsp; {fmt_mcap(c.get('market_cap'), c.get('currency'))}</div>
    </div>"""
    if ig is None:
        return f"""<div class="card">{head}
        <div class="na">Reverse-DCF ikke tilgjengelig (negativ/manglende FCF
        eller finansforetak) — typisk for banker og selskaper uten positiv
        kontantstrøm.</div></div>"""
    cheap = " cheap" if (hg is not None and ig < hg) else ""
    dots = f"""
    <div class="axis">
      <div class="zero" style="left:{pos(0)}%"></div>
      <span class="lbl" style="left:{pos(ig)}%">{fmt_pct(ig)}</span>
      <div class="dot market{cheap}" style="left:{pos(ig)}%"
           title="Implisitt FCF-vekst (markedet)"></div>"""
    if hg is not None:
        dots += f"""<div class="dot hist" style="left:{pos(hg)}%"
           title="Historisk FCF-vekst ({fmt_pct(hg)})"></div>"""
    dots += "</div>"
    legend = """<div class="legend"><span class="m">priset inn (10 år)</span>
                <span class="h">historisk FCF-vekst</span></div>"""
    return f'<div class="card">{head}{dots}{legend}</div>'


def render_site(data, path):
    a = data["assumptions"]
    gen = datetime.fromisoformat(data["generated"]).strftime("%d.%m.%Y %H:%M UTC")

    cards = "".join(
        company_card(tk, c) for tk, c in data["companies"].items()
    )
    msgs = "".join(
        f"""<a class="msg" href="{m['url']}" target="_blank" rel="noopener">
            <div class="d">{m['published'][:10]} · {m['ticker']}</div>
            <div class="t">{m['title']}</div></a>"""
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
og hvilken vekst markedet priser inn i hvert selskap (reverse-DCF).</p>
<div class="meta">Oppdatert {gen} · WACC {a['wacc']*100:.0f}% ·
terminalvekst {a['terminal_g']*100:.1f}% · {a['stage1_years']} års horisont</div>
<div class="stale" id="stale" hidden>Dataene er over to døgn gamle —
den nattlige oppdateringen har trolig feilet.</div>

<h2>Selskaper med fersk innsideaktivitet</h2>
{cards}

<h2>Siste meldinger</h2>
{msgs}

<p class="foot">Reverse-DCF løser for den 10-årige FCF-veksten som gjør at
nåverdien av fremtidige kontantstrømmer er lik dagens selskapsverdi
(enterprise value = markedsverdi + gjeld − kontanter; to-stegs modell,
Gordon-vekst i terminalen). Grønn markør til høyre for rød
betyr at selskapet historisk har vokst raskere enn markedet nå krever.
Datakilder: Newsweb (Euronext Oslo) og Yahoo Finance. Dette er et
analyseverktøy, ikke investeringsråd.</p>

<script>
if (Date.now() - new Date("{data['generated']}").getTime() > 48*3600*1000)
  document.getElementById("stale").hidden = false;
</script>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
