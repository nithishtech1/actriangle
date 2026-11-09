"""Compare phases, expose supporting signals, and quantify explicit estimates."""
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import config
from twin.data import DataError, expand_paths, is_fake, read_run
from twin.fit_tau import FitError, fit_tau
from twin.health import health_score


def analyze_run(path, setpoint=None):
    path = Path(path)
    df = read_run(path)
    fit = fit_tau(df)
    sidecar = path.with_suffix(".meta.json")
    if setpoint is None and sidecar.exists():
        try:
            setpoint = json.loads(sidecar.read_text(encoding="utf-8" )).get("setpoint_C")
        except (ValueError, OSError):
            pass
    window = df[(df.elapsed_min >= fit.start_min) &
                (df.elapsed_min <= fit.start_min + config.FIT_WINDOW_MIN)]
    outdoor = window.outdoor_C.dropna()
    return {
        "file": path.name, "phase": str(df.phase.iloc[0]), "synthetic": is_fake(path),
        **asdict(fit), "setpoint_C": setpoint,
        "outdoor_mean_C": float(outdoor.mean()) if len(outdoor) else None,
        "outdoor_min_C": float(outdoor.min()) if len(outdoor) else None,
        "outdoor_max_C": float(outdoor.max()) if len(outdoor) else None,
        "temperature_split_C": float((window.return_C - window.supply_C).mean()),
        "humidity_drop_pct_per_min": float(-np.polyfit(window.elapsed_min, window.room_RH, 1)[0]),
    }


def compare_phases(records):
    by_phase = {r["phase"]: r for r in records}
    if len(by_phase) != len(records) or set(by_phase) != {"clean1", "blocked", "clean2"}:
        raise ValueError("Select exactly one clean1, blocked and clean2 run.")
    if len({r["synthetic"] for r in records}) != 1:
        raise ValueError("Do not combine FAKE and real runs in a comparison.")
    clean1, blocked, clean2 = [by_phase[p]["tau_min"] for p in ("clean1", "blocked", "clean2")]
    repeatability = abs(clean2 - clean1) / clean1 * 100
    separates = blocked > max(clean1, clean2) * 1.15 and repeatability <= 20
    return {
        "raw_improvement_pct": (blocked - clean2) / blocked * 100,
        "blocked_health": health_score(clean1, blocked),
        "clean_repeatability_pct": repeatability,
        "tau_separates": separates,
        "decision": ("Tau separates these three runs under a provisional 15% margin; validate with repeats."
                     if separates else "Tau separation is inconclusive. Review temperature split and humidity slopes; do not auto-calibrate the alert."),
        "threshold_status": "80 is a provisional default, not a calibrated fault boundary.",
    }


def minutes_to_target(tau, final, start, target):
    if not all(math.isfinite(v) for v in (tau, final, start, target)) or tau <= 0:
        raise ValueError("Invalid cooling parameters")
    if not final < target < start:
        raise ValueError("Target must lie above the fitted final temperature and below the start.")
    return float(-tau * math.log((target - final) / (start - final)))


def savings_estimate(blocked, clean2, *, kw=None, tariff=None, target=26.0):
    if kw is None or tariff is None:
        return {"available": False, "reason": "Enter actual nameplate kW and tariff; no cost has been assumed."}
    if not all(math.isfinite(v) and v > 0 for v in (kw, tariff)):
        raise ValueError("Nameplate kW and tariff must be finite and positive.")
    start = max(blocked["start_C"], clean2["start_C"])
    try:
        before = minutes_to_target(blocked["tau_min"], blocked["final_C"], start, target)
        after = minutes_to_target(clean2["tau_min"], clean2["final_C"], start, target)
    except ValueError as exc:
        return {"available": False, "reason": str(exc)}
    saved = before - after
    return {"available": True, "minutes_saved": saved, "estimated_kwh": saved / 60 * kw,
            "estimated_rs": saved / 60 * kw * tariff, "nameplate_kw": kw,
            "tariff_rs_per_kwh": tariff, "common_start_C": start, "target_C": target,
            "before_minutes": before, "after_minutes": after,
            "assumptions": "One pull-down to a common target; constant nameplate input power. No duty-cycle, seasonal or measured-energy claim. Raw weather-unadjusted estimate."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        records = [analyze_run(p) for p in expand_paths(args.files)]
        result = {"runs": records, "comparison": compare_phases(records)}
        encoded = json.dumps(result, indent=2, allow_nan=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded + "\n", encoding="utf-8")
        print(encoded)
    except (DataError, FitError, ValueError, OSError) as exc:
        parser.exit(1, f"Analysis failed: {exc}\n")


if __name__ == "__main__":
    main()
