"""Prepare clearly labeled service and weather demo fixtures."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import config
from twin.gen_synthetic import generate_all, generate_run


def prepare(output=config.DATA_REPLAY):
    output = Path(output)
    paths = generate_all(output, overwrite=True)
    weather = output / 'weather'
    weather.mkdir(exist_ok=True)
    for i, (outdoor, tau) in enumerate([(31, 12), (35, 16)]):
        start = datetime(2026, 11, 8, 9 + 2*i, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        df = generate_run('blocked', start=start, noise=0.05, seed=100+i)
        t = df.ms.to_numpy()/60000
        df.room_C = 24 + 6*np.exp(-t/tau) + np.random.default_rng(100+i).normal(0, 0.05, len(t))
        df.outdoor_C = outdoor
        path = weather / f'FAKE_run_blocked_{start:%Y%m%d_%H%M}.csv'
        df.to_csv(path, index=False)
        paths.append(path)
    for path in paths:
        path.with_suffix('.meta.json').write_text(json.dumps({'synthetic': True, 'setpoint_C': 18,
            'fan_setting': 'high', 'test_unit': 'FAKE-demo-room'}, indent=2), encoding='utf-8')
    return paths


if __name__ == '__main__':
    for path in prepare():
        print('FAKE:', path.name)
