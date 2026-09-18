import json, pathlib, urllib.request, urllib.parse, wave

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'Politics_Economics/2026-09-09_fiscal_policy/speech'
BASE = 'http://127.0.0.1:50121'

def request(path, data=None):
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as response:
        return response.read()

speakers = json.loads(request('/speakers'))
speaker = next(s for s in speakers if s['name'] == '女声1')
style = next(s for s in speaker['styles'] if s['name'] == 'ノーマル')
manifest = {'engine': 'VOICEVOX Nemo Engine', 'engine_version': json.loads(request('/version')), 'speaker': speaker, 'credit': 'VOICEVOX Nemo', 'items': []}
for stem in ['01_opening', '02_tax_burden', '03_household_support']:
    text = (OUT / f'{stem}.txt').read_text(encoding='utf-8').strip()
    query = json.loads(request('/audio_query?' + urllib.parse.urlencode({'text': text, 'speaker': style['id']}), b''))
    query.update(speedScale=1.0, pitchScale=0.0, intonationScale=1.0, volumeScale=1.0,
                 prePhonemeLength=0.25, postPhonemeLength=0.4, outputSamplingRate=48000, outputStereo=False)
    (OUT / f'{stem}.audio_query.json').write_text(json.dumps(query, ensure_ascii=False, indent=2), encoding='utf-8')
    wav = OUT / f'{stem}_nemo_f1.wav'
    wav.write_bytes(request('/synthesis?' + urllib.parse.urlencode({'speaker': style['id']}), json.dumps(query).encode('utf-8')))
    with wave.open(str(wav)) as f:
        duration = f.getnframes()/f.getframerate()
        assert f.getnchannels() == 1 and f.getframerate() == 48000
    manifest['items'].append({'id': stem, 'text': text, 'wav': str(wav), 'duration_seconds': duration, 'kana': query.get('kana')})
    print(stem, round(duration, 3), query.get('kana'), flush=True)
(OUT / 'nemo_generation_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
