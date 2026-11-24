"""Sauvegarde à chaud de la base (API backup de SQLite), avec rotation.

python -m companion.backup --db data/companion.db --dir data/backups --keep 30
"""
from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path


def backup(db_path: str | Path, out_dir: str | Path, keep: int = 30) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"companion-{time.strftime('%Y%m%d-%H%M%S')}.db"
    src = sqlite3.connect(str(db_path))
    dst = sqlite3.connect(str(dest))
    with dst:
        src.backup(dst)
    ok = dst.execute("PRAGMA integrity_check").fetchone()[0]
    src.close()
    dst.close()
    if ok != "ok":
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"Sauvegarde corrompue : {ok}")
    backups = sorted(out_dir.glob("companion-*.db"))
    for old in backups[:-keep]:
        old.unlink()
    return dest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/companion.db")
    ap.add_argument("--dir", default="data/backups")
    ap.add_argument("--keep", type=int, default=30)
    a = ap.parse_args()
    print(backup(a.db, a.dir, a.keep))


if __name__ == "__main__":
    main()
