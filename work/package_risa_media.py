"""Preserve Sample v1 timing and prepare independent Filmora media."""
import csv, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
OUT=P/'media/sample_v1_risa'
def run(args):
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',*map(str,args)],check=True)
def main():
    for d in ('video','backgrounds','audio','live2d','qa'): (OUT/d).mkdir(parents=True,exist_ok=True)
    rows=list(csv.DictReader((P/'code_edit/sample_v1/timeline.csv').open(encoding='utf-8-sig')))
    for r in rows:
        name=r['id']; src=Path(r['intermediate']); duration=int(r['planned_frames'])/30
        if r['type']=='video':
            dst=OUT/'video'/f'{name}.mp4'
            if not dst.exists(): run(['-i',src,'-map','0:v:0','-map','0:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t',duration,'-movflags','+faststart',dst])
        else:
            dst=OUT/'backgrounds'/f'{name}.mp4'
            if not dst.exists(): run(['-i',src,'-map','0:v:0','-an','-c:v','copy','-movflags','+faststart',dst])
            dst=OUT/'audio'/f'{name}.wav'
            if not dst.exists(): run(['-i',src,'-map','0:a:0','-vn','-af',f'apad,atrim=duration={duration}','-c:a','pcm_s16le','-ar','48000','-ac','2',dst])
        print(name,flush=True)
    run(['-framerate','30','-i',ROOT/'output/live2d/voice_sync_v4/frames/%05d.png','-frames:v','60','-vf','crop=512:560:128:0,scale=384:420,format=rgba,pad=1920:1080:1275:99:color=black@0','-c:v','prores_ks','-profile:v','4','-pix_fmt','yuva444p10le','-threads','4',OUT/'qa/alpha_test.mov'])
    (OUT/'asset_timeline.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__': main()

