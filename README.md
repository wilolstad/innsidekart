# Innsidekart

Innsidehandler på Oslo Børs + hva markedet priser inn (reverse-DCF).
Statisk side som regenereres hver natt — null hostingkostnad.

Live: https://wilolstad.github.io/innsidekart/

## Hva den gjør

1. Henter meldepliktige handler for primærinnsidere (kategori 1102) fra
   Newsweb sitt åpne API, siste 14 dager.
2. Klassifiserer hver melding som KJØP / SALG / PROGRAM / UKJENT og trekker
   ut volum, pris, beløp, navn og rolle (`newsweb.py`). Parserekkefølge:
   tittel → brødtekst → MAR-PDF-vedlegg (tabellbevisst via pdfplumber).
   PROGRAM = opsjoner/tildelinger/aksjeprogram — holdes utenfor signaltallene.
3. Lagrer alt i `data/transactions.ndjson` (append-only, committes av
   GitHub-runneren hver natt). `build_db.py` materialiserer SQLite ved behov.
4. For selskaper med aktivitet: henter markedsverdi og fri kontantstrøm via
   yfinance (`TICKER.OL`), og løser med bisection for FCF-veksten som gjør
   DCF-verdi = enterprise value (markedsverdi + gjeld − kontanter).
   To-stegs modell: 10 år + Gordon-terminal, WACC 9 %, terminal 2,5 %.
   Banker/forsikring filtreres (FCF-DCF gir ikke mening der).
5. Flagger cluster-kjøp (2+ innsidekjøp i samme selskap innen 14 dager) og
   skriver `data.json` + `index.html`.

## Kjør lokalt

```bash
pip install requests yfinance pdfplumber
python pipeline.py          # siste 14 dager + side
python backfill.py 1930     # historikk til mars 2021 (resumerbar, throttlet)
python build_db.py          # innsidekart.db for analyse
python backtest.py          # slår innsidekjøp indeksen? (fase 2)
open index.html
```

`backtest.py` måler likevektet meravkastning 1/3/6/12 mnd etter hvert
innsidekjøp mot ^OSEAX, segmentert på cluster og rolle. Entry er første
handelsdag etter publisering (ingen look-ahead), og events uten prisdata
hos Yahoo telles og rapporteres (overlevelsesskjevhet). Til artikkelen:
bytt prisdata til TITLON og faktorjuster med Ødegaards data.

## Kjente begrensninger

- Flat WACC 9 % for alle selskaper. Neste steg: bransje-beta via CAPM.
- Parsingen er regelbasert. Måling juni 2026: type klassifisert ~99 %,
  volum ~84 %, beløp lavere (MAR-PDF-tabeller varierer). Uparsede felter
  vises som «–» og lenker til originalmeldingen — vi gjetter ikke.
- Newsweb publiserer ofte samme handel på norsk og engelsk; dubletter
  fjernes på (ticker, type, volum, dato).
- yfinance er uoffisielt Yahoo-API — greit for hobby, bytt til betalt
  kilde hvis dette skal bli seriøst.
- Ikke backfill lenger tilbake enn mars 2021 (MAR-ikrafttredelse i Norge;
  eldre meldinger har annet format).

## Roadmap

- [x] Parse vedlegg/brødtekst: kjøp/salg, volum, beløp, rolle
- [x] Cluster-kjøp-flagg (2+ innsidekjøp samme selskap innen 14 dager)
- [x] Historisk transaksjonsbase (NDJSON i repo + SQLite lokalt)
- [ ] Backfill til mars 2021 (kjører — `backfill.py` er resumerbar)
- [ ] Backtest-artikkel: slår norske innsidekjøp indeksen?
      (`backtest.py` er klar; venter på full historikk)
- [ ] Per-selskap WACC (bransje-beta)
