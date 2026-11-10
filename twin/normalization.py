"""Optional outdoor-temperature regression with no extrapolation."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class WeatherModel:
    slope: float
    intercept: float
    min_C: float
    max_C: float
    n_runs: int
    phase: str

    def predict(self, outdoor_C):
        if not np.isfinite(outdoor_C) or not self.min_C <= outdoor_C <= self.max_C:
            raise ValueError("Outdoor temperature outside the training range; no extrapolation.")
        predicted = self.slope * outdoor_C + self.intercept
        if predicted <= 0:
            raise ValueError("Weather model predicted a non-positive tau.")
        return float(predicted)


def fit_weather_model(records):
    """Each record must be an independent run in the SAME equipment condition."""
    if len(records) < 2:
        raise ValueError("Need at least two independent before-service runs.")
    if len({r["phase"] for r in records}) != 1:
        raise ValueError("Do not mix clean and blocked conditions in weather training.")
    if len({r["synthetic"] for r in records}) != 1:
        raise ValueError("Do not mix synthetic and real weather training runs.")
    x = np.array([r["outdoor_mean_C"] for r in records], dtype=float)
    y = np.array([r["tau_min"] for r in records], dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or (y <= 0).any():
        raise ValueError("Weather training requires valid outdoor temperatures and tau fits.")
    if np.ptp(x) < 0.5:
        raise ValueError("Need distinct outdoor temperatures spanning at least 0.5 C.")
    slope, intercept = np.polyfit(x, y, 1)
    return WeatherModel(float(slope), float(intercept), float(x.min()), float(x.max()),
                        len(records), records[0]["phase"])
