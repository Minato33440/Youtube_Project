"""Composite the approved performance style, keeping the original audio stream."""
import csv,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
M=P/'media/sample_v1_risa'
R=ROOT/'output/live2d/full_sample_v1'
def run(args):
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',*map(str,args)],check=True)
def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--package-filmora-media',action='store_true');ap.add_argument('--prototype',action='store_true');options=ap.parse_args()
    rows=list(csv.DictReader((P/'code_edit/sample_v1/timeline.csv').open(encoding='utf-8-sig')))
    narr=[r for r in rows if r['type']=='narration']
    # Preserve real MP4 sample timestamps, fill packet gaps, and pad exact frame lengths.
    for r in narr if options.package_filmora_media else []:
        dur=int(r['planned_frames'])/30
        run(['-i',P/'exports/Sample-MP4_v1.mp4','-ss',r['timeline_in'],'-t',dur,'-vn','-af','aresample=48000:async=1:first_pts=0','-c:a','pcm_s16le','-ac','2',M/'audio'/f"{r['id']}.wav"])
        print('audio',r['id'],flush=True)
    args=['-threads','4','-i',P/'exports/Sample-MP4_v1.mp4']
    for r in narr: args+=['-threads','2','-i',R/r['id']/f"{r['id']}_alpha_512x560.mov"]
    # Normalize the original millisecond timestamps to its existing 30fps frame
    # order, then use exact frame numbers for every overlay boundary.
    filters=['[0:v]settb=1/30,setpts=N[base]'];last='base'
    for i,r in enumerate(narr,1):
        start=float(r['timeline_in']);end=float(r['timeline_out'])
        # The original concat has millisecond PTS jitter. Hold the final alpha
        # frame through the exact interval so it cannot disappear one frame early.
        start_frame=round(start*30);end_frame=start_frame+int(r['planned_frames'])
        filters += [f'[{i}:v]scale=384:420,settb=1/30,setpts=N+{start_frame}[a{i}]',f'[{last}][a{i}]overlay=1275:99:eof_action=repeat:repeatlast=1:enable=\'between(n,{start_frame},{end_frame-1})\'[v{i}]']
        last=f'v{i}'
    out=P/('media/sample_v1_risa/qa/boundary_prototype.mp4' if options.prototype else 'exports/Sample-MP4_v1-Risa-complete.mp4')
    run(args+['-filter_complex_threads','2','-filter_complex',';'.join(filters),'-map',f'[{last}]','-map','0:a:0','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','8','-frames:v','1140' if options.prototype else '29733','-c:a','copy','-movflags','+faststart',out])
    if options.prototype:return
    # -frames:v can stop muxing before the final audio packet. Remux the full
    # original stream afterward so every packet, including the tail, is preserved.
    remux=out.with_name(out.stem+'-remux.mp4')
    run(['-i',out,'-i',P/'exports/Sample-MP4_v1.mp4','-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',remux])
    remux.replace(out)
    print('complete',out,flush=True)
    for r in narr if options.package_filmora_media else []:
        run(['-threads','2','-i',R/r['id']/f"{r['id']}_alpha_512x560.mov",'-vf','scale=384:420,format=rgba,pad=1920:1080:1275:99:color=black@0','-c:v','prores_ks','-profile:v','4','-pix_fmt','yuva444p10le','-threads','4',M/'live2d'/f"{r['id']}.mov"])
        print('Filmora alpha',r['id'],flush=True)
if __name__=='__main__':main()
