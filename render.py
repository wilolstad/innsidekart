"""Renderer data.json til index.html + analyse.html."""

import csv
import json
import os
from datetime import datetime
from html import escape
from urllib.parse import quote

# Fase 0-validering for Pro-abonnementet: e-postfangst. Settes til en
# skjema-URL (f.eks. Tally) når den finnes — tom streng gir mailto-fallback,
# så lista virker fra dag én uten tredjepartskonto.
PRO_SIGNUP_URL = ""
PRO_SIGNUP_EMAIL = "william.olstad@gmail.com"

CSS = """
:root{
  --ink:#16191D; --muted:#667085; --faint:#98A2B3; --hair:#E4E7EC;
  --green:#067647; --red:#B42318; --rowhover:#F9FAFB; --chip:#F2F4F7;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:#FFFFFF;color:var(--ink);
  font-family:'IBM Plex Sans',sans-serif;line-height:1.55;font-size:15px;
  padding:44px 24px 80px;max-width:980px;margin:0 auto}
.nav{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  flex-wrap:wrap}
.kicker{font-family:'IBM Plex Mono',monospace;font-size:11px;
  letter-spacing:0.14em;color:var(--muted);text-transform:uppercase}
.navlink{font-size:13px;color:var(--ink);text-decoration:none;
  border-bottom:1px solid var(--ink);padding-bottom:1px;white-space:nowrap}
.navlink:hover{color:var(--muted);border-color:var(--muted)}
h1{font-size:27px;font-weight:600;letter-spacing:-0.01em;margin-top:4px}
.lead{color:var(--ink);max-width:74ch;margin-top:10px;font-size:15px}
.lead b{font-weight:600}
.stats{display:flex;gap:26px;flex-wrap:wrap;margin-top:16px;
  border-top:2px solid var(--ink);padding-top:10px}
.stat .v{font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:17px}
.stat .l{font-size:11px;color:var(--muted);text-transform:uppercase;
  letter-spacing:0.06em}
.meta{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--faint);
  margin-top:12px;text-transform:uppercase;letter-spacing:0.08em}
h2{font-size:15px;font-weight:600;margin:40px 0 8px;
  text-transform:uppercase;letter-spacing:0.05em}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));
  gap:12px}
.scard{border:1px solid var(--hair);border-radius:4px;padding:14px 16px}
.slabel{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;
  letter-spacing:0.08em;text-transform:uppercase;display:inline-block;
  padding:2px 7px;border-radius:3px;background:var(--chip);
  color:var(--muted);margin-bottom:9px}
.slabel.strong{background:var(--green);color:#fff}
.slabel.good{color:var(--green);background:#E7F4EE}
.slabel.warn{color:var(--red);background:#FBEAE7}
.scard .stxt{font-size:13.5px;margin-top:5px;color:var(--ink)}
.bars{margin-top:11px}
.brow{display:flex;align-items:center;gap:8px;margin-top:5px}
.blbl{font-size:11px;color:var(--muted);width:118px;flex:none}
.btrack{flex:1;height:7px;background:var(--chip);border-radius:2px;
  position:relative}
.bfill{position:absolute;left:0;top:0;height:7px;border-radius:2px}
.bfill.ink{background:var(--faint)} .bfill.grn{background:var(--green)}
.bval{font-family:'IBM Plex Mono',monospace;font-size:11.5px;width:56px;
  text-align:right;flex:none;font-variant-numeric:tabular-nums}
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
.probox{border:2px solid var(--ink);margin-top:40px;padding:18px 20px 16px}
.probox .pk{font-family:'IBM Plex Mono',monospace;font-size:11px;
  font-weight:600;letter-spacing:0.14em;text-transform:uppercase}
.probox .pk .soon{color:var(--muted);font-weight:400}
.probox .pfeat{font-size:14px;margin-top:9px;max-width:78ch}
.probox .phon{font-size:13px;color:var(--muted);margin-top:7px;max-width:78ch}
.probox .prow{display:flex;align-items:center;gap:14px;flex-wrap:wrap;
  margin-top:13px}
.pbtn{display:inline-block;background:var(--ink);color:#fff;padding:8px 15px;
  font-size:13px;font-weight:600;text-decoration:none;white-space:nowrap}
.pbtn:hover{background:var(--muted)}
.pfound{font-size:12.5px;color:var(--ink)}
.pfine{font-family:'IBM Plex Mono',monospace;font-size:10.5px;
  color:var(--faint);margin-top:11px}
article{max-width:720px}
article h2{margin-top:36px}
article p{margin:12px 0;font-size:15px}
article ul{margin:12px 0 12px 22px}
article li{margin:7px 0;font-size:15px}
article .tablenote{font-size:12.5px;color:var(--muted)}
article .srcs{font-size:12.5px;color:var(--muted);margin-top:20px}
article table{margin-top:14px}
"""

HEAD = """<!doctype html>
<html lang="no"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{css}</style></head><body>
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


def signal_cards(companies):
    """Inntil 3 kort om de mest interessante kjøpene, med søyle-sammenligning
    av hva markedet forventer og hva selskapet har levert."""
    items = []
    for tk, c in companies.items():
        if not c.get("n_buy"):
            continue
        if c.get("sector") == "Financial Services":
            ig = hg = None
        else:
            ig, hg = c.get("implied_growth"), c.get("hist_fcf_growth")
        cheap = ig is not None and hg is not None and ig < hg
        amt, approx = est_amount(c, "buy")
        items.append(((c.get("cluster", False), cheap, c["n_buy"], amt or 0),
                      tk, c, ig, hg, cheap, amt, approx))
    items.sort(key=lambda x: x[0], reverse=True)

    cards = []
    for _, tk, c, ig, hg, cheap, amt, approx in items[:3]:
        cluster = c.get("cluster", False)
        if cluster and cheap:
            label, lcls = "Sterkt kjøpssignal", "strong"
        elif cheap:
            label, lcls = "Kjøp i lavt priset selskap", "good"
        elif ig is not None:
            label, lcls = "Kjøp tross høy prising", "warn"
        else:
            label, lcls = "Kjøpssignal", ""
        nm = escape(c.get("name") or c.get("issuer") or "")
        if c["n_buy"] >= 2:
            txt = f"<b>{c['n_buy']} innsidekjøp</b> på to uker"
        else:
            who = escape(c["buyers"][0]) if c.get("buyers") else None
            rolle = c.get("top_role")
            hvem = f"{who} ({rolle.lower()})" if who and rolle else (who or "Én innsider")
            txt = f"<b>{hvem}</b> kjøpte"
        if amt:
            txt += f" for {'≈ ' if approx else ''}{fmt_nok(amt)}"
        txt += "."

        bars = ""
        if ig is not None and hg is not None:
            mx = max(abs(ig), abs(hg)) or 1
            wi, wh = max(abs(ig)/mx*100, 3), max(abs(hg)/mx*100, 3)
            bars = f"""<div class="bars">
  <div class="brow"><span class="blbl">markedet forventer</span>
    <div class="btrack"><div class="bfill ink" style="width:{wi:.0f}%"></div></div>
    <span class="bval">{fmt_pct(ig)}</span></div>
  <div class="brow"><span class="blbl">selskapet har levert</span>
    <div class="btrack"><div class="bfill grn" style="width:{wh:.0f}%"></div></div>
    <span class="bval">{fmt_pct(hg)}</span></div>
</div>"""
        elif ig is not None:
            bars = f"""<div class="bars"><div class="brow">
  <span class="blbl">markedet forventer</span>
  <div class="btrack"><div class="bfill ink" style="width:50%"></div></div>
  <span class="bval">{fmt_pct(ig)}</span></div></div>"""

        cards.append(f"""<div class="scard">
<span class="slabel {lcls}">{label}</span>
<div><span class="tick">{tk}</span> <span class="name">{nm}</span></div>
<p class="stxt">{txt}</p>
{bars}</div>""")
    return "".join(cards)


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


def pro_box():
    """Venteliste-boks for Pro (fase 0: måler betalingsvilje før bygging)."""
    if PRO_SIGNUP_URL:
        href = PRO_SIGNUP_URL
    else:
        subject = quote("Innsidekart Pro — sett meg på lista")
        body = quote("Sett meg på Pro-lista. Send e-posten som den er — "
                     "du trenger ikke skrive noe mer.")
        href = f"mailto:{PRO_SIGNUP_EMAIL}?subject={subject}&body={body}"
    return f"""<div class="probox">
<div class="pk">Innsidekart Pro <span class="soon">· under bygging</span></div>
<p class="pfeat">Full historikk for hvert selskap siden 2021 ·
shortregisteret med navngitte fond · selskapenes egne tilbakekjøp ·
e-postvarsler per ticker.</p>
<p class="phon">Komplett data, ikke «signaler» —
<a class="mlink" href="analyse.html"><b>analysen</b></a> viser hvorfor vi
aldri kommer til å selge kjøpsanbefalinger. 99 kr/mnd ved lansering.</p>
<div class="prow">
  <a class="pbtn" href="{href}">Sett meg på lista →</a>
  <span class="pfound">De første 50 låser <b>49 kr/mnd — for alltid</b>.</span>
</div>
<p class="pfine">Ingen spam: én e-post når Pro lanseres, maks to underveis.</p>
</div>"""


def render_site(data, path):
    a = data["assumptions"]
    gen = datetime.fromisoformat(data["generated"]).strftime("%d.%m.%Y %H:%M UTC")
    signal_msgs = [m for m in data["messages"] if m["type"] != "PROGRAM"]
    prog_msgs = [m for m in data["messages"] if m["type"] == "PROGRAM"]
    n_buy = sum(1 for m in signal_msgs if m["type"] == "KJØP")
    n_sell = sum(1 for m in signal_msgs if m["type"] == "SALG")
    n_cluster = sum(1 for c in data["companies"].values() if c.get("cluster"))

    cards = signal_cards(data["companies"])
    comp_rows = "".join(company_row(tk, c)
                        for tk, c in data["companies"].items())
    sig_rows = "".join(message_row(m) for m in signal_msgs[:40])
    prog_rows = "".join(message_row(m) for m in prog_msgs[:40])

    html = HEAD.format(title="Innsidekart — innsidekjøp og hva markedet "
                             "priser inn, Oslo Børs", css=CSS) + f"""
<div class="nav">
<div class="kicker">Oslo Børs · meldepliktige handler · siste {data['window_days']} dager</div>
<a class="navlink" href="analyse.html">Analyse: slår innsidekjøp børsen? →</a>
</div>
<h1>Innsidekart</h1>
<p class="lead">Når ledelsen eller styret handler aksjer i eget selskap, må
det meldes til børsen samme dag. Denne siden leser alle meldingene, hver
natt, og viser hvem som handlet og hva børskursen allerede forutsetter.
<b>Fem års fasit: innsidekjøp flest slår ikke børsen</b> —
<a class="mlink" href="analyse.html"><b>analysen viser hvorfor</b></a>,
og hvilket hjørne av dem som likevel står seg.</p>
<div class="stats">
  <div class="stat"><div class="v">{data.get('base_total', '–')}</div>
    <div class="l">handler i basen</div></div>
  <div class="stat"><div class="v buy">{n_buy}</div>
    <div class="l">kjøp siste 14 d</div></div>
  <div class="stat"><div class="v sell">{n_sell}</div>
    <div class="l">salg siste 14 d</div></div>
  <div class="stat"><div class="v">{n_cluster}</div>
    <div class="l">cluster-selskaper</div></div>
</div>
<div class="meta">Oppdatert {gen} · WACC {a['wacc']*100:.0f} % ·
terminalvekst {a['terminal_g']*100:.1f} % · {a['stage1_years']} års horisont</div>
<div class="stale" id="stale" hidden>Dataene er over to døgn gamle —
den nattlige oppdateringen har trolig feilet.</div>

<h2>Akkurat nå</h2>
<div class="cards">{cards or '<p class="fnt">Ingen innsidekjøp siste to uker.</p>'}</div>

{pro_box()}

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
Dette er et analyseverktøy, ikke investeringsråd.
<a class="mlink" href="https://github.com/wilolstad/innsidekart"><b>Kode og
rådata på GitHub</b></a>.</p>
</div>

<script>
if (Date.now() - new Date("{data['generated']}").getTime() > 48*3600*1000)
  document.getElementById("stale").hidden = false;
</script>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def results_table(csv_path):
    seg_label = {"Alle kjøp": "Alle kjøp", "Cluster-kjøp": "Cluster-kjøp",
                 "CEO/CFO/styreleder": "CEO/CFO/styreleder"}
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(f"""<tr>
  <td>{seg_label.get(r['segment'], r['segment'])}</td>
  <td class="num">{r['horisont']}</td>
  <td class="num r">{int(r['n'])}</td>
  <td class="num r">{float(r['snitt'])*100:+.1f} %</td>
  <td class="num r">{float(r['median'])*100:+.1f} %</td>
  <td class="num r">{float(r['hit_rate'])*100:.0f} %</td>
</tr>""".replace(".", ","))
    return """<div class="twrap"><table>
<thead><tr><th>Segment</th><th>Horisont</th><th class="r">N</th>
<th class="r">Snitt</th><th class="r">Median</th>
<th class="r">Hit-rate</th></tr></thead>
<tbody>""" + "".join(rows) + "</tbody></table></div>"


def render_article(data, path):
    if not (os.path.exists("backtest_results.csv")
            and os.path.exists("backtest_meta.json")):
        print("hopper over analyse.html (ingen backtest-resultater)")
        return
    from article import ARTICLE_BODY
    with open("backtest_meta.json", encoding="utf-8") as f:
        meta = json.load(f)
    body = ARTICLE_BODY.format(
        results_table=results_table("backtest_results.csv"),
        base_total=data.get("base_total", "–"),
        n_missing=meta["n_missing_prices"],
        **{k: v for k, v in meta.items() if k != "n_missing_prices"})
    html = (HEAD.format(title="Slår norske innsidekjøp børsen? — Innsidekart",
                        css=CSS)
            + f"<article>{body}{pro_box()}</article></body></html>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
