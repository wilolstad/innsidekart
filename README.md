# Innsidekart

Innsidehandler på Oslo Børs + hva markedet priser inn (reverse-DCF).
Statisk side som regenereres hver natt — null hostingkostnad.

## Hva den gjør

1. Henter meldepliktige handler for primærinnsidere (kategori 1102) fra
   Newsweb sitt åpne API, siste 14 dager.
2. For hvert unikt selskap: henter markedsverdi og fri kontantstrøm via
   yfinance (`TICKER.OL`).
3. Reverse-DCF (to-stegs, 10 år + Gordon-terminal, WACC 9 %, terminal 2,5 %):
   løser med bisection for FCF-veksten som gjør DCF-verdi = enterprise value
   (markedsverdi + gjeld − kontanter — FCF-en er til hele firmaet, så
   sammenligningsgrunnlaget må inkludere gjelden).
4. Skriver `data.json` og `index.html`.

## Kjør lokalt

```bash
pip install requests yfinance
python pipeline.py
open index.html
```

## Deploy (gratis, ~10 min)

1. Push repoet til GitHub.
2. Settings → Pages → Source: **GitHub Actions**.
3. Actions-fanen → kjør "Nattlig oppdatering" manuelt én gang.
4. Ferdig — siden oppdaterer seg selv 06:30 hver morgen.

## Kjente begrensninger (v1)

- Flat WACC 9 % for alle selskaper. Neste steg: bransje-beta via CAPM.
- Banker/forsikring og selskaper med negativ FCF får ikke implied growth
  (riktig oppførsel — FCF-DCF gir ikke mening der).
- Skiller ikke kjøp fra salg ennå. Transaksjonsdetaljene ligger i
  PDF-vedlegg på Newsweb; parsing av disse er den viktigste v2-featuren.
- yfinance er uoffisielt Yahoo-API — greit for hobby, bytt til en betalt
  kilde hvis dette skal bli seriøst.

## Roadmap

- [ ] Parse PDF-vedlegg: kjøp/salg, volum, rolle (CEO/CFO/styre)
- [ ] Cluster-kjøp-flagg (flere innsidere samme uke)
- [ ] Historisk database (SQLite) i stedet for kun siste 14 dager
- [ ] Backtest: slår norske innsidekjøp indeksen?
- [ ] Per-selskap WACC (bransje-beta)
