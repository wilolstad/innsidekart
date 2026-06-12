"""
Newsweb-klient og transaksjonsparser for meldepliktige handler (MAR).

Klassifiserer hver melding som KJØP / SALG / PROGRAM / UKJENT og trekker ut
volum, pris, beløp, navn og rolle. PROGRAM = opsjoner, tildelinger og
aksjeprogrammer — transaksjoner uten særlig signalverdi.

Parserekkefølge: tittel → brødtekst → PDF-vedlegg (kun når brødteksten
ikke gir volum). Alt regelbasert; meldinger vi ikke klarer å tolke
beholdes som UKJENT i stedet for å gjettes på.
"""

import io
import json
import os
import re
import time

import requests

API = "https://api3.oslo.oslobors.no/v1/newsreader"
CATEGORY_INSIDER = 1102
MESSAGE_URL = "https://newsweb.oslobors.no/message/{id}"
NDJSON_PATH = "data/transactions.ndjson"
THROTTLE = 0.35  # sekunder mellom API-kall


def _get(url, **kw):
    r = requests.get(url, timeout=30, headers={"Accept": "application/json"}, **kw)
    r.raise_for_status()
    return r


def fetch_list(from_date, to_date, category=CATEGORY_INSIDER):
    """Meldingsliste (uten brødtekst) for et datovindu."""
    r = _get(f"{API}/list", params={
        "category": category, "fromDate": from_date, "toDate": to_date,
    })
    out = []
    for m in r.json()["data"]["messages"]:
        if m.get("test"):
            continue
        out.append({
            "messageId": m["messageId"],
            "ticker": m.get("issuerSign", ""),
            "issuer": m.get("issuerName", ""),
            "title": m.get("title", ""),
            "published": m.get("publishedTime", ""),
            "url": MESSAGE_URL.format(id=m["messageId"]),
        })
    return out


def fetch_detail(message_id):
    """Brødtekst + vedleggsliste for én melding."""
    r = _get(f"{API}/message", params={"messageId": message_id})
    msg = r.json()["data"]["message"]
    return {"body": msg.get("body") or "",
            "attachments": msg.get("attachments") or []}


def fetch_attachment_data(message_id, attachment_id):
    """Laster ned ett PDF-vedlegg. Returnerer (tekst, [(volum, pris), ...]).

    MAR-skjemaet er en tabell, så ren tekstuttrekking mister strukturen.
    Vi leser tabellene: to-kolonners rader blir "nøkkel: verdi"-linjer
    (så colon-regexene treffer), og pris/volum-kolonnepar plukkes direkte.
    """
    r = _get(f"{API}/attachment",
             params={"messageId": message_id, "attachmentId": attachment_id})
    if r.content[:4] != b"%PDF":
        return "", []
    text_parts, pairs = [], []
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            for page in pdf.pages[:6]:
                text_parts.append(page.extract_text() or "")
                for table in page.extract_tables() or []:
                    price_col = vol_col = None
                    for row in table:
                        cells = ["" if c is None else " ".join(c.split())
                                 for c in row]
                        nonempty = [c for c in cells if c]
                        # par-vis "nøkkel: verdi" så colon-regexene treffer
                        # uansett om raden er ["Navn", "X"] eller ["a)", "Navn", "X"]
                        for j in range(len(nonempty) - 1):
                            text_parts.append(f"{nonempty[j]}: {nonempty[j+1]}")
                        for i, c in enumerate(cells):
                            low = c.lower()
                            if price_col is None and ("pris" in low or "price" in low):
                                price_col = i
                            if vol_col is None and ("volum" in low or "antall" in low):
                                vol_col = i
                        if price_col is not None and vol_col is not None \
                                and price_col != vol_col:
                            p = _num(cells[price_col]) if price_col < len(cells) else None
                            v = _num(cells[vol_col]) if vol_col < len(cells) else None
                            if p and v:
                                pairs.append((v, p))
    except Exception:
        pass
    return "\n".join(text_parts), pairs


# --- klassifisering -------------------------------------------------------

PROGRAM_WORDS = [
    "opsjon", "option", "tildel", "allocation", "allotment", "grant",
    "aksjeprogram", "spareprogram", "aksjesparing", "incentive", "insentiv",
    "rsu", "psu", "vesting", "bonus", "variabel avlønning", "remuneration",
    "utøv", "exercis", "tegning", "tegnet", "subscri", "tilbakekjøp",
]
SELL_WORDS = ["salg", "solgt", "selger", "sale", "sold", "sells",
              "disposal", "dispos", "avhend", "nedsalg"]
BUY_WORDS = ["kjøp", "kjøpt", "kjøper", "purchas", "acquisition", "acquir",
             "bought", "erverv", "buy"]


def _classify_text(text):
    t = text.lower()
    if any(w in t for w in PROGRAM_WORDS):
        return "PROGRAM"
    sell = min((t.find(w) for w in SELL_WORDS if w in t), default=-1)
    buy = min((t.find(w) for w in BUY_WORDS if w in t), default=-1)
    if sell >= 0 and (buy < 0 or sell < buy):
        return "SALG"
    if buy >= 0:
        return "KJØP"
    return "UKJENT"


def classify(title, body=""):
    cls = _classify_text(title)
    if cls != "UKJENT":
        return cls
    m = re.search(r"(?:karakter|art|nature of the transaction)\s*:?\s*([^\n]{2,80})",
                  body, re.I)
    if m:
        cls = _classify_text(m.group(1))
        if cls != "UKJENT":
            return cls
    return _classify_text(body[:2500])


# --- feltuttrekk ----------------------------------------------------------

NUMBER = r"([\d][\d .,\u00a0\u202f]*\d|\d)"
VOLUME_RE = re.compile(
    r"(?:antall\s+(?:aksjer|egenkapitalbevis)|volum|volume|number of shares)"
    r"\s*[:\s]\s*" + NUMBER, re.I)
PRICE_RE = re.compile(
    r"(?:gjennomsnitt(?:lig)?\s*(?:pris|kurs)|pris(?:\s*per\s*aksje)?|kurs|"
    r"average price|price(?:\(s\))?(?:\s*per\s*share)?)"
    r"\s*(?:of|på|at|per\s+(?:aksje|share))?\s*[:\s]*(?:nok|kr|usd|eur)?\s*"
    + NUMBER, re.I)
NAME_RE = re.compile(r"(?:navn|name)\s*:\s*([^\n:]{2,60})", re.I)
NAME_FALLBACK_RE = re.compile(
    r"(?:navn|name)\s+([A-ZÆØÅ][a-zæøå]+(?:\s+[A-ZÆØÅ][\wæøå.-]+){1,3})")
ROLE_RE = re.compile(
    r"(?:stilling|posisjon|verv|position|status)\s*[:/]\s*([^\n:]{2,50})", re.I)


def _num(s):
    if not s:
        return None
    s = re.sub(r"[A-Za-zÆØÅæøå]", "", s)
    s = re.sub(r"[\s ]", "", s).strip(".,:")
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = (head + tail) if len(tail) == 3 else (head + "." + tail)
        s = s.replace(",", "")
    elif "." in s:
        head, _, tail = s.rpartition(".")
        if len(tail) == 3:
            s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def norm_role(raw):
    if not raw:
        return None
    t = raw.lower()
    if any(w in t for w in ["adm", "administrerende", "ceo", "chief executive",
                            "konsernsjef", "daglig leder", "managing director"]):
        return "CEO"
    if any(w in t for w in ["cfo", "finansdirektør", "chief financial",
                            "økonomidirektør"]):
        return "CFO"
    if any(w in t for w in ["styreleder", "chair"]):
        return "Styreleder"
    if any(w in t for w in ["styremedlem", "board", "varamedlem", "director"]):
        return "Styre"
    if any(w in t for w in ["nærstående", "closely associated"]):
        return "Nærstående"
    if any(w in t for w in ["direktør", "chief", "leder", "evp", "svp",
                            "president", "manager"]):
        return "Ledelse"
    return "Innsider"


PRICE_MAX = 5000      # ingen OSE-aksje koster mer; over = feilparset beløp
AMOUNT_MAX = 2e9      # innsidehandler over 2 mrd NOK = nesten sikkert feil


CORP_RE = re.compile(r"\b(asa?|ab|abp|plc|ltd|as|sparebank(?:en)?|bank|"
                     r"group|holding|invest(?:ment)?s?|capital|pension)\b", re.I)


def extract_fields(text, pairs=None, issuer=None):
    """Trekker volum/pris/beløp/navn/rolle ut av meldingstekst.

    Meldinger kan inneholde flere transaksjoner (flere innsidere) — da
    summeres beløpene og antall distinkte navn telles. `pairs` er
    (volum, pris)-par lest direkte fra MAR-tabellen og vinner over regex.
    Navn som ligner utstederen eller ser ut som selskaper filtreres bort —
    MAR-skjemaet har egne navnefelt for utsteder.
    """
    if pairs:
        volumes = [v for v, _ in pairs]
        prices = [p for _, p in pairs if 0.01 <= p <= PRICE_MAX]
    else:
        volumes = [v for v in (_num(m) for m in VOLUME_RE.findall(text)) if v]
        prices = [p for p in (_num(m) for m in PRICE_RE.findall(text))
                  if p and 0.01 <= p <= PRICE_MAX]
    names = []
    for n in NAME_RE.findall(text) + NAME_FALLBACK_RE.findall(text):
        n = " ".join(n.split()).strip(".,")
        if not n or len(n) < 3 or CORP_RE.search(n):
            continue
        if issuer and (n.lower() in issuer.lower() or issuer.lower() in n.lower()):
            continue
        if n.lower() not in (x.lower() for x in names):
            names.append(n)
    role = None
    m = ROLE_RE.search(text)
    if m:
        role = norm_role(m.group(1))

    amount = None
    if volumes and prices:
        if len(volumes) == len(prices):
            amount = sum(v * p for v, p in zip(volumes, prices))
        else:
            amount = sum(volumes) * prices[0]
    return {
        "volume": int(sum(volumes)) if volumes else None,
        "price": round(prices[0], 4) if prices else None,
        "amount": round(amount, 2) if amount else None,
        "n_insiders": max(len(names), 1) if (volumes or names) else None,
        "name": names[0] if names else None,
        "role": role,
    }


def parse_message(summary, fetch_pdfs=True):
    """Henter detalj for én melding og returnerer en transaksjonsrad."""
    detail = fetch_detail(summary["messageId"])
    body = detail["body"]
    issuer = summary.get("issuer")
    cls = classify(summary["title"], body)
    fields = extract_fields(body, issuer=issuer)
    source = "body"

    if fields["volume"] is None and fetch_pdfs and detail["attachments"]:
        for att in detail["attachments"][:2]:
            time.sleep(THROTTLE)
            pdf_text, pairs = fetch_attachment_data(summary["messageId"], att["id"])
            if not pdf_text and not pairs:
                continue
            f2 = extract_fields(pdf_text, pairs=pairs or None, issuer=issuer)
            if f2["volume"] is not None:
                fields, source = f2, "pdf"
                if cls == "UKJENT":
                    cls = classify("", pdf_text)
                break

    return {
        "messageId": summary["messageId"],
        "published": summary["published"],
        "ticker": summary["ticker"],
        "issuer": summary["issuer"],
        "title": summary["title"],
        "url": summary["url"],
        "type": cls,
        "source": source if fields["volume"] is not None else "none",
        **fields,
    }


# --- lagring (append-only NDJSON, runneren eier filen) --------------------

def load_transactions(path=NDJSON_PATH):
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                out[rec["messageId"]] = rec
    return out


def save_transactions(records, path=NDJSON_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = sorted(records.values(), key=lambda r: (r["published"], r["messageId"]))
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
