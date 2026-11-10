"""Open-Meteo temperature cache with explicit fallback provenance."""
import logging
import math
import time

import requests
import config

log = logging.getLogger(__name__)


class WeatherClient:
    def __init__(self, latitude=config.LATITUDE, longitude=config.LONGITUDE,
                 fallback=config.OUTDOOR_FALLBACK_C, offline=False, session=None,
                 clock=time.monotonic):
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Invalid weather coordinates.")
        if fallback is not None and (not math.isfinite(fallback) or not -60 <= fallback <= 60):
            raise ValueError("Outdoor fallback must be -60..60 C.")
        self.latitude, self.longitude = latitude, longitude
        self.fallback, self.offline = fallback, offline
        self.session, self.clock = session or requests.Session(), clock
        self.next_refresh = float("-inf")
        self.value, self.source = fallback, "typed fallback" if fallback is not None else "unavailable"

    def get(self):
        now = self.clock()
        if now < self.next_refresh:
            return self.value
        self.next_refresh = now + config.OUTDOOR_REFRESH_MIN * 60
        self.value, self.source = self.fallback, "typed fallback" if self.fallback is not None else "unavailable"
        if self.offline:
            return self.value
        try:
            response = self.session.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": self.latitude, "longitude": self.longitude,
                "current": "temperature_2m", "temperature_unit": "celsius",
                "timezone": "UTC",
            }, timeout=5)
            response.raise_for_status()
            value = float(response.json()["current"]["temperature_2m"])
            if not math.isfinite(value) or not -60 <= value <= 60:
                raise ValueError("Invalid weather temperature")
            self.value, self.source = value, "Open-Meteo"
        except (requests.RequestException, ValueError, KeyError, TypeError):
            log.warning("Weather unavailable; using %s (%s C).", self.source, self.value)
        return self.value
