"""Renderer data.json til en statisk index.html."""

from datetime import datetime
from html import escape

CSS = """
:root{
  --ink:#16191D; --muted:#667085; --faint:#98A2B3; --hair:#E4E7EC;
  --green:#067647; --red:#B42318; --rowhover:#F9FAFB;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#FFFFFF;color:var(--ink);
  font-family:'IBM Plex Sans',sans-serif;line-height:1.55;font-size:15px;
  padding:44px 24px 80px;max-width:980px;margin:0 auto}
.kicker{font-family:'IBM Plex Mono',monospace;font-size:11px;
  letter-spacing:0.14em;color:var(--muted);text-transform:uppercase}
h1{font-size:27px;font-weight:600;letter-spacing:-0.01em;margin-top:4px}
.lead{color:var(--ink);max-width:74ch;margin-top:10px;font-size:15px}
.lead b{font-weight:600}
.meta{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--faint);
  margin-top:12px;text-transform:uppercase;letter-spacing:0.08em}
h2{font-size:15px;font-weight:600;margin:40px 0 8px;
  text-transform:uppercase;letter-spacing:0.05em}
.hl{max-width:78ch}
.hl p{padding:7px 0;border-bottom:1px solid var(--hair);font-size:14.5px}
.hl p:first-child{border-top:2px solid var(--ink)}
.hl .tick{margin-right:2px}
.guide{font-size:12.5px;color:var(--muted);margin-bottom:10px;max-width:80ch}
.twrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
thead th{font-size:11px;font-weight:500;text-transform:uppercase;
  letter-spacing:0.06em;color:var(--muted);text-align:left;
  border-top:2px solid var(--ink);border-bottom:1px solid var(--hair);
  padding:8px 10px 6px;white-space:nowrap}
td{border-bottom:1px solid var(--hair);padding:8px 8px;vertical-align:top}
tbody tr:hover{background:var(--rowhover)}
.num{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;
  white-space:nowrap}
th.r,td.r{text-align:right}
.tick{font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:13.5px}
.name{color:var(--muted);font-size:12.5px}
.buy{color:var(--green)} .sell{color:var(--red)}
.prog,.unk{color:var(--faint)}
.pos{color:var(--red)} .neg{color:var(--green)} .neu{color:var(--muted)}
.badge{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;
  color:var(--green);border:1px solid var(--green);border-radius:3px;
  padding:0 5px;margin-left:7px;letter-spacing:0.05em;white-space:nowrap}
.type{font-size:11px;font-weight:600;letter-spacing:0.04em;
  font-family:'IBM Plex Mono',monospace;white-space:nowrap}
a.mlink{color:inherit;text-decoration:none}
a.mlink:hover{text-decoration:underline}
.mut{color:var(--muted)} .fnt{color:var(--faint)}
details{margin-top:14px}
summary{cursor:pointer;font-family:'IBM Plex Mono',monospace;font-size:12px;
  color:var(--muted);padding:8px 0}
summary:hover{color:var(--ink)}
.foot{margin-top:48px;font-size:13px;color:var(--muted);max-width:78ch;
  border-top:1px solid var(--hair);padding-top:16px}
.foot p{margin-bottom:8px}
.stale{border:1px solid var(--red);color:var(--red);
  padding:10px 14px;border-radius:4px;margin-top:14px;font-size:14px}
"""


def fmt_pct(g):
    return f"{g*100:+.1f} %".replace(".", ",") if g is not None else "–"


def fmt_nok(v, kr=True):
    if not v:
        return None
    suffix = " kr" if kr else ""
    if v >= 1e6:
        tall = f"{v/1e6:.1f}".replace(".0", "").replace(".", ",")
        return f"{tall} mill.{suffix}"
    if v >= 1e3:
        return f"{round(v/1e3):.0f}&nbsp;000{suffix}"
    return f"{v:.0f}{suffix}"


def fmt_mcap(v):
    if not v:
        return "–"
    if v >= 1e9:
        return f"{v/1e9:.1f}".replace(".", ",") + " mrd"
    return f"{v/1e6:.0f} mill"


def est_amount(c, side):
    """Samlet beløp for kjøp/salg. Der pris ikke sto i meldingen estimeres
    beløpet som volum x dagens kurs — returnerer (beløp, er_estimat)."""
    known = c.get(f"{side}_amount") or 0
    vol = c.get(f"{side}_vol_noamt") or 0
    price = c.get("price")
    if vol and price:
        return known + vol * price, True
    return (known or None), False


def growth_cls(ig, hg):
    if ig is None or hg is None:
        return "neu"
    return "neg" if ig < hg else "pos"


def build_highlights(companies):
    """1-3 setninger i klartekst om det mest interessante akkurat nå."""
    items = []
    for tk, c in companies.items():
        if not c.get("n_buy"):
            continue
        ig, hg = c.get("implied_growth"), c.get("hist_fcf_growth")
        cheap = ig is not None and hg is not None and ig < hg
        amt, approx = est_amount(c, "buy")
        items.append(((c.get("cluster", False), cheap, c["n_buy"], amt or 0),
                      tk, c, amt, approx))
    items.sort(key=lambda x: x[0], reverse=True)

    out = []
    for _, tk, c, amt, approx in items[:3]:
        ig, hg = c.get("implied_growth"), c.get("hist_fcf_growth")
        nm = escape(c.get("name") or c.get("issuer") or tk)
        if c["n_buy"] >= 2:
            s = f"<span class='tick'>{tk}</span> {nm}: <b>{c['n_buy']} innsidekjøp</b> på to uker"
        else:
            who = escape(c["buyers"][0]) if c.get("buyers") else None
            rolle = c.get("top_role")
            hvem = f"{who} ({rolle.lower()})" if who and rolle else (who or "én innsider")
            s = f"<span class='tick'>{tk}</span> {nm}: <b>{hvem} kjøpte</b>"
        if amt:
            s += f" for {'≈ ' if approx else ''}{fmt_nok(amt)}"
        if ig is not None:
            s += f". Børskursen forutsetter {fmt_pct(ig)} årlig vekst"
            if hg is not None:
                s += f" — selskapet har levert {fmt_pct(hg)}"
        s += "."
        out.append(f"<p>{s}</p>")
    return "".join(out)


def company_row(tk, c):
    cluster = '<span class="badge">CLUSTER</span>' if c.get("cluster") else ""
    nm = escape(c.get("name") or c.get("issuer") or "")
    buyers = escape(", ".join(c.get("buyers", [])[:4]))

    def cell(n, side, cls, word):
        if not n:
            return '<span class="fnt">–</span>'
        amt, approx = est_amount(c, side)
        txt = f"{n} {word}"
        if amt:
            txt += f" · {'≈ ' if approx else ''}{fmt_nok(amt, kr=False)}"
        return f'<span class="{cls}">{txt}</span>'

    ig, hg = c.get("implied_growth"), c.get("hist_fcf_growth")
    if c.get("sector") == "Financial Services":
        ig = hg = None  # FCF-tall er meningsløse for bank/forsikring
    return f"""<tr>
  <td><span class="tick">{tk}</span>{cluster}<br>
      <span class="name">{nm}</span></td>
  <td class="num" title="{buyers}">{cell(c['n_buy'], 'buy', 'buy', 'kjøp')}</td>
  <td class="num">{cell(c['n_sell'], 'sell', 'sell', 'salg')}</td>
  <td class="num r {growth_cls(ig, hg)}">{fmt_pct(ig)}</td>
  <td class="num r mut">{fmt_pct(hg)}</td>
  <td class="num r mut">{fmt_mcap(c.get('market_cap'))}</td>
</tr>"""


TYPE_CLS = {"KJØP": "buy", "SALG": "sell", "PROGRAM": "prog", "UKJENT": "unk"}


def message_row(m):
    d = f"{m['published'][8:10]}.{m['published'][5:7]}"
    cls = TYPE_CLS.get(m["type"], "unk")
    who = escape(m.get("name") or "")
    if m.get("role") and who:
        who += f' <span class="fnt">({m["role"]})</span>'
    elif m.get("role"):
        who = m["role"]
    amt = fmt_nok(m.get("amount"))
    return f"""<tr>
  <td class="num fnt">{d}</td>
  <td class="tick">{escape(m['ticker'] or '–')}</td>
  <td><span class="type {cls}">{m['type']}</span></td>
  <td>{who or '<span class="fnt">–</span>'}</td>
  <td class="num r">{amt or '<span class="fnt">–</span>'}</td>
  <td><a class="mlink" href="{m['url']}" target="_blank" rel="noopener">{escape(m['title'][:90])}</a></td>
</tr>"""


MSG_HEAD = """<thead><tr><th>Dato</th><th>Ticker</th><th>Type</th>
<th>Innsider</th><th class="r">Beløp</th><th>Melding</th></tr></thead>"""


def render_site(data, path):
    a = data["assumptions"]
    gen = datetime.fromisoformat(data["generated"]).strftime("%d.%m.%Y %H:%M UTC")
    signal_msgs = [m for m in data["messages"] if m["type"] != "PROGRAM"]
    prog_msgs = [m for m in data["messages"] if m["type"] == "PROGRAM"]
    n_buy = sum(1 for m in signal_msgs if m["type"] == "KJØP")
    n_sell = sum(1 for m in signal_msgs if m["type"] == "SALG")

    highlights = build_highlights(data["companies"])
    comp_rows = "".join(company_row(tk, c)
                        for tk, c in data["companies"].items())
    sig_rows = "".join(message_row(m) for m in signal_msgs[:40])
    prog_rows = "".join(message_row(m) for m in prog_msgs[:40])

    html = f"""<!doctype html>
<html lang="no"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Innsidekart — innsidekjøp og hva markedet priser inn, Oslo Børs</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>

<div class="kicker">Oslo Børs · meldepliktige handler · siste {data['window_days']} dager</div>
<h1>Innsidekart</h1>
<p class="lead">Når ledelsen eller styret handler aksjer i eget selskap, må det
meldes til børsen samme dag. <b>Innsidekjøp er et av de mer pålitelige
signalene i aksjemarkedet</b> — innsidere kjøper når de mener prisen er for
lav. Siste to uker: {n_buy} kjøp og {n_sell} salg. Opsjonstildelinger og
aksjeprogrammer er rutine uten signalverdi og er skilt ut nederst.</p>
<div class="meta">Oppdatert {gen} · WACC {a['wacc']*100:.0f} % ·
terminalvekst {a['terminal_g']*100:.1f} % · {a['stage1_years']} års horisont</div>
<div class="stale" id="stale" hidden>Dataene er over to døgn gamle —
den nattlige oppdateringen har trolig feilet.</div>

<h2>Akkurat nå</h2>
<div class="hl">{highlights or '<p class="fnt">Ingen innsidekjøp siste to uker.</p>'}</div>

<h2>Kjøp og salg per selskap</h2>
<p class="guide"><b>«Markedet krever»</b> er den årlige kontantstrømveksten
som må til for å forsvare dagens børskurs (reverse-DCF) — <b>«har levert»</b>
er hva selskapet faktisk har klart historisk. Grønt krav = markedet forventer
mindre enn selskapet har levert; innsidekjøp dér er det interessante signalet.
≈ betyr at beløpet er anslått fra antall aksjer × dagens kurs.
CLUSTER = to eller flere innsidekjøp på to uker.</p>
<div class="twrap"><table>
<thead><tr><th>Selskap</th><th>Innsidekjøp</th><th>Innsidesalg</th>
<th class="r" title="Årlig FCF-vekst som forsvarer dagens kurs">Markedet krever</th>
<th class="r" title="Historisk årlig FCF-vekst">Har levert</th>
<th class="r">Børsverdi</th></tr></thead>
<tbody>{comp_rows}</tbody>
</table></div>

<h2>Meldingene</h2>
<div class="twrap"><table>
{MSG_HEAD}
<tbody>{sig_rows}</tbody>
</table></div>
<details><summary>+ {len(prog_msgs)} rutinemeldinger (opsjoner, tildelinger,
aksjeprogrammer) — klikk for å vise</summary>
<div class="twrap"><table>
{MSG_HEAD}
<tbody>{prog_rows}</tbody>
</table></div></details>

<div class="foot">
<p><b>Metode.</b> «Markedet krever» løser for den 10-årige FCF-veksten som
gjør at nåverdien av fremtidige kontantstrømmer (WACC {a['wacc']*100:.0f} %,
Gordon-terminal {a['terminal_g']*100:.1f} %) er lik dagens selskapsverdi
(enterprise value = markedsverdi + gjeld − kontanter). Banker og forsikring
får ikke estimat — kontantstrømmodeller gir ikke mening der.</p>
<p><b>Data.</b> Kjøp/salg, volum og beløp leses maskinelt fra meldingstekst
og MAR-vedlegg. Beløp merket ≈ er anslått fra volum × dagens kurs fordi
prisen ikke lot seg lese; felter vi ikke klarer å tolke vises som «–» og
lenker til originalmeldingen. Samme handel publisert på norsk og engelsk
telles én gang.</p>
<p>Datakilder: Newsweb (Euronext Oslo) og Yahoo Finance.
Dette er et analyseverktøy, ikke investeringsråd.</p>
</div>

<script>
if (Date.now() - new Date("{data['generated']}").getTime() > 48*3600*1000)
  document.getElementById("stale").hidden = false;
</script>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
