"""ClimaTwin shared configuration. Every TODO is owned by someone; see README."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_env():
    """Tiny .env reader so no extra dependency is needed."""
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


_load_env()

# ---------- Serial / logging ----------
SERIAL_PORT = "COM5"          # TODO (hardware lead): e.g. COM5 on Windows, /dev/ttyUSB0 on Linux
BAUD = 115200
SAMPLE_INTERVAL_S = 5         # NOMINAL. Real spacing is ~5.8 s (DS18B20 conversion blocks ~0.75 s + delay(5000)).
                              # Always use the ms / ts_iso columns as the time axis, never the row number.

# ---------- Outdoor temperature (Open-Meteo, no key needed) ----------
LATITUDE = 13.08              # TODO: approximate; replace with the test room's location
LONGITUDE = 80.27             # TODO: approximate; replace with the test room's location
OUTDOOR_REFRESH_MIN = 10
OUTDOOR_FALLBACK_C = None     # TODO: set a typed value if the internet drops (e.g. 33.0)

# ---------- Probe mapping (set after task 35: warm each probe in your hand) ----------
# Firmware prints probe0_C and probe1_C in the order DallasTemperature finds them.
PROBE_ROLES = {"probe0": "supply", "probe1": "return"}   # TODO: swap if labelled the other way

# ---------- Sensor offsets (from the task-41 side-by-side check, AC off) ----------
# Convention: corrected = raw + offset, where offset = reference - raw.
# Reference = the average of the three sensors during the 5-minute check.
SENSOR_OFFSETS = {
    "supply_C": 0.0,          # TODO
    "return_C": 0.0,          # TODO
    "room_C": 0.0,            # TODO
    "room_RH": 0.0,           # TODO
}

# ---------- Estimate inputs (energy is an ESTIMATE, never a measurement) ----------
AC_NAMEPLATE_KW = None        # TODO: from the nameplate photo (task 27)
TARIFF_RS_PER_KWH = None      # TODO: use the real tariff for the household; do not guess

# ---------- Telegram (secrets live in .env, never in git) ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ---------- Data contract (see README.md) ----------
RAW_COLUMNS = ["ms", "probe0_C", "probe1_C", "room_C", "room_RH"]   # what the ESP32 prints
COLUMNS = ["ts_iso", "ms", "supply_C", "return_C", "room_C", "room_RH", "outdoor_C", "phase"]
PHASES = ("clean1", "blocked", "clean2", "reset")
FAKE_PREFIX = "FAKE_"

# ---------- Paths ----------
DATA_RAW = ROOT / "data" / "raw"
DATA_REPLAY = ROOT / "data" / "replay"

# ---------- Health / alert defaults (REVISIT after task 85, using real data) ----------
HEALTH_ALERT_THRESHOLD = 80
ALERT_CONSECUTIVE_FITS = 3
FIT_INTERVAL_S = 60

# Fit the initial pull-down only; do not model steady-state compressor cycling.
FIT_WINDOW_MIN = 15.0
LIVE_MIN_FIT_MIN = 8.0        # provisional fits at 8, 9, ... 15 minutes
MIN_FIT_R2 = 0.90
MAX_SAMPLE_GAP_S = 30.0      # reject an interrupted fitting window
SETPOINT_C = None           # enter the actual setting; not inferred from sensor data
REPORTS = ROOT / "reports"
