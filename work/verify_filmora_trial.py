"""Verify the natively saved/exported Filmora trial against its source assets."""
import argparse, json, subprocess, zipfile, io
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stem',default='Risa_Layered_Trial_20260915')
args=parser.parse_args()
OUT=P/f'exports/{args.stem}.mp4'
REPORT=P/'code_edit/sample_v1_risa'

def pcm(path,start=0,duration=None):
    cmd=['ffmpeg','-v','error','-i',str(path),'-ss',str(start)]
    if duration is not None:cmd+=['-t',str(duration)]
    return np.frombuffer(subprocess.check_output(cmd+['-vn','-ac','1','-ar','16000','-f','f32le','-']),dtype=np.float32)

checks=[]
for name,start,dur in [('HOOK',0,21.433333),('N01',643/30,479/30),('C01a',1122/30,1121/30),('C01b',2243/30,473/30),('C02a',2716/30,1184/30),('C02b',3900/30,845/30)]:
    source=P/'media/sample_v1_risa'/('audio/N01.wav' if name=='N01' else f'video/{name}.mp4')
    a=pcm(source,0,dur);b=pcm(OUT,start,dur);n=min(len(a),len(b));a=a[:n];b=b[:n]
    size=1<<(2*n-1).bit_length();cc=np.fft.irfft(np.fft.rfft(b,size)*np.conj(np.fft.rfft(a,size)),size)
    lags=np.arange(-1600,1601);lag=int(lags[np.argmax(cc[lags%size])]);aa=a[max(0,-lag):min(n,n-lag)];bb=b[max(0,lag):min(n,n+lag)]
    corr=float(np.dot(aa,bb)/(np.linalg.norm(aa)*np.linalg.norm(bb))) if np.any(bb) else 0
    checks.append(dict(segment=name,offset_ms=lag/16,correlation=corr,rms=float(np.sqrt(np.mean(b*b))),passed=corr>.98 and abs(lag)<533))

probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(OUT)]))
decode=subprocess.run(['ffmpeg','-v','error','-i',str(OUT),'-f','null','-'],capture_output=True,text=True)
wfp=P/f'filmora/{args.stem}.wfp'
with zipfile.ZipFile(wfp) as z:
    info=json.loads(z.read('ProjectFolder/project_info.json'))
    doc=json.loads(z.read(f"ProjectFolder/Medias/{info['timeline_mediaId']}/timeline.wesproj"))
    paths=[Path(r['filename'].removeprefix('file:/')) for r in doc['resources']]
    tracks=[dict(type=t['trackType'],clips=[dict(file=c['filename'],begin=c['tlBegin'],end=c['tlEnd']) for c in t['clipList']]) for t in doc['timelineInfos'][0]['trackInfos']]

sheet=Image.new('RGB',(960,810),'#202020');draw=ImageDraw.Draw(sheet)
for i,t in enumerate([10,21.5,26,36.9,37.433333,140]):
    data=subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(OUT),'-frames:v','1','-vf','scale=480:270','-f','image2pipe','-vcodec','png','-'])
    im=Image.open(io.BytesIO(data));x=i%2*480;y=i//2*270;sheet.paste(im,(x,y));draw.rectangle((x,y,x+120,y+20),fill='black');draw.text((x+5,y+4),f'{t:.3f} sec',fill='white')
sheet.save(REPORT/f'{args.stem}_contact_sheet.jpg',quality=95)
motion_path=REPORT/'motion_checks'/f'{args.stem}.motion_check.json'
motion=json.loads(motion_path.read_text(encoding='utf-8')) if motion_path.exists() else {}
time_maps=[]
for t in doc['timelineInfos'][0]['trackInfos']:
    if t['trackType']!=1:continue
    for c in t['clipList']:
        speed=c.get('speed',{});curve=json.loads(speed.get('speedParam','{}'))
        duration=(c['outPoint']-c['inPoint'])/1e7
        time_maps.append(dict(file=c['filename'],passed=abs(speed.get('offsetEnd',0)-duration)<1e-6 and abs(curve.get('_totalTime',0)-duration)<1e-6))
result=dict(project=str(wfp),export=str(OUT),native_save_and_reopen='GUI observation required; not inferred by this script',video_frames=probe['streams'][0]['nb_frames'],duration=probe['format']['duration'],decode_passed=decode.returncode==0,decode_errors=decode.stderr,media_references_exist=all(p.exists() for p in paths),tracks=tracks,audio_checks=checks,video_time_maps=time_maps,motion_check_passed=motion.get('passed',False),motion_check_report=str(motion_path),human_full_playback_review='pending')
result['technical_passed']=result['decode_passed'] and result['media_references_exist'] and result['video_frames']=='4745' and all(c['passed'] for c in checks) and all(c['passed'] for c in time_maps) and result['motion_check_passed']
(REPORT/f'{args.stem}_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='tracks'},ensure_ascii=False,indent=2))
