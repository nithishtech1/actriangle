"""One validated CSV contract for replay, live analysis, and reports."""
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

import config


class DataError(ValueError):
    pass


def validate_run(frame: pd.DataFrame) -> pd.DataFrame:
    if list(frame.columns) != config.COLUMNS:
        raise DataError("Expected CSV columns: " + ",".join(config.COLUMNS))
    if frame.empty:
        raise DataError("No complete readings yet.")
    df = frame.copy()
    if df.phase.isna().any() or not set(df.phase).issubset(config.PHASES):
        raise DataError("Unknown or missing phase.")
    if df.phase.nunique() != 1:
        raise DataError("Use one phase per CSV; do not concatenate runs.")
    for col in config.COLUMNS[1:-1]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    required = ["ms", "supply_C", "return_C", "room_C", "room_RH"]
    if not np.isfinite(df[required].to_numpy()).all():
        raise DataError("Missing or non-finite sensor reading.")
    if (df.ms < 0).any() or (df.ms % 1 != 0).any() or (df.ms.diff().dropna() <= 0).any():
        raise DataError("ms must be non-negative integers, strictly increasing. Split rebooted runs.")
    for col in ("supply_C", "return_C", "room_C"):
        if not df[col].between(-10, 60).all():
            raise DataError(f"{col} outside -10..60 C (check disconnected probes).")
    if not df.room_RH.between(0, 100).all():
        raise DataError("room_RH outside 0..100%.")
    outdoor = df.outdoor_C.dropna()
    if not np.isfinite(outdoor).all() or not outdoor.between(-60, 60).all():
        raise DataError("Outdoor temperature outside -60..60 C.")
    timestamps = pd.to_datetime(df.ts_iso, errors="coerce", utc=True, format="mixed")
    if timestamps.isna().any():
        raise DataError("Invalid ts_iso timestamp.")
    df["elapsed_min"] = (df.ms - df.ms.iloc[0]) / 60000.0
    return df.reset_index(drop=True)


def read_run(path: str | Path, live: bool = False) -> pd.DataFrame:
    path = Path(path)
    # A logger may be in the middle of writing the last line. Ignore only that
    # incomplete line in live mode; never silently skip malformed complete rows.
    text = path.read_text(encoding="utf-8-sig")
    if live and text and not text.endswith("\n"):
        text = text.rsplit("\n", 1)[0] + "\n" if "\n" in text else ""
    try:
        return validate_run(pd.read_csv(StringIO(text)))
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DataError("CSV is empty or malformed.") from exc


def is_fake(path: str | Path) -> bool:
    return Path(path).name.upper().startswith(config.FAKE_PREFIX)


def expand_paths(args) -> list[Path]:
    import glob
    result = []
    for arg in args:
        p = Path(arg)
        matches = sorted(p.glob("*.csv")) if p.is_dir() else [Path(x) for x in glob.glob(str(p))]
        if not matches:
            raise DataError(f"No CSVs found: {arg}")
        result.extend(matches)
    return list(dict.fromkeys(result))
