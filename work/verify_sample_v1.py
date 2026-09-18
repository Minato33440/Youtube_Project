"""Verify rendered audio placement and capture review frames; does not listen."""
from pathlib import Path
import json
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
OUT=P/'code_edit/sample_v1'
manifest=json.loads((OUT/'render_manifest.json').read_text(encoding='utf-8'))
final=Path(manifest['output'])
qa=OUT/'qa'
qa.mkdir(exist_ok=True)

def audio(path,start):
    result=subprocess.run(['ffmpeg','-v','error','-ss',str(start),'-i',str(path),'-t','3',
                           '-vn','-ac','1','-ar','8000','-f','f32le','-'],capture_output=True,check=True)
    x=np.frombuffer(result.stdout,dtype='<f4').astype(np.float64)
    return x-x.mean()

checks=[]
for row in manifest['segments']:
    reference=audio(row['source'],float(row['source_in'] or 0)+2)
    actual=audio(final,float(row['timeline_in'])+2)
    n=min(len(reference),len(actual));a=reference[:n];b=actual[:n]
    length=1 << (2*n-1).bit_length()
    corr=np.fft.irfft(np.fft.rfft(a,length)*np.conj(np.fft.rfft(b,length)),length)
    lags=np.arange(-400,401)
    vals=corr[lags%length]/max(1e-20,np.linalg.norm(a)*np.linalg.norm(b))
    best=int(np.argmax(vals));score=float(vals[best]);lag=float(lags[best]/8000)
    checks.append(dict(id=row['id'],normalized_correlation=score,lag_seconds=lag,
                       passed=score>.90 and abs(lag)<.05))
    print(row['id'],round(score,4),lag,flush=True)

sheet=Image.new('RGB',(1920,1188),'#17212c')
d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc',24)
ids=['HOOK','N01','N02','ND01','N03','C03','N04','C06','N05']
headers=[]
for row in manifest['segments']:
    cid=row['id']
    png=qa/f'{cid}.png'
    subprocess.run(['ffmpeg','-v','error','-ss',str(float(row['timeline_in'])+3),'-i',str(final),
                    '-frames:v','1','-y',str(png)],capture_output=True,check=True)
    full=Image.open(png)
    if row['type']=='video':
        band=np.asarray(full)[:68,64:1800,:3]
        bright_pixels=int(np.sum(np.min(band,axis=2)>150))
        headers.append(dict(id=cid,bright_pixels=bright_pixels,passed=bright_pixels>200))
    if cid not in ids:
        continue
    idx=ids.index(cid)
    im=full.resize((640,360))
    x=(idx%3)*640;y=(idx//3)*396
    sheet.paste(im,(x,y+36));d.text((x+10,y+2),cid,font=font,fill='white')
sheet.save(qa/'contact_sheet.jpg',quality=92)
result=dict(audio_placement=checks,all_audio_placement_passed=all(c['passed'] for c in checks),
            header_presence=headers,all_headers_present=all(h['passed'] for h in headers),
            method='3 second waveform FFT cross-correlation at +2s in every segment against its source; checks placement, not intelligibility or lip sync.',
            listening='not available in this session',contact_sheet=str(qa/'contact_sheet.jpg'))
(OUT/'qa_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if not result['all_audio_placement_passed'] or not result['all_headers_present']:
    raise SystemExit('Audio placement or header visibility requires investigation')
