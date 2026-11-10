"""Shared incremental pipeline used by both live and 10x replay modes."""
from dataclasses import dataclass, field
import numpy as np
import config
from twin.fit_tau import FitError, FitResult, detect_cooling_start, fit_tau
from twin.health import AlertRule, health_score


@dataclass
class Monitor:
    baseline: FitResult
    rule: AlertRule = field(default_factory=AlertRule)
    next_fit_s: float = config.LIVE_MIN_FIT_MIN * 60
    latest: FitResult | None = None
    health: float | None = None
    reason: str = "Waiting for 8 minutes of sustained cooling."
    complete: bool = False
    history: list = field(default_factory=list)

    def advance(self, df):
        if df.empty:
            return []
        end_s = float(df.elapsed_min.iloc[-1] * 60)
        events = []
        while self.next_fit_s <= end_s + 0.001 and not self.complete:
            stamp = self.next_fit_s
            self.next_fit_s += config.FIT_INTERVAL_S
            view = df[df.elapsed_min * 60 <= stamp + 0.001]
            try:
                start = detect_cooling_start(view.elapsed_min, view.room_C.rolling(3, center=True, min_periods=1).median())
                start_s = float(view.elapsed_min.iloc[start] * 60)
                if stamp > start_s + config.FIT_WINDOW_MIN * 60 + config.FIT_INTERVAL_S:
                    self.complete = True
                    break
                if stamp - float(view.elapsed_min.iloc[-1] * 60) > 15:
                    raise FitError("No fresh reading at this fit interval.")
                current = fit_tau(view, min_duration_min=config.LIVE_MIN_FIT_MIN)
                self.latest = current
                self.health = health_score(self.baseline.tau_min, current.tau_min)
                self.reason = "Valid initial cooling fit."
                if stamp >= start_s + config.FIT_WINDOW_MIN * 60:
                    self.complete = True
            except FitError as exc:
                self.health = None
                self.reason = str(exc)
            event = self.rule.update(self.health, stamp)
            self.history.append({"elapsed_min": stamp / 60, "health": self.health,
                                 "tau_min": self.latest.tau_min if self.health is not None else np.nan,
                                 "event": event})
            if event:
                events.append({"event": event, "at_seconds": stamp, "health": self.health})
        return events
