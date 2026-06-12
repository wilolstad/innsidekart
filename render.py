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
h2{font-size:15px;font-weight:600;margin:42px 0 10px;
  text-transform:uppercase;letter-spacing:0.05em}
.twrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13.5px}
thead th{font-size:11px;font-weight:500;text-transform:uppercase;
  letter-spacing:0.06em;color:var(--muted);text-align:left;
  border-top:2px solid var(--ink);border-bottom:1px solid var(--hair);
  padding:8px 10px 6px;white-space:nowrap}
td{border-bottom:1px solid var(--hair);padding:9px 10px;vertical-align:top}
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
.foot{margin-top:48px;font-size:13px;color:var(--muted);max-width:78ch;
  border-top:1px solid var(--hair);padding-top:16px}
.foot p{margin-bottom:8px}
.stale{border:1px solid var(--red);color:var(--red);
  padding:10px 14px;border-radius:4px;margin-top:14px;font-size:14px}
"""


def fmt_pct(g):
    return f"{g*100:+.1f} %" if g is not None else "–"


def fmt_nok(v):
    if not v:
        return None
    if v >= 1e6:
        return f"{v/1e6:.1f} MNOK".replace(".", ",")
    return f"{v:,.0f}".replace(",", " ") + " NOK"


def fmt_mcap(v):
    if not v:
        return "–"
    if v >= 1e9:
        return f"{v/1e9:.1f}".replace(".", ",") + " mrd"
    return f"{v/1e6:.0f} mill"


def growth_cls(ig, hg):
    if ig is None:
        return "neu"
    if hg is None:
        return "neu"
    return "neg" if ig < hg else "pos"


def company_row(tk, c):
    cluster = '<span class="badge">CLUSTER</span>' if c.get("cluster") else ""
    nm = escape(c.get("name") or c.get("issuer") or "")
    buyers = escape(", ".join(c.get("buyers", [])[:4]))

    def activity(n, nok, cls):
        if not n:
            return '<span class="fnt">–</span>'
        amt = fmt_nok(nok)
        s = f'<span class="{cls}">{n}'
        s += f' · {amt}' if amt else ""
        return s + "</span>"

    ig, hg = c.get("implied_growth"), c.get("hist_fcf_growth")
    has_val = "market_cap" in c
    return f"""<tr>
  <td><span class="tick">{tk}</span>{cluster}<br>
      <span class="name">{nm}</span></td>
  <td class="num" title="{buyers}">{activity(c['n_buy'], c['buy_nok'], 'buy')}</td>
  <td class="num">{activity(c['n_sell'], c['sell_nok'], 'sell')}</td>
  <td class="num r {growth_cls(ig, hg)}">{fmt_pct(ig) if has_val else '–'}</td>
  <td class="num r mut">{fmt_pct(hg) if has_val else '–'}</td>
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


def render_site(data, path):
    a = data["assumptions"]
    gen = datetime.fromisoformat(data["generated"]).strftime("%d.%m.%Y %H:%M UTC")
    n_buy = sum(1 for m in data["messages"] if m["type"] == "KJØP")
    n_sell = sum(1 for m in data["messages"] if m["type"] == "SALG")

    comp_rows = "".join(company_row(tk, c)
                        for tk, c in data["companies"].items())
    msg_rows = "".join(message_row(m) for m in data["messages"][:40])

    html = f"""<!doctype html>
<html lang="no"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Innsidekart — innsidekjøp og hva markedet priser inn, Oslo Børs</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>

<div class="kicker">Oslo Børs · meldepliktige handler · siste {data['window_days']} dager</div>
<h1>Innsidekart</h1>
<p class="lead">Ledelse og styremedlemmer må melde alle handler i eget selskap
til børsen. <b>Innsidekjøp</b> er historisk et av de mer pålitelige signalene
i aksjemarkedet — innsidere kjøper når de mener prisen er for lav. Tabellen
viser hvem som har kjøpt og solgt siste to uker ({n_buy} kjøp, {n_sell} salg),
og hvilken årlig kontantstrømvekst dagens børskurs allerede forutsetter
(<b>«priset inn»</b>, reverse-DCF). Kombinasjonen er poenget: innsidekjøp i
selskaper der markedet priser inn lite, er det mest interessante hjørnet.</p>
<div class="meta">Oppdatert {gen} · WACC {a['wacc']*100:.0f} % ·
terminalvekst {a['terminal_g']*100:.1f} % · {a['stage1_years']} års horisont</div>
<div class="stale" id="stale" hidden>Dataene er over to døgn gamle —
den nattlige oppdateringen har trolig feilet.</div>

<h2>Selskaper med innsideaktivitet</h2>
<div class="twrap"><table>
<thead><tr><th>Selskap</th><th>Innsidekjøp</th><th>Innsidesalg</th>
<th class="r">Priset inn</th><th class="r">Levert (FCF)</th>
<th class="r">Mcap</th></tr></thead>
<tbody>{comp_rows}</tbody>
</table></div>

<h2>Siste meldinger</h2>
<div class="twrap"><table>
<thead><tr><th>Dato</th><th>Ticker</th><th>Type</th><th>Innsider</th>
<th class="r">Beløp</th><th>Melding</th></tr></thead>
<tbody>{msg_rows}</tbody>
</table></div>

<div class="foot">
<p><b>Metode.</b> «Priset inn» er den 10-årige FCF-veksten som gjør at
nåverdien av fremtidige kontantstrømmer (WACC {a['wacc']*100:.0f} %,
Gordon-terminal {a['terminal_g']*100:.1f} %) er lik dagens selskapsverdi
(enterprise value = markedsverdi + gjeld − kontanter). Grønt tall = selskapet
har historisk levert mer enn markedet nå krever. Banker og forsikring får
ikke estimat — FCF-modeller gir ikke mening der.</p>
<p><b>Klassifisering.</b> Kjøp/salg leses maskinelt fra meldingstekst og
MAR-vedlegg. PROGRAM er opsjoner, tildelinger og aksjeprogrammer — rutinemessige
transaksjoner med liten signalverdi, holdt utenfor kjøps- og salgstallene.
Beløp vises der volum og pris lar seg lese; resten lenker til
originalmeldingen. CLUSTER = to eller flere innsidekjøp i samme selskap
innenfor vinduet.</p>
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
