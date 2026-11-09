"""Health proxy and one alert per sustained degradation episode."""
from dataclasses import dataclass
import math
import config


def health_score(baseline_tau, current_tau):
    if not all(math.isfinite(x) and x > 0 for x in (baseline_tau, current_tau)):
        raise ValueError("Tau values must be finite and positive.")
    return min(100.0, 100 * baseline_tau / current_tau)


@dataclass
class AlertRule:
    threshold: float = config.HEALTH_ALERT_THRESHOLD
    required: int = config.ALERT_CONSECUTIVE_FITS
    interval_s: float = config.FIT_INTERVAL_S
    count: int = 0
    active: bool = False
    last_time: float | None = None

    def update(self, health, at_seconds):
        """Returns degraded/recovered/None; only new 60-second fits count."""
        if self.last_time is not None:
            gap = at_seconds - self.last_time
            if gap < self.interval_s - 0.001:
                return None
            if gap > self.interval_s * 1.5:
                self.count = 0
        self.last_time = at_seconds
        if health is None or not math.isfinite(health):
            self.count = 0
            return None
        if health < self.threshold:
            self.count += 1
            if self.count >= self.required and not self.active:
                self.active = True
                return "degraded"
        else:
            self.count = 0
            if self.active:
                self.active = False
                return "recovered"
        return None
