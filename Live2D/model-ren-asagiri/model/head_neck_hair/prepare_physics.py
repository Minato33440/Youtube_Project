"""Build Ren's small-roll hair physics settings for import into Cubism Editor."""
from pathlib import Path
import json

root = Path(__file__).resolve().parent
settings, names = [], []
for i, (label, dest, radius, mobility, delay, accel, scale) in enumerate([
    ('Front and ahoge', 'ParamHairFront', 6, .86, .65, 1.2, 5.2),
    ('Side hair', 'ParamHairSide', 8, .90, .75, 1.0, 5.0),
    ('Back hair', 'ParamHairBack', 10, .86, .80, 1.1, 4.5),
], 1):
    pid = f'PhysicsSetting{i}'
    names.append({'Id': pid, 'Name': label})
    settings.append({
        'Id': pid,
        'Input': [{'Source': {'Target': 'Parameter', 'Id': 'ParamAngleZ'},
                   'Weight': 100, 'Type': 'Angle', 'Reflect': False}],
        'Output': [{'Destination': {'Target': 'Parameter', 'Id': dest},
                    'VertexIndex': 1, 'Scale': scale, 'Weight': 100,
                    'Type': 'Angle', 'Reflect': False}],
        'Vertices': [
            {'Position': {'X': 0, 'Y': 0}, 'Mobility': 1, 'Delay': 1,
             'Acceleration': 1, 'Radius': 0},
            {'Position': {'X': 0, 'Y': radius}, 'Mobility': mobility,
             'Delay': delay, 'Acceleration': accel, 'Radius': radius}],
        'Normalization': {
            'Position': {'Minimum': -10, 'Default': 0, 'Maximum': 10},
            'Angle': {'Minimum': -6, 'Default': 0, 'Maximum': 6}}
    })
data = {'Version': 3, 'Meta': {
    'PhysicsSettingCount': 3, 'TotalInputCount': 3, 'TotalOutputCount': 3,
    'VertexCount': 6, 'Fps': 60,
    'EffectiveForces': {'Gravity': {'X': 0, 'Y': -1}, 'Wind': {'X': 0, 'Y': 0}},
    'PhysicsDictionary': names}, 'PhysicsSettings': settings}
path = root / 'Ren_hair.physics3.json'
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(path)
