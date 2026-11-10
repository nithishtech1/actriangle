"""One conservative service verdict shared by the dashboard and PDF.

Legacy phase labels remain unchanged: blocked = before service, clean2 = after,
clean1 = optional healthy reference. A verdict concerns cooling performance only.
"""
from pathlib import Path
import pandas as pd
import config
from twin.analyze import analyze_run
from twin.data import DataError, is_fake, read_run
from twin.fit_tau import FitError
from twin.normalization import fit_weather_model

def stamp(value):
    return pd.to_datetime(value, utc=True)


LABELS = {'improved': 'Cooling performance improved',
          'not_improved': 'No clear cooling improvement',
          'inconclusive': 'Inconclusive - repeat or complete the test'}


def assess_service(paths, *, weather_baselines=(), setpoint=None, conditions_confirmed=False):
    paths = list(map(Path, paths))
    if len({p.resolve() for p in paths}) != len(paths):
        raise ValueError('Select distinct recordings.')
    if len({is_fake(p) for p in paths}) != 1:
        raise ValueError('Do not combine FAKE and real recordings.')
    frames = {str(read_run(p).phase.iloc[0]): p for p in paths}
    if len(frames) != len(paths) or not {'blocked', 'clean2'} <= set(frames) or set(frames) - {'clean1', 'blocked', 'clean2'}:
        raise ValueError('Select exactly one before-service (blocked) and after-service (clean2) run; clean1 is optional.')
    result = {'status': 'inconclusive', 'label': LABELS['inconclusive'], 'synthetic': is_fake(paths[0]),
              'records': [], 'reasons': [], 'warnings': [], 'raw_improvement_pct': None,
              'normalized_improvement_pct': None, 'expected_old_tau_min': None,
              'basis': 'unavailable', 'weather_detail': 'No weather training recordings selected.',
              'conditions_confirmed': bool(conditions_confirmed),
              'minimum_improvement_pct': config.SERVICE_MIN_IMPROVEMENT_PCT}
    reasons, warnings = result['reasons'], result['warnings']
    for phase in ('clean1', 'blocked', 'clean2'):
        if phase not in frames:
            continue
        try:
            record = analyze_run(frames[phase], setpoint)
            result['records'].append(record)
        except (FitError, DataError, ValueError) as exc:
            message = f'{phase}: {exc}'
            reasons.append(message)
    by_phase = {r['phase']: r for r in result['records']}
    if not {'blocked', 'clean2'} <= set(by_phase):
        return result
    before, after = by_phase['blocked'], by_phase['clean2']
    result['raw_improvement_pct'] = 100 * (before['tau_min'] - after['tau_min']) / before['tau_min']
    if not conditions_confirmed:
        reasons.append('Confirm the same AC/room, fan setting, doors/windows, occupancy and comparable solar conditions for all selected runs.')
    if stamp(after['recording_start']) <= stamp(before['recording_end']):
        reasons.append('After-service recording must start after the before-service recording ends.')
    if abs(before['start_C'] - after['start_C']) > config.SERVICE_MAX_START_DIFF_C:
        reasons.append(f'Start temperatures differ by over {config.SERVICE_MAX_START_DIFF_C:g} C; repeat from comparable starts.')
    setpoints = [r['setpoint_C'] for r in (before, after)]
    if any(x is None for x in setpoints):
        reasons.append('Record the actual AC setpoint for both runs.')
    elif abs(float(setpoints[0]) - float(setpoints[1])) > 0.5:
        reasons.append('AC setpoints differ; repeat with identical settings.')
    for key in ('fan_setting', 'test_unit'):
        if before.get(key) and after.get(key) and before[key] != after[key]:
            reasons.append(f'Recorded {key.replace("_", " ")} differs between runs.')
    for r in (before, after):
        if r['tau_std_min'] / r['tau_min'] > config.SERVICE_MAX_REL_TAU_STD:
            reasons.append(f"{r['phase']}: tau is too uncertain for a service verdict.")
        if r['outdoor_coverage'] < 0.9:
            reasons.append(f"{r['phase']}: outdoor temperature is missing for too much of the fit window.")
        if r['outdoor_min_C'] is not None and r['outdoor_max_C'] - r['outdoor_min_C'] > config.SERVICE_MAX_OUTDOOR_RANGE_C:
            reasons.append(f"{r['phase']}: outdoor temperature varied too much during the test.")
    weather_baselines = list(map(Path, weather_baselines))
    if weather_baselines:
        try:
            if len({p.resolve() for p in weather_baselines}) != len(weather_baselines):
                raise ValueError('Weather training files must be distinct independent recordings.')
            training = [analyze_run(p, setpoint) for p in weather_baselines]
            for r in training:
                if r['phase'] != 'blocked' or r['synthetic'] != result['synthetic']:
                    raise ValueError('Use before-service blocked runs of matching real/FAKE provenance.')
                if stamp(r['recording_end']) >= stamp(after['recording_start']):
                    raise ValueError('Weather training must precede the after-service run.')
                if r['outdoor_coverage'] < 0.9 or r['tau_std_min'] / r['tau_min'] > config.SERVICE_MAX_REL_TAU_STD:
                    raise ValueError('Weather training has missing outdoor data or uncertain tau.')
                if r['setpoint_C'] is None or before['setpoint_C'] is None or abs(float(r['setpoint_C']) - float(before['setpoint_C'])) > 0.5:
                    raise ValueError('Weather training requires the same recorded AC setpoint.')
                if abs(r['start_C'] - before['start_C']) > config.SERVICE_MAX_START_DIFF_C:
                    raise ValueError('Weather training must use comparable start temperatures.')
                if r['outdoor_max_C'] - r['outdoor_min_C'] > config.SERVICE_MAX_OUTDOOR_RANGE_C:
                    raise ValueError('Weather varies too much inside a training run.')
                for key in ('fan_setting', 'test_unit'):
                    if r.get(key) and before.get(key) and r[key] != before[key]:
                        raise ValueError(f'Weather training has a different {key}.')
            ordered = sorted(training, key=lambda r: stamp(r['recording_start']))
            if any(stamp(b['recording_start']) <= stamp(a['recording_end']) for a, b in zip(ordered, ordered[1:])):
                raise ValueError('Weather training recordings overlap; use independent runs.')
            model = fit_weather_model(training)
            if after['outdoor_mean_C'] is None:
                raise ValueError('After-service outdoor temperature is unavailable.')
            expected = model.predict(after['outdoor_mean_C'])
            result.update(expected_old_tau_min=expected,
                          normalized_improvement_pct=100 * (expected - after['tau_min']) / expected,
                          basis='weather-normalized')
            result['weather_detail'] = (f'{model.n_runs} before-service runs, {model.min_C:.1f}-{model.max_C:.1f} C; '
                                        f'expected old tau {expected:.2f} min at {after["outdoor_mean_C"]:.1f} C.')
            warnings.append('Small weather-regression demonstration; prediction uncertainty and seasonal accuracy are not validated.')
        except (ValueError, FitError, DataError, OSError) as exc:
            result['weather_detail'] = f'Unavailable: {exc}'
            warnings.append(result['weather_detail'])
    if result['normalized_improvement_pct'] is None:
        values = [r['outdoor_mean_C'] for r in (before, after)]
        if all(v is not None for v in values) and abs(values[0] - values[1]) <= config.SERVICE_MAX_OUTDOOR_DIFF_C:
            result['basis'] = 'matched outdoor conditions (raw comparison)'
            warnings.append('Weather normalization unavailable; raw comparison uses outdoor means within 1 C.')
        else:
            reasons.append('Outdoor conditions differ or are unknown; supply valid weather training or repeat in matched weather.')
    warnings.append('Prototype decision margins are provisional. This checks cooling performance, not every service procedure or fault.')
    if reasons:
        return result
    value = result['normalized_improvement_pct'] if result['normalized_improvement_pct'] is not None else result['raw_improvement_pct']
    # Guard against a positive verdict based on a numerically unstable curve fit.
    expected = result['expected_old_tau_min'] or before['tau_min']
    margin = 2 * (before['tau_std_min'] + after['tau_std_min'])
    if value >= config.SERVICE_MIN_IMPROVEMENT_PCT and expected - after['tau_min'] > margin:
        result['status'] = 'improved'
        reasons.append(f'Cooling time constant fell by {value:.1f}%, exceeding the provisional {config.SERVICE_MIN_IMPROVEMENT_PCT:g}% margin.')
    else:
        result['status'] = 'not_improved'
        reasons.append(f'Change in cooling time constant: {value:.1f}%. Clear improvement is not supported by this test; review or repeat the service check.')
    result['label'] = LABELS[result['status']]
    return result
