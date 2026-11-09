"""Optional secondary anomaly flag; never changes the health/service verdict."""
import numpy as np
import config
from twin.data import validate_run
from twin.fit_tau import fit_tau


def features(df, tau):
    if df.outdoor_C.isna().any():
        raise ValueError("Anomaly layer needs outdoor temperature for every reading.")
    # Tau is run-level; do not pretend it is an independently observed per-row signal.
    return np.column_stack((df.room_C, df.return_C - df.supply_C,
                            np.full(len(df), tau), df.outdoor_C))


class HealthyAnomalyModel:
    def fit(self, clean1, contamination=0.02):
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler
        clean1 = validate_run(clean1[config.COLUMNS])
        if clean1.phase.iloc[0] != "clean1":
            raise ValueError("Isolation Forest must be trained on clean1 only.")
        if not 0 < contamination <= 0.5:
            raise ValueError("contamination must be between 0 and 0.5.")
        x = features(clean1, fit_tau(clean1).tau_min)
        self.scaler = StandardScaler().fit(x)
        self.model = IsolationForest(n_estimators=200, contamination=contamination, random_state=0)
        self.model.fit(self.scaler.transform(x))
        return self

    def score(self, frame):
        frame = validate_run(frame[config.COLUMNS])
        x = self.scaler.transform(features(frame, fit_tau(frame).tau_min))
        return self.model.decision_function(x)
