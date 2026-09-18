"""Map aligned Japanese phones to this rig's single mouth-open parameter.

This is a coarticulated aperture approximation, not a five-viseme mouth rig.
Audio remains unchanged. Phone times are measured by the alignment stage.
"""
from pathlib import Path
import csv
import json
import wave
import numpy as np

ROOT = Path(__file__).resolve().parent
FPS, COUNT = 30, 478
VOWEL_OPEN = {'a': .80, 'e': .64, 'o': .59, 'i': .43, 'u': .38}
CLOSED = {'m', 'b', 'p', 'cl'}
SILENCE = {'sil', 'silB', 'silE', 'sp', 'pau'}
LEAD = .020

def main():
    raw = json.loads((ROOT / 'alignment/phonemes.json').read_text(encoding='utf-8-sig'))
    phones = raw if isinstance(raw, list) else raw['phonemes']
    for p in phones:
        p['start_s'], p['end_s'] = float(p['start_s']), float(p['end_s'])
    with wave.open(str(ROOT / 'audio_mono_44100_pcm16.wav')) as w:
        rate = w.getframerate()
        sound = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(float) / 32768
    def rms(start, end):
        a, b = max(0, round(start * rate)), min(len(sound), round(end * rate))
        return float(np.sqrt(np.mean(sound[a:b] ** 2))) if b > a else 0.
    energies = [rms(p['start_s'], p['end_s']) for p in phones if p['phoneme'].lower().rstrip(':') in VOWEL_OPEN]
    reference = float(np.percentile(energies, 85))
    # Work at 1 ms before resampling to the model's 30 fps. Smoothing is centered
    # so it does not add the old causal envelope's tail/attack delay.
    t = np.arange(0, COUNT/FPS + .1, .001)
    target = np.zeros(len(t))
    for i, p in enumerate(phones):
        ph = p['phoneme']
        vowel = ph.lower().rstrip(':')
        energy = rms(p['start_s'], p['end_s'])
        if ph in SILENCE or ph in CLOSED:
            value = 0.
        elif vowel in VOWEL_OPEN:
            strength = .84 + .16 * np.clip(energy / max(reference, .0001), 0, 1)
            value = VOWEL_OPEN[vowel] * strength
            if ph.isupper():  # unvoiced I/U, if present in the acoustic model
                value *= .72
        elif ph == 'N':
            value = .14
        elif ph in {'s', 'sh', 'z', 'j', 'ch', 'ts', 'f'}:
            value = .19 if ph != 'f' else .12
        else:
            following = next((q['phoneme'].lower().rstrip(':') for q in phones[i+1:i+4] if q['phoneme'].lower().rstrip(':') in VOWEL_OPEN), 'u')
            value = VOWEL_OPEN[following] * .56
        p['target_open'], p['rms'] = round(float(value), 6), energy
        target[(t >= max(0, p['start_s'] - LEAD)) & (t < p['end_s'] - LEAD)] = value
    # Acoustic silence overrides an uncertain aligned phone. This matters when
    # the speaker pauses without punctuation in the written transcript.
    bins = np.arange(0, COUNT/FPS, .01)
    quiet = np.array([rms(b, b+.01) < .001 for b in bins])
    silent_runs, begin = [], None
    for i in range(len(quiet)+1):
        is_quiet = i < len(quiet) and quiet[i]
        if is_quiet and begin is None: begin = i
        if not is_quiet and begin is not None:
            if i-begin >= 4:
                start, end = bins[begin], min(i*.01, COUNT/FPS)
                target[(t >= max(0,start-LEAD)) & (t < end-LEAD)] = 0
                silent_runs.append([float(start),float(end)])
            begin = None
    x = np.arange(-42, 43) / 1000
    kernel = np.exp(-.5 * (x/.014)**2)
    smooth = np.convolve(target, kernel/kernel.sum(), mode='same')
    times = np.arange(COUNT) / FPS
    values = np.interp(times, t, smooth)
    closures = []
    # Preserve a readable lip closure for bilabial consonants. Other consonants
    # do not all require the lips to close; treating each phone as a flap is avoided.
    for p in phones:
        if p['phoneme'] in CLOSED and p['end_s'] - p['start_s'] >= .035:
            idx = int(round(((p['start_s']+p['end_s'])/2 - LEAD) * FPS))
            if 0 <= idx < COUNT:
                values[idx] = 0
                closures.append({'frame': idx, 'time_s': idx/FPS, 'phoneme': p['phoneme'], 'sentence': p.get('sentence'), 'mora': p.get('mora')})
    values[times >= 15.602] = 0
    values[values < .025] = 0
    # Rate limiting from both directions preserves closure anchors while avoiding
    # a one-frame pop immediately before/after them.
    for i in range(1, COUNT):
        values[i] = min(values[i], values[i-1] + .34)
    for i in range(COUNT-2, -1, -1):
        values[i] = min(values[i], values[i+1] + .34)
    # Match the supplied clip's narration range; the post-narration transient is excluded.
    values = np.round(values, 6)
    prior = list(csv.DictReader((ROOT.parent / 'voice_sync_v1/mouth_curve.csv').open()))
    rows = []
    for i, (time, value) in enumerate(zip(times, values)):
        p = next((p for p in phones if p['start_s'] <= time < p['end_s']), {})
        rows.append({'frame': i, 'time_s': round(float(time),6), 'rms': round(rms(time-1/60,time+1/60),8), 'mouth_open_y': float(value), 'v1_open': float(prior[i]['mouth_open_y']), 'phoneme': p.get('phoneme','sil'), 'sentence': p.get('sentence',''), 'mora': p.get('mora','')})
    with (ROOT/'mouth_curve.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader();writer.writerows(rows)
    meta = {'method': 'Aligned Japanese phone aperture + phone-level energy + centered coarticulation', 'vowel_targets': VOWEL_OPEN, 'lead_seconds': LEAD, 'gaussian_sigma_seconds': .014, 'max_step_per_frame': .34, 'closure_anchors': closures, 'phonemes_with_targets': phones, 'frames': rows, 'limits': ['One open parameter; no lip rounding or width change', 'Phone boundaries are automatic estimates, not manually verified ground truth']}
    meta['acoustic_silence_intervals'] = silent_runs
    (ROOT/'mouth_curve.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    segments = [0.,float(values[0])]
    for time,value in zip(times[1:],values[1:]): segments.extend([0,round(float(time),6),float(value)])
    motion={'Version':3,'Meta':{'Duration':COUNT/FPS,'Fps':FPS,'Loop':False,'CurveCount':1,'TotalSegmentCount':COUNT-1,'TotalPointCount':COUNT,'AreBeziersRestricted':True},'Curves':[{'Target':'Parameter','Id':'ParamMouthOpenY','Segments':segments}],'UserData':[]}
    (ROOT/'voice_sync.motion3.json').write_text(json.dumps(motion,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'phones':len(phones),'closures':closures,'peak':float(values.max()),'max_step':float(np.abs(np.diff(values)).max())},ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
