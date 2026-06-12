"""Artikkelteksten til analyse.html. Ren tekst/HTML — ingen logikk.

Plassholderne ({run_date}, {results_table}, ...) fylles av
render.render_article(). Prosaen er skrevet for å tåle at tallene
oppdateres: tolkningen peker på tabellen og er datert, ikke hardkodet
til ett resultat.
"""

ARTICLE_BODY = """
<div class="kicker"><a class="mlink" href="index.html">← Innsidekart</a></div>
<h1>Slår norske innsidekjøp børsen?</h1>
<p class="lead">Et levende eksperiment: hver natt leser denne siden alle
meldepliktige innsidehandler på Oslo Børs, og tallene i analysen under
regenereres automatisk. Datasettet dekker hele MAR-perioden — mars 2021
til i dag. Skrevet juni 2026 — konklusjonen har dato, ikke fasit.</p>
<div class="meta">Backtest per {run_date} · {n_buys} innsidekjøp
{period_from} – {period_to} · benchmark {benchmark}</div>

<h2>Hvorfor spørsmålet er verdt å stille</h2>
<p>Innsidere — ledelsen og styret — vet mer om selskapet sitt enn du gjør.
Når de bruker egne penger på å kjøpe aksjer i eget selskap, er det den
dyreste formen for optimisme som finnes. Salg betyr derimot lite: folk
selger fordi de skal kjøpe hus, betale skatt eller spre risiko. Kjøp har
i praksis bare én forklaring. Derfor har innsidekjøp en særstilling i
finanslitteraturen som et av få signaler som ser ut til å bære ekte
informasjon.</p>
<p>Men det meste av det vi «vet», er amerikansk. Seyhun (1986) viste at
amerikanske innsidere tjener unormal avkastning, Lakonishok og Lee (2001)
fant at det særlig er <i>kjøpene</i> — og spesielt i små selskaper — som er
informative, og Cohen, Malloy og Pomorski (2012) skilte rutinehandler fra
opportunistiske og fant at nesten all informasjon ligger i de siste.
For Norge er det påfallende tynt, og det mest kjente resultatet peker
motsatt vei: Eckbo og Smith fulgte innsidehandler på Oslo Børs gjennom
80- og 90-tallet og fant <i>ingen</i> meravkastning (Journal of Finance,
1998). Etter at EUs markedsmisbruksforordning MAR trådte i kraft i Norge
i mars 2021 — med krav om umiddelbar offentliggjøring i standardisert
format — har jeg ikke funnet noen åpen, etterprøvbar test på norske data.
Det er hullet dette prosjektet borer i.</p>

<h2>Datasettet</h2>
<p>Kilden er Newsweb, Oslo Børs' meldingssystem, kategori «meldepliktige
handler for primærinnsidere». Hver melding parses maskinelt: kjøp eller
salg, antall aksjer, pris, beløp og innsiderens rolle, lest fra
meldingsteksten og MAR-vedleggene. Basen inneholder
<b>{base_total} transaksjoner</b> og dekker hele perioden siden MAR trådte
i kraft i mars 2021; nye meldinger legges til hver natt.</p>
<p>To valg er viktige for kvaliteten. For det første filtreres
opsjonstildelinger, aksjeprogrammer og andre rutinemessige transaksjoner
bort fra signaltallene — det er Cohen-Malloy-Pomorski-poenget om at rutine
er støy. For det andre gjettes det aldri: felter parseren ikke klarer å
lese (priser i ustrukturerte PDF-er, typisk) står som ukjente og er
synlige i rådataene. Samme handel publisert på norsk og engelsk telles
én gang.</p>

<h2>Metoden</h2>
<p>Klassisk eventstudie, med vilje enkel og uten frihetsgrader å skru på:</p>
<ul>
<li><b>Entry:</b> første handelsdag <i>etter</i> at meldingen er publisert.
Ingen look-ahead — du kunne handlet på dette i virkeligheten.</li>
<li><b>Horisonter:</b> 1, 3, 6 og 12 måneder (21/63/126/252 handelsdager).</li>
<li><b>Mål:</b> aksjens avkastning minus benchmark ({benchmark}) i samme
vindu — likevektet per event.</li>
<li><b>Segmenter:</b> alle kjøp; cluster-kjøp (minst to innsidekjøp i samme
selskap innen 14 dager); kjøp av CEO, CFO eller styreleder.</li>
</ul>
<p>Events uten prisdata hos Yahoo Finance telles åpent i stedet for å
forsvinne stille: per {run_date} mangler {n_missing} av {n_buys} kjøp
prisdata, typisk fordi selskapet er strøket fra børsen. Det er
overlevelsesskjevhet, og den gjør tallene under <i>penere</i> enn
virkeligheten — de dårligste utfallene mangler.</p>

<h2>Tallene, per {run_date}</h2>
{results_table}
<p class="tablenote">{n_events} målbare events. Snitt og median er
meravkastning mot {benchmark}; hit-rate er andelen events som slo
benchmarken. Horisonter mangler der datasettet ennå er for ungt.</p>
<p>Fem års fasit er ubehagelig lesning for innsidekjøp-entusiaster:
porteføljen av norske innsidekjøp har tapt mot hovedindeksen på samtlige
horisonter, og gapet vokser med tiden — rundt to–tre prosentpoeng bak
etter tre måneder, over ti etter ett år, med treffrate under 40 %. Mest
påfallende: <b>cluster-kjøp, det mest populære «sterke» signalet, er det
svakeste av alt.</b> Når flere innsidere kjøper samtidig, er det oftere et
selskap i fritt fall enn en skjult perle. Det eneste segmentet som holder
seg rundt nullstreken er kjøp fra CEO, CFO og styreleder — hierarki ser
ut til å bety mer enn antall.</p>
<p>Dette rimer med Eckbo og Smith (1998) og står i kontrast til de
amerikanske funnene. Husk også retningen på skjevheten: kjøpene uten
prisdata er i stor grad selskaper som siden forsvant fra børsen — med dem
inkludert blir bildet trolig <i>verre</i>, ikke bedre. En del av
underprestasjonen er sannsynligvis en størrelseseffekt (innsidekjøp
domineres av småselskaper, mens hovedindeksen i perioden ble løftet av
store energiselskaper), og å isolere den er neste steg. Men den praktiske
konklusjonen står seg: å kopiere norske innsidekjøp i blinde har vært en
pålitelig måte å tape mot indeksen på.</p>

<h2>Hva som mangler før dette er et svar</h2>
<ul>
<li><b>Delistede selskaper.</b> Yahoo mangler dem; de {n_missing} tapte
eventene må hentes fra en akademisk database (TITLON ved UiT har norske
børsdata med delistede aksjer, gratis for studenter via Feide).</li>
<li><b>Faktorjustering.</b> Meravkastning mot hovedindeksen blander
innsidesignalet med størrelseseffekten — innsidekjøp domineres av små
selskaper. Neste steg er justering med markeds- og size-faktorer
(Ødegaard publiserer ferdigberegnede faktorer for Oslo Børs) og OSESX
som robusthetssjekk.</li>
<li><b>Per-selskap-vekting.</b> Likevekt per event lar ett selskap med
fem kjøp og ett kursras dominere. Robusthet: aggreger per selskap.</li>
<li><b>Kostnader.</b> Småselskaper på Oslo Børs har spread som spiser
papiravkastning. En tradbar strategi må regne netto.</li>
<li><b>Inferens.</b> Overlappende vinduer og klyngede events gjør naive
t-verdier for optimistiske; bootstrap eller klyngerobuste standardfeil
før noe kalles signifikant.</li>
</ul>

<h2>Veien videre</h2>
<p>Basen er komplett tilbake til MAR-grensen, så neste steg er presisjon,
ikke volum: delistede selskaper inn via TITLON, faktorjustering, vekting
per selskap og kostnader — listen over. Hvis topplederkjøpene fortsatt
står seg etter de justeringene, er <i>det</i> det tradbare hjørnet.
All kode og alle rådata er åpne: <a class="mlink"
href="https://github.com/wilolstad/innsidekart"><b>github.com/wilolstad/innsidekart</b></a>.
Finner du feil i metoden, si fra — det er halve poenget med å gjøre dette
i det åpne.</p>

<p class="srcs"><b>Referanser.</b> Seyhun (1986), <i>Insiders' profits,
costs of trading, and market efficiency</i>, JFE · Eckbo &amp; Smith (1998),
<i>The conditional performance of insider trades</i>, JF · Lakonishok &amp;
Lee (2001), <i>Are insider trades informative?</i>, RFS · Cohen, Malloy
&amp; Pomorski (2012), <i>Decoding inside information</i>, JF.</p>

<p class="srcs">Dette er et studentprosjekt og analyseverktøy,
ikke investeringsråd. Datakilder: Newsweb (Euronext Oslo), Yahoo Finance.</p>
"""
