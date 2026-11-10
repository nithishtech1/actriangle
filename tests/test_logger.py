from datetime import datetime, timezone
import json
from unittest.mock import Mock

import pandas as pd
import pytest
import requests
import serial

from logger.log_serial import RunWriter, capture, parse_line
from logger.weather import WeatherClient
from app.notifications import send_telegram


@pytest.mark.parametrize("line", [b"ms,probe0_C,probe1_C,room_C,room_RH", b"SHT31 not found", b"\xff\xff",
                                    b"2,-127,24,24,60", b"2,20,nan,24,60", b"2,20,25,24,120",
                                    b"-1,20,25,24,60", b"2,85,25,24,60", b"2,20,inf,24,60"])
def test_invalid_sensor_lines_ignored(line):
    assert parse_line(line) is None


def test_mapping_offsets_and_validation():
    row = parse_line(b"5800,25,17,24,60\r\n", roles={"probe0": "return", "probe1": "supply"},
                     offsets={"supply_C": -0.5, "return_C": 0.2})
    assert row == {"ms": 5800, "return_C": 25.2, "supply_C": 16.5, "room_C": 24, "room_RH": 60}
    with pytest.raises(ValueError):
        parse_line("1,20,25,24,60", roles={"probe0": "return", "probe1": "return"})


def test_writer_flush_duplicate_reset_and_no_overwrite(tmp_path):
    stamp = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    writer = RunWriter(tmp_path, "clean1")
    row = parse_line("5800,18,25,24,60")
    assert writer.write(row, 33, now=stamp, weather_source="typed fallback")
    first = writer.path
    assert len(pd.read_csv(first)) == 1  # readable before close -> per-row flush
    assert not writer.write(row, 33, now=stamp)
    assert writer.write({**row, "ms": 0}, 33, now=stamp)
    assert writer.path != first
    assert first.name == "run_clean1_20261109_1200.csv"
    assert writer.path.name.endswith("_01.csv")
    writer.close()
    assert len(list(tmp_path.glob("*.csv"))) == 2
    metadata = json.loads(first.with_suffix(".meta.json").read_text())
    assert not metadata["synthetic"]
    assert "typed fallback" in first.with_suffix(".weather.jsonl").read_text()


def test_weather_cache_refresh_and_fallback():
    session = Mock()
    session.get.return_value.json.return_value = {"current": {"temperature_2m": 34}}
    clock = Mock(return_value=0)
    weather = WeatherClient(fallback=32, session=session, clock=clock)
    assert weather.get() == 34
    clock.return_value = 599
    assert weather.get() == 34
    assert session.get.call_count == 1
    clock.return_value = 600
    session.get.side_effect = requests.ConnectionError("offline")
    assert weather.get() == 32
    assert weather.source == "typed fallback"
    assert WeatherClient(offline=True).get() is None


def test_five_minute_simulated_serial_capture_with_reconnect(tmp_path):
    class Clock:
        seconds = 0
        def __call__(self):
            return self.seconds
        def sleep(self, seconds):
            self.seconds += seconds
    clock = Clock()
    count = 0
    connections = 0

    class Device:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def readline(self):
            nonlocal count
            if count == 20 and connections == 1:
                raise serial.SerialException("unplugged")
            count += 1
            clock.seconds += 5
            return f"{count*5000},18,25,24,60\n".encode()

    def factory(*args, **kwargs):
        nonlocal connections
        connections += 1
        return Device()

    rows = capture("SIMULATED", "clean1", tmp_path, duration_s=300,
                    weather=WeatherClient(fallback=33, offline=True), serial_factory=factory,
                    clock=clock, sleep=clock.sleep)
    assert rows == 60
    assert connections == 2
    assert len(list(tmp_path.glob("*.csv"))) == 2
    assert sum(len(pd.read_csv(p)) for p in tmp_path.glob("*.csv")) == 60


def test_disk_errors_not_swallowed_as_serial_disconnect(tmp_path, monkeypatch):
    device = Mock()
    device.__enter__ = Mock(return_value=device)
    device.__exit__ = Mock(return_value=False)
    device.readline.return_value = b"5000,18,25,24,60\n"
    monkeypatch.setattr(RunWriter, "write", Mock(side_effect=OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        capture("SIMULATED", "clean1", tmp_path, duration_s=1,
                weather=WeatherClient(offline=True), serial_factory=lambda *a, **kw: device)


def test_telegram_is_explicit_and_redacts_errors():
    session = Mock()
    session.post.return_value.json.return_value = {"ok": True}
    assert send_telegram("test", token="secret", chat_id="123", session=session).ok
    session.post.side_effect = requests.ConnectionError("https://api.telegram.org/botsecret")
    result = send_telegram("test", token="secret", chat_id="123", session=session)
    assert not result.ok and "secret" not in result.detail
    assert not send_telegram("test", token="", chat_id="").ok
