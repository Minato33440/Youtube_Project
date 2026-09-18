"""Create a standalone short opening; preserve and fingerprint Sample MP4 v1."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
D=P/'code_edit/hook_montage_v1'
MEDIA=P/'media/hook_montage_v1'
BASELINE=P/'exports/Sample-MP4_v1.mp4'
OUTPUT=P/'exports/Opening-montage_v1.mp4'
for path in [D,MEDIA]:path.mkdir(parents=True,exist_ok=True)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def run(args):
    r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace')
    if r.returncode:raise RuntimeError(r.stderr)
    return r.stdout

def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def fp(path):return str(path.resolve()).replace('\\','/').replace(':',r'\:')
def stamp(t):
    c=round(t*100);return f'{c//360000}:{c//6000%60:02}:{c//100%60:02}.{c%100:02}'

before=sha(BASELINE)
expected='5d85bdf43ee52dcb0f5f7610be7c1a31365c53133f19a4189ab5a3f3eea51f64'
assert before==expected,'Baseline changed since inspection; preserve and investigate before rendering.'
baseline_record=dict(path=str(BASELINE),sha256=before,size=BASELINE.stat().st_size,
    original_hook_source='HDIBA7-83yE',original_hook_in=150.16,original_hook_out=171.60,
    original_hook_timeline_seconds=21.4333333333,user_feedback='冒頭切り抜きは良い所を切り抜いている',
    recorded_at_utc=datetime.now(timezone.utc).isoformat())
save(D/'baseline_record.json',baseline_record)
for name,src in [('baseline_sample_v1_spec.json',P/'code_edit/sample_v1_spec.json'),
                 ('baseline_timeline.csv',P/'code_edit/sample_v1/timeline.csv')]:
    dest=D/name
    if not dest.exists():shutil.copy2(src,dest)

clips=[
    dict(id='M01',source_id='HDIBA7-83yE',a=150.16,b=157.40,topic='成長への投資',date='2025-12-13',
         reason='成長投資が将来の所得・成長を生むという理由と、国債による資金調達の主張を一緒に残す。',
         captions=[(0,5.55,'将来の所得を生む、成長投資'),(5.55,None,'その投資に、国債を使う')]),
    dict(id='M02',source_id='YXQjMSHSWEo',a=846.86,b=849.34,topic='減税の財源',date='2026-05-03',
         reason='税収の増加を財源とする説明の前提「名目GDPが持続的に上がる」を音声でも残す。',
         captions=[(0,None,'名目GDPの成長が続くなら')]),
    dict(id='M03',source_id='YXQjMSHSWEo',a=855.90,b=858.90,topic='減税の財源',date='2026-05-03',
         reason='直前の条件を受ける結論。説明の中間部分を省いて同じ話者の主張を短く提示。',
         captions=[(0,None,'税収の増加を、財源へ')]),
    dict(id='M04',source_id='VdKZeKSmo8o',a=895.38,b=899.20,topic='投資と暮らし',date='2026-09-05',
         reason='投資の成果が届くまでの家計支援。消費減税を含むという主張を保持。',
         captions=[(0,None,'消費減税を含めた、家計支援')]),
    dict(id='M05',source_id='VdKZeKSmo8o',a=901.80,b=905.84,topic='投資と暮らし',date='2026-09-05',
         reason='「その後」景気回復の果実を回すという順序と、政策戦略として述べている語尾を残す。',
         captions=[(0,None,'成長の果実を、暮らしへ')]),
]

style='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Header,Meiryo,32,&H00FFFFFF,&H00FFFFFF,&H00131D28,&H00131D28,0,0,0,0,100,100,0,0,1,1,0,7,64,64,4,1
Style: Caption,Meiryo,116,&H00FFFFFF,&H00FFFFFF,&H00131D28,&H00131D28,-1,0,0,0,100,100,0,0,1,4,1,5,70,70,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
timeline=[];cursor=0
for i,c in enumerate(clips):
    frames=math.floor((c['b']-c['a'])*30+.5);duration=frames/30
    header=f"本編ダイジェスト  ｜  {c['topic']}"
    ass=style+f"Dialogue: 0,0:00:00.00,{stamp(duration)},Header,,0,0,0,,{header}\n"
    ass+=f"Dialogue: 0,0:00:00.00,{stamp(duration)},Header,,0,0,0,,{{\\pos(64,43)\\fs21}}三橋TV ｜ {c['date']}公開 ｜ 会田卓司氏の発言\n"
    ass+=f"Dialogue: 0,0:00:00.00,{stamp(duration)},Header,,0,0,0,,{{\\pos(72,865)\\fs23\\c&H62ADD5&}}発言の要点\n"
    for a,b,text in c['captions']:
        for word in ['成長投資','国債','成長が続くなら','財源','家計支援','暮らし']:
            if word in text:
                text=text.replace(word,r'{\c&H62ADD5&}'+word+r'{\c&HFFFFFF&}')
        ass+=f"Dialogue: 1,{stamp(a)},{stamp(duration if b is None else b)},Caption,,0,0,0,,{{\\pos(960,963)}}{text}\n"
    ass_path=MEDIA/(c['id']+'.ass');ass_path.write_text(ass,encoding='utf-8-sig')
    # A subtle zoom on the second tax excerpt makes the internal jump visible.
    zoom='scale=1978:1112,crop=1920:1080:29:16,' if c['id']=='M03' else ''
    vf=(f"setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
        f"{zoom}setsar=1,fps=30,tpad=stop_mode=clone:stop_duration=0.1,trim=end_frame={frames},"
        "drawbox=x=0:y=0:w=iw:h=77:color=0x101c2a@0.9:t=fill,"
        "drawbox=x=0:y=842:w=iw:h=238:color=0x101c2a@0.80:t=fill,"
        f"subtitles=filename='{fp(ass_path)}',format=yuv420p")
    if i==len(clips)-1:vf+=f',fade=t=out:st={duration-.1}:d=0.1'
    af=(f'asetpts=PTS-STARTPTS,aresample=48000,loudnorm=I=-18:TP=-2:LRA=11,apad,atrim=duration={duration},'
        f'afade=t=in:d=0.012,afade=t=out:st={duration-.015}:d=0.015,aformat=sample_rates=48000:channel_layouts=stereo')
    target=MEDIA/(c['id']+'.mkv')
    print('RENDER',c['id'],duration,flush=True)
    run(['ffmpeg','-v','error','-y','-threads','4','-ss',str(c['a']),'-t',str(c['b']-c['a']),
         '-i',str(P/'media/sources'/(c['source_id']+'.mp4')),'-vf',vf,'-af',af,
         '-c:v','libx264','-threads','4','-preset','veryfast','-crf','19','-c:a','pcm_s16le',str(target)])
    timeline.append(dict(**c,timeline_in=cursor,timeline_out=cursor+duration,frames=frames,intermediate=str(target)))
    cursor+=duration

concat=D/'concat.txt';concat.write_text(''.join(f"file '{Path(c['intermediate']).as_posix()}'\n" for c in timeline),encoding='utf-8')
tmp=OUTPUT.with_suffix('.pending.mp4')
run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(concat),'-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(tmp)])
probe=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(tmp)]))
video=next(s for s in probe['streams'] if s['codec_type']=='video')
assert int(video['nb_frames'])==sum(c['frames'] for c in timeline)
assert abs(float(probe['format']['duration'])-cursor)<.04
run(['ffmpeg','-v','error','-xerror','-i',str(tmp),'-f','null','-'])
assert sha(BASELINE)==before
tmp.replace(OUTPUT)
save(D/'manifest.json',dict(output=str(OUTPUT),reference_url='https://www.youtube.com/watch?v=4nR3dvrMdB0',
    baseline=baseline_record,baseline_unchanged=True,duration=float(probe['format']['duration']),
    timeline=timeline,probe=probe,technical_decode='passed',captions='Editorial summaries, labelled 発言の要点; not verbatim quotations',
    listening='not available',agent_count=0,reasoning_effort='effective parent setting not verified'))
print('DONE',OUTPUT,cursor,flush=True)
