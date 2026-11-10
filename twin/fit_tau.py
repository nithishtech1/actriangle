"""Fit the first 15 minutes of cooling, using actual elapsed time."""
import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from scipy.optimize import OptimizeWarning, curve_fit

import config
from twin.data import DataError, expand_paths, read_run, validate_run


class FitError(ValueError):
    pass


@dataclass(frozen=True)
class FitResult:
    tau_min: float
    final_C: float
    start_C: float
    r2: float
    start_min: float
    duration_min: float
    n_points: int
    tau_std_min: float


def cooling_curve(minutes, final_C, start_C, tau_min):
    return final_C + (start_C - final_C) * np.exp(-np.asarray(minutes) / tau_min)


def check_continuous_cooling(t, y):
    """Conservative eligibility gate, not a compressor-state detector.

    Every three-minute segment must still show a measurable decline. A run
    that reaches a plateau too early must be repeated under sustained cooling;
    fitting the plateau can produce a spuriously small, apparently healthy tau.
    """
    for left in np.arange(0, max(0, t[-1] - 3) + 0.001, 1):
        mask = (t >= left) & (t <= left + 3)
        if mask.sum() < 10:
            continue
        slope = np.polyfit(t[mask] - left, y[mask], 1)[0]
        if slope >= -0.02:
            raise FitError("Cooling interrupted or plateaued: repeat a sustained cooling run.")


def detect_cooling_start(t, smoothed) -> int:
    """First sustained 90-second decline; tolerates pre-cooling flat samples.

    Refine a candidate with a flat-then-declining change point, so warm-up
    samples do not bias the exponential fit. This estimates room response,
    not the electrical state of the compressor.
    """
    t, y = np.asarray(t), np.asarray(smoothed)
    for i in range(len(t)):
        j = int(np.searchsorted(t, t[i] + 1.5))
        if j >= len(t):
            break
        if j - i < 2:
            continue
        slope = np.polyfit(t[i:j + 1] - t[i], y[i:j + 1], 1)[0]
        if slope < -0.06 and y[i] - np.median(y[max(i, j - 2):j + 1]) >= 0.15:
            left = max(0, int(np.searchsorted(t, t[i] - 1)))
            right = min(len(t), int(np.searchsorted(t, t[i] + 2.25)) + 1)
            local_t, local_y = t[left:right], y[left:right]
            best = (float("inf"), i)
            for onset in range(i, j + 1):
                design = np.column_stack((np.ones(len(local_t)), np.maximum(local_t - t[onset], 0)))
                params = np.linalg.lstsq(design, local_y, rcond=None)[0]
                if params[1] >= -0.06:
                    continue
                error = float(np.sum((local_y - design @ params) ** 2))
                if error < best[0]:
                    best = (error, onset)
            if best[0] < float("inf"):
                return best[1]
    raise FitError("No sustained cooling detected.")


def fit_tau(frame: pd.DataFrame, *, min_duration_min=None) -> FitResult:
    df = validate_run(frame[config.COLUMNS])
    if df.phase.iloc[0] == "reset":
        raise FitError("Warm-back/reset data is not a cooling run.")
    t = df.elapsed_min.to_numpy()
    smooth = df.room_C.rolling(3, center=True, min_periods=1).median().to_numpy()
    start = detect_cooling_start(t, smooth)
    mask = (t >= t[start]) & (t <= t[start] + config.FIT_WINDOW_MIN)
    x, y = t[mask] - t[start], smooth[mask]
    minimum = config.FIT_WINDOW_MIN if min_duration_min is None else min_duration_min
    # Allow one sample of endpoint rounding for irregular 5-6 second sampling.
    if len(x) < 30 or x[-1] < minimum - 0.15:
        raise FitError(f"Need {minimum:g} minutes of cooling; have {x[-1]:.1f}.")
    if np.max(np.diff(x)) * 60 > config.MAX_SAMPLE_GAP_S:
        raise FitError("Gap over 30 seconds in cooling window; use an uninterrupted run.")
    if y[0] - np.median(y[-5:]) < 0.5:
        raise FitError("Cooling drop below 0.5 C; tau is not identifiable.")
    check_continuous_cooling(x, y)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", OptimizeWarning)
            params, covariance = curve_fit(
                cooling_curve, x, y,
                p0=[max(-9, float(y[-1] - 1)), float(y[0]), 10.0],
                bounds=([-10, y[0] - 2, 0.25], [min(y[0] - 0.1, 59), min(y[0] + 2, 60), 120]),
                maxfev=20000,
            )
    except (RuntimeError, ValueError, OptimizeWarning) as exc:
        raise FitError("Cooling fit did not converge.") from exc
    residual = y - cooling_curve(x, *params)
    total = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - float(np.sum(residual ** 2)) / total if total > 0 else 0
    final, initial, tau = map(float, params)
    tau_std = float(np.sqrt(max(0, covariance[2, 2])))
    if r2 < config.MIN_FIT_R2:
        raise FitError(f"Weak fit: R2={r2:.3f} below {config.MIN_FIT_R2}.")
    if not np.isfinite(tau_std) or tau_std / tau > 0.5 or tau >= 119.9 or final <= -9.9:
        raise FitError("Tau is poorly constrained; collect a clearer cooling run.")
    return FitResult(tau, final, initial, r2, float(t[start]), float(x[-1]), len(x), tau_std)


def twin_overlay(baseline: FitResult, current: FitResult, elapsed_min):
    """Keep clean-run tau/final temperature, use this run's own fitted start."""
    t = np.asarray(elapsed_min) - current.start_min
    return np.where(t >= 0, cooling_curve(np.maximum(t, 0), baseline.final_C,
                                         current.start_C, baseline.tau_min), np.nan)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()
    failed = False
    try:
        paths = expand_paths(args.files)
    except DataError as exc:
        parser.exit(1, f"{exc}\n")
    for path in paths:
        try:
            print(json.dumps({"file": path.name, **asdict(fit_tau(read_run(path)))}, indent=2))
        except (DataError, FitError, OSError) as exc:
            failed = True
            print(f"REJECTED {path.name}: {exc}", file=sys.stderr)
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
