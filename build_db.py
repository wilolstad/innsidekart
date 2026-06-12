"""
Bygger SQLite-database fra data/transactions.ndjson — for backtest og
analyse (fase 2). Basen i git er NDJSON (tekst, små diffs); SQLite er
et lokalt artefakt man bygger ved behov.

Bruk: python3 build_db.py    ->  innsidekart.db
"""

import sqlite3

import newsweb

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    message_id  INTEGER PRIMARY KEY,
    published   TEXT NOT NULL,
    ticker      TEXT,
    issuer      TEXT,
    type        TEXT NOT NULL,      -- KJØP / SALG / PROGRAM / UKJENT
    volume      INTEGER,
    price       REAL,
    amount      REAL,
    n_insiders  INTEGER,
    name        TEXT,
    role        TEXT,
    source      TEXT,               -- body / pdf / none
    title       TEXT,
    url         TEXT
);
CREATE INDEX IF NOT EXISTS idx_tx_ticker ON transactions(ticker, published);
CREATE INDEX IF NOT EXISTS idx_tx_type ON transactions(type, published);
"""


def main(db_path="innsidekart.db"):
    records = newsweb.load_transactions()
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    con.executemany(
        """INSERT OR REPLACE INTO transactions
           (message_id, published, ticker, issuer, type, volume, price,
            amount, n_insiders, name, role, source, title, url)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(r["messageId"], r["published"], r["ticker"], r["issuer"], r["type"],
          r.get("volume"), r.get("price"), r.get("amount"), r.get("n_insiders"),
          r.get("name"), r.get("role"), r.get("source"), r["title"], r["url"])
         for r in records.values()])
    con.commit()
    n = con.execute("SELECT count(*) FROM transactions").fetchone()[0]
    print(f"{db_path}: {n} transaksjoner")
    con.close()


if __name__ == "__main__":
    main()
