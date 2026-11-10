"""Capture ESP32 readings, flush each row, reconnect and split rebooted runs."""
import argparse
import csv
from datetime import datetime
import json
import logging
import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import serial
import config
from logger.weather import WeatherClient

log = logging.getLogger(__name__)


def parse_line(line, roles=None, offsets=None):
    """Return corrected numeric readings; ignore headers/startup diagnostics."""
    roles = config.PROBE_ROLES if roles is None else roles
    offsets = config.SENSOR_OFFSETS if offsets is None else offsets
    if set(roles) != {"probe0", "probe1"} or set(roles.values()) != {"supply", "return"}:
        raise ValueError("PROBE_ROLES must map probe0/probe1 to distinct supply/return roles.")
    if isinstance(line, bytes):
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError:
            return None
    fields = line.strip().split(",")
    if len(fields) != 5:
        return None
    try:
        ms = int(fields[0])
        values = [float(x) for x in fields[1:]]
    except ValueError:
        return None
    if not 0 <= ms <= 0xFFFFFFFF or not all(math.isfinite(x) for x in values):
        return None
    if not all(-10 <= x <= 60 for x in values[:3]) or not 0 <= values[3] <= 100:
        return None
    row = {"ms": ms, f"{roles['probe0']}_C": values[0],
           f"{roles['probe1']}_C": values[1], "room_C": values[2], "room_RH": values[3]}
    for name in ("supply_C", "return_C", "room_C", "room_RH"):
        row[name] = round(row[name] + float(offsets.get(name, 0)), 3)
        low, high = (0, 100) if name == "room_RH" else (-10, 60)
        if not math.isfinite(row[name]) or not low <= row[name] <= high:
            return None
    return row


class RunWriter:
    def __init__(self, directory, phase, metadata=None):
        self.directory, self.phase = Path(directory), phase
        if phase not in config.PHASES:
            raise ValueError("Unknown phase")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.metadata = metadata or {}
        self.handle = self.writer = self.path = None
        self.previous_ms = None
        self.rows = 0

    def close(self):
        if self.handle:
            self.handle.close()
        self.handle = self.writer = None
        self.previous_ms = None

    def _open(self, now):
        stem = f"run_{self.phase}_{now:%Y%m%d_%H%M}"
        for index in range(10000):
            suffix = "" if index == 0 else f"_{index:02}"
            path = self.directory / f"{stem}{suffix}.csv"
            try:
                self.handle = path.open("x", newline="", encoding="utf-8")
                break
            except FileExistsError:
                continue
        else:
            raise OSError("Too many filename collisions")
        self.path = path
        self.writer = csv.DictWriter(self.handle, fieldnames=config.COLUMNS)
        self.writer.writeheader()
        self.handle.flush()
        path.with_suffix(".meta.json").write_text(json.dumps({
            "phase": self.phase, "started": now.isoformat(), "synthetic": False,
            "probe_roles": config.PROBE_ROLES, "sensor_offsets": config.SENSOR_OFFSETS,
            "setpoint_C": config.SETPOINT_C, **self.metadata,
        }, indent=2), encoding="utf-8")
        log.info("Writing %s", path)

    def write(self, row, outdoor_C, now=None, weather_source="unavailable"):
        now = now or datetime.now().astimezone()
        if self.previous_ms is not None:
            if row["ms"] == self.previous_ms:
                return False
            if row["ms"] < self.previous_ms:
                log.warning("ESP32 reboot/millis wrap detected; starting a new file.")
                self.close()
        if self.handle is None:
            self._open(now)
        self.writer.writerow({**row, "ts_iso": now.isoformat(timespec="milliseconds"),
                              "outdoor_C": outdoor_C, "phase": self.phase})
        self.handle.flush()
        # Preserve the fixed CSV contract; weather provenance lives in a sidecar.
        provenance = (weather_source, outdoor_C)
        if getattr(self, "_weather", None) != provenance or self.previous_ms is None:
            with self.path.with_suffix(".weather.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"ts_iso": now.isoformat(), "outdoor_C": outdoor_C,
                                         "source": weather_source}) + "\n")
            self._weather = provenance
        self.previous_ms = row["ms"]
        self.rows += 1
        return True


def capture(port, phase, output=config.DATA_RAW, *, baud=config.BAUD, duration_s=None,
            weather=None, reconnect_s=2, serial_factory=serial.serial_for_url,
            clock=time.monotonic, sleep=time.sleep, metadata=None):
    weather = weather or WeatherClient()
    writer = RunWriter(output, phase, metadata)
    start = clock()
    try:
        while duration_s is None or clock() - start < duration_s:
            try:
                with serial_factory(port, baudrate=baud, timeout=1) as device:
                    log.info("Connected to %s at %s baud", port, baud)
                    pending = b""
                    while duration_s is None or clock() - start < duration_s:
                        pending += device.readline()
                        if len(pending) > 4096:
                            pending = b""
                            log.warning("Discarded oversized serial line.")
                            continue
                        while b"\n" in pending:
                            line, pending = pending.split(b"\n", 1)
                            row = parse_line(line)
                            if row is None:
                                log.debug("Ignored invalid/startup serial line.")
                                continue
                            writer.write(row, weather.get(), weather_source=weather.source)
            except serial.SerialException:
                # Do not log exception URLs or tokens; do not append across outages.
                log.warning("Serial connection dropped/unavailable; retrying in %ss.", reconnect_s)
                writer.close()
                sleep(reconnect_s)
    except KeyboardInterrupt:
        log.info("Capture stopped by user.")
    finally:
        writer.close()
    log.info("Saved %s rows.", writer.rows)
    return writer.rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=config.SERIAL_PORT)
    parser.add_argument("--phase", choices=config.PHASES, required=True)
    parser.add_argument("--output", type=Path, default=config.DATA_RAW)
    parser.add_argument("--baud", type=int, default=config.BAUD)
    parser.add_argument("--duration-min", type=float)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--outdoor-c", type=float, default=config.OUTDOOR_FALLBACK_C)
    parser.add_argument("--latitude", type=float, default=config.LATITUDE)
    parser.add_argument("--longitude", type=float, default=config.LONGITUDE)
    parser.add_argument("--setpoint-c", type=float, default=config.SETPOINT_C)
    args = parser.parse_args()
    if args.duration_min is not None and args.duration_min <= 0:
        parser.error("--duration-min must be positive")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    weather = WeatherClient(args.latitude, args.longitude, args.outdoor_c, args.offline)
    rows = capture(args.port, args.phase, args.output, baud=args.baud,
                   duration_s=None if args.duration_min is None else args.duration_min * 60,
                   weather=weather, metadata={"latitude": args.latitude, "longitude": args.longitude,
                                              "setpoint_C": args.setpoint_c})
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
