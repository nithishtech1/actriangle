"""Deterministic FAKE cooling runs. Never writes into data/raw."""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import config


def generate_run(phase, *, seed=42, duration_min=40, interval_s=5.8,
                 start=None, warmup_min=0, noise=0.1):
    if phase not in ("clean1", "blocked", "clean2"):
        raise ValueError("Choose clean1, blocked or clean2.")
    if duration_min <= 0 or interval_s <= 0 or noise < 0 or warmup_min < 0:
        raise ValueError("Invalid simulation duration, interval, warmup or noise.")
    start = start or datetime(2026, 11, 9, 9, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    rng = np.random.default_rng(seed)
    seconds = np.arange(0, duration_min * 60 + 0.001, interval_s)
    cooling = np.maximum(seconds / 60 - warmup_min, 0)
    tau, final = (14.0, 24.0) if phase == "blocked" else (8.0, 22.0)
    room = final + (30 - final) * np.exp(-cooling / tau)
    return pd.DataFrame({
        "ts_iso": [(start + timedelta(seconds=float(s))).isoformat(timespec="milliseconds") for s in seconds],
        "ms": np.rint(seconds * 1000).astype(int),
        "supply_C": np.round(room - (7 if phase == "blocked" else 10) + rng.normal(0, noise, len(room)), 3),
        "return_C": np.round(room + 0.3 + rng.normal(0, noise, len(room)), 3),
        "room_C": np.round(room + rng.normal(0, noise, len(room)), 3),
        "room_RH": np.round(45 + 20 * np.exp(-cooling / 20) + rng.normal(0, 0.15, len(room)), 2),
        "outdoor_C": np.full(len(room), 33.0),
        "phase": phase,
    }, columns=config.COLUMNS)


def generate_all(output=config.DATA_REPLAY, seed=42, overwrite=False):
    output = Path(output)
    if output.resolve() == config.DATA_RAW.resolve() or config.DATA_RAW.resolve() in output.resolve().parents:
        raise ValueError("Synthetic data must not be written into data/raw.")
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    start = datetime(2026, 11, 9, 9, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    for i, phase in enumerate(("clean1", "blocked", "clean2")):
        run_start = start + timedelta(minutes=65 * i)
        path = output / f"FAKE_run_{phase}_{run_start:%Y%m%d_%H%M}.csv"
        df = generate_run(phase, seed=seed + i, start=run_start)
        # Exclusive creation prevents accidentally overwriting a demo recording.
        with path.open("w" if overwrite else "x", newline="", encoding="utf-8") as handle:
            df.to_csv(handle, index=False)
        paths.append(path)
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=config.DATA_REPLAY)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        for path in generate_all(args.output, args.seed, args.overwrite):
            print(f"FAKE: {path}")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
