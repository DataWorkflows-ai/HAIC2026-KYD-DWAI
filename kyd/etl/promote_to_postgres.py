"""Load the app's data into Postgres (Supabase) for live mode, then read it back and compare.

    python kyd/etl/promote_to_postgres.py                 # schema (db/live.sql) + load + verify
    python kyd/etl/promote_to_postgres.py --check         # verify only: Postgres must equal the repository
    python kyd/etl/promote_to_postgres.py --app-env kyd/backend/.env.render
                                                          # also give the read-only role kyd_app a login and
                                                          # write its connection string to that file

What is loaded:
  kyd.geography / indicator / source / observation / breakdown   ← kyd/data/kyd.sqlite, row for row
  kyd.datafile   ← the reference files the app reads at run time (app/services/datastore.py FILES), whole,
                   plus two documents computed here from scripts/ so the server does not parse raw workbooks
  kyd.load_run   ← one row per load: git commit, SQLite checksum, row counts

The connection string comes from --url, else KYD_DATABASE_URL (environment or kyd/backend/.env). It is never
printed. The load runs in one transaction: readers see the old data or the new data, never a mix.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

KYD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KYD / "backend"))
os.environ["KYD_DATA_MODE"] = "sqlite"      # the documents computed below come from the bundled data and scripts/

from app.config import settings  # noqa: E402
from app.services import datastore  # noqa: E402

TABLES = ("geography", "indicator", "source", "observation", "breakdown")   # parents before children


def sqlite_rows() -> dict[str, tuple[list[str], list[tuple]]]:
    c = sqlite3.connect(f"file:{settings().data_dir / 'kyd.sqlite'}?mode=ro", uri=True)
    out = {}
    for t in TABLES:
        cur = c.execute(f"SELECT * FROM {t}")
        out[t] = ([d[0] for d in cur.description], cur.fetchall())
    c.close()
    return out


def documents() -> dict[str, tuple[str, str]]:
    """name → (content, origin) for every reference file and computed document."""
    docs: dict[str, tuple[str, str]] = {}
    for name in datastore.FILES:
        t = datastore.text(name)
        if t is None:
            raise SystemExit(f"missing reference file: {datastore.disk_path(name)}")
        docs[name] = (t, str(datastore.disk_path(name).relative_to(KYD.parent)).replace("\\", "/"))
    from app.services import program_context as pc
    under = pc._scripts()[3]
    ids = [g for g in datastore.load_json("district_counties.json") if g[:2] in ("HD", "SD")]
    static = json.dumps(pc._static(), ensure_ascii=False, sort_keys=True)
    ue = json.dumps({g: under.get_tanf_underenrollment("house" if g.startswith("HD") else "senate", int(g[3:]))
                     for g in ids}, ensure_ascii=False, sort_keys=True)
    docs[datastore.COMPUTED[0]] = (static, "computed: app.services.program_context._static() from scripts/")
    docs[datastore.COMPUTED[1]] = (ue, "computed: scripts/tanf_underenrollment.py for every district")
    return docs


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_sha() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(KYD), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return None


def load(conn, tables, docs) -> dict:
    counts = {t: len(rows) for t, (_, rows) in tables.items()} | {"datafile": len(docs)}
    with conn.transaction():
        conn.execute("TRUNCATE kyd.breakdown, kyd.observation, kyd.indicator, kyd.source, kyd.geography, kyd.datafile")
        with conn.cursor() as cur:
            for t in TABLES:
                cols, rows = tables[t]
                with cur.copy(f"COPY kyd.{t} (ord, {', '.join(cols)}) FROM STDIN") as cp:
                    for n, r in enumerate(rows):
                        cp.write_row((n, *r))
            with cur.copy("COPY kyd.datafile (name, content, sha256, bytes, origin) FROM STDIN") as cp:
                for name, (content, origin) in docs.items():
                    cp.write_row((name, content, sha(content), len(content.encode("utf-8")), origin))
        sq = hashlib.sha256((settings().data_dir / "kyd.sqlite").read_bytes()).hexdigest()
        conn.execute("INSERT INTO kyd.load_run (git_sha, sqlite_sha256, counts) VALUES (%s, %s, %s)",
                     (git_sha(), sq, json.dumps(counts)))
    return counts


def check(conn, tables, docs) -> list[str]:
    """Every row and every document in Postgres must equal the repository. Returns the differences."""
    bad: list[str] = []
    with conn.cursor() as cur:
        for t in TABLES:
            cols, rows = tables[t]
            got = cur.execute(f"SELECT {', '.join(cols)} FROM kyd.{t} ORDER BY ord").fetchall()
            if got != rows:
                diff = sum(1 for a, b in zip(got, rows) if a != b) + abs(len(got) - len(rows))
                bad.append(f"kyd.{t}: {len(got)} rows in Postgres, {len(rows)} in SQLite, {diff} differ")
        got = dict(cur.execute("SELECT name, content FROM kyd.datafile").fetchall())
        for name, (content, _) in docs.items():
            if got.get(name) != content:
                bad.append(f"kyd.datafile {name}: " + ("missing" if name not in got else "content differs"))
        for name in set(got) - set(docs):
            bad.append(f"kyd.datafile {name}: in Postgres but not in the repository")
    return bad


def app_login(conn, url: str, out: Path) -> None:
    """Give the read-only role a login and write its connection string to a local file (never printed)."""
    pw = secrets.token_urlsafe(24).replace("-", "x").replace("_", "y")
    conn.execute(f"ALTER ROLE kyd_app LOGIN PASSWORD '{pw}'")      # pw is alphanumeric, generated above
    u = urlsplit(url)
    user = (u.username or "postgres")
    app_user = "kyd_app." + user.split(".", 1)[1] if "." in user else "kyd_app"   # Supabase pooler: role.project-ref
    host = u.hostname + (f":{u.port}" if u.port else "")
    app_url = urlunsplit((u.scheme, f"{quote(app_user)}:{pw}@{host}", u.path, u.query, ""))
    import psycopg
    try:
        with psycopg.connect(app_url, connect_timeout=20, prepare_threshold=None) as c2:
            n = c2.execute("SELECT count(*) FROM kyd.observation").fetchone()[0]
            try:
                c2.execute("DELETE FROM kyd.observation")
                raise SystemExit("kyd_app was able to delete data. Refusing to continue.")
            except psycopg.errors.InsufficientPrivilege:
                c2.rollback()
        out.write_text(f"KYD_DATA_MODE=live\nKYD_DATABASE_URL={app_url}\n", encoding="utf-8")
        print(f"kyd_app can log in, reads {n} observations, cannot write data. Connection string written to {out}")
    except psycopg.OperationalError as e:
        print(f"kyd_app login did not work through this host ({type(e).__name__}). Nothing written. "
              "Use the owner connection string for now.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", help="Postgres connection string (default: KYD_DATABASE_URL)")
    ap.add_argument("--check", action="store_true", help="verify only; change nothing")
    ap.add_argument("--app-env", type=Path, help="create a login for kyd_app and write its connection string here")
    a = ap.parse_args()
    import psycopg
    url = a.url or settings().database_url
    print(f"Postgres host: {urlsplit(url).hostname}")
    tables, docs = sqlite_rows(), documents()
    with psycopg.connect(url, connect_timeout=20, prepare_threshold=None, autocommit=True) as conn:
        if not a.check:
            conn.execute((KYD / "db" / "live.sql").read_text(encoding="utf-8"))
            counts = load(conn, tables, docs)
            print("loaded:", ", ".join(f"{k} {v}" for k, v in counts.items()))
        bad = check(conn, tables, docs)
        for b in bad:
            print("DIFFERENT:", b)
        if bad:
            return 1
        print(f"verified: {sum(len(r) for _, r in tables.values())} rows and {len(docs)} documents in Postgres "
              "equal the repository")
        if a.app_env and not a.check:
            app_login(conn, url, a.app_env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
