"""
Backfill: henter og parser historiske innsidemeldinger til NDJSON-basen.

Bruk: python3 backfill.py [dager]    (default 90)

Resumerbar — meldinger som allerede ligger i data/transactions.ndjson
hoppes over, og basen lagres etter hvert 14-dagersvindu. Ikke gå lenger
tilbake enn mars 2021 (MAR trådte i kraft; eldre meldinger har annet format).
"""

import sys
import time
from datetime import datetime, timedelta, timezone

import newsweb


def main(days=90, max_minutes=None):
    start = time.time()
    db = newsweb.load_transactions()
    print(f"{len(db)} transaksjoner i basen fra før")
    today = datetime.now(timezone.utc).date()
    new = failed = 0

    for offset in range(0, days, 14):
        if max_minutes and (time.time() - start) / 60 > max_minutes:
            print(f"Tidsbudsjett ({max_minutes} min) brukt — stopper her, "
                  "resumerbar fra neste kjøring", flush=True)
            break
        to_d = today - timedelta(days=offset)
        from_d = today - timedelta(days=min(offset + 14, days))
        msgs = newsweb.fetch_list(from_d.isoformat(),
                                  (to_d + timedelta(days=1)).isoformat())
        time.sleep(newsweb.THROTTLE)
        for m in msgs:
            if m["messageId"] in db:
                continue
            try:
                db[m["messageId"]] = newsweb.parse_message(m)
                new += 1
            except Exception as e:
                failed += 1
                print(f"  FEIL {m['messageId']} ({m['ticker']}): {e}",
                      file=sys.stderr)
            time.sleep(newsweb.THROTTLE)
        newsweb.save_transactions(db)
        print(f"vindu {from_d} – {to_d}: {len(msgs)} meldinger, "
              f"totalt {len(db)} i basen", flush=True)

    ok_vol = sum(1 for r in db.values() if r.get("volume"))
    ok_amt = sum(1 for r in db.values() if r.get("amount"))
    n = len(db) or 1
    print(f"\nFerdig: {len(db)} transaksjoner ({new} nye, {failed} feilet)")
    print(f"volum {ok_vol/n*100:.0f}% · beløp {ok_amt/n*100:.0f}%")


if __name__ == "__main__":
    args = sys.argv[1:]
    dager = int(args[0]) if args and not args[0].startswith("-") else 90
    minutter = None
    if "--minutes" in args:
        minutter = int(args[args.index("--minutes") + 1])
    main(dager, minutter)
