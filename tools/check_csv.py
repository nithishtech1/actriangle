"""Validate run CSVs against the data contract.

Usage:
    python tools/check_csv.py data/raw            # a whole folder
    python tools/check_csv.py data/raw/*.csv      # wildcards work even in PowerShell / cmd
    python tools/check_csv.py some_file.csv
Files named bench_*.csv are checked against the raw 5-column ESP32 format instead.
"""
import glob
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

NAME_RE = re.compile(r"^(FAKE_)?run_(clean1|blocked|clean2|reset)_\d{8}_\d{4}(?:_\d{2,})?\.csv$")


def expand(args):
    files = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            files += sorted(p.glob("*.csv"))
        elif any(ch in a for ch in "*?["):
            files += [Path(x) for x in sorted(glob.glob(a))]
        else:
            files.append(p)
    return files


def check(path: Path) -> bool:
    problems, warnings = [], []
    if not path.exists():
        return report(path, ["file not found"], warnings)
    bench = path.name.startswith("bench_")
    expected = config.RAW_COLUMNS if bench else config.COLUMNS
    if not bench and not NAME_RE.match(path.name):
        warnings.append("filename does not match [FAKE_]run_<phase>_<YYYYMMDD_HHMM>.csv")
    try:
        df = pd.read_csv(path)
    except Exception as e:  # empty file, bad encoding, etc.
        return report(path, [f"could not read file: {e}"], warnings)
    if list(df.columns) != expected:
        return report(path, [f"columns are {list(df.columns)}, expected {expected}"], warnings)
    if df.empty:
        return report(path, ["file has no rows"], warnings)

    if not bench:
        from twin.data import DataError, validate_run
        try:
            validate_run(df)
        except DataError as exc:
            problems.append(str(exc))

    if not bench:
        bad = set(df["phase"].dropna().unique()) - set(config.PHASES)
        if bad:
            problems.append(f"unknown phase values: {sorted(bad)}")
        if df["phase"].nunique() > 1:
            warnings.append("more than one phase inside one file")
    num_cols = [c for c in expected if c not in ("ts_iso", "phase")]
    for col in num_cols:
        if col == "ms":
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        n_bad = int(s.isna().sum())
        if n_bad:
            warnings.append(f"{col}: {n_bad} missing/non-numeric rows")
        if (s == -127).any():
            problems.append(f"{col}: contains -127 (DS18B20 disconnected)")
        if col.endswith("_C") and ((s < -10) | (s > 60)).any():
            warnings.append(f"{col}: values outside -10..60 C")
        if col == "room_RH" and ((s < 0) | (s > 100)).any():
            problems.append("room_RH outside 0..100")
    ms = pd.to_numeric(df["ms"], errors="coerce")
    d = ms.diff().dropna()
    if (d <= 0).any():
        warnings.append("ms is not strictly increasing (ESP32 reset or rows out of order?)")
    gap = d[d > 0].median() / 1000.0 if (d > 0).any() else None
    if gap is not None and not (3.0 <= gap <= 8.0):
        warnings.append(f"median sample gap is {gap:.1f}s (expected about 5-6s)")
    return report(path, problems, warnings, rows=len(df))


def report(path, problems, warnings, rows=None):
    status = "FAIL" if problems else "ok"
    print(f"[{status}] {path.name}" + (f" ({rows} rows)" if rows else ""))
    for p in problems:
        print(f"    ERROR: {p}")
    for w in warnings:
        print(f"    warn:  {w}")
    return not problems


if __name__ == "__main__":
    files = expand(sys.argv[1:])
    if not files:
        sys.exit("No CSV files found. usage: python tools/check_csv.py <folder | file.csv ...>")
    results = [check(f) for f in files]
    print(f"\n{sum(results)}/{len(results)} files ok")
    sys.exit(0 if all(results) else 1)
