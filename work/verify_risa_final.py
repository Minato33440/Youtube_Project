import csv,json,subprocess,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
OUT=P/'code_edit/sample_v1_risa';OUT.mkdir(exist_ok=True)
original=P/'exports/Sample-MP4_v1.mp4'
final=P/'exports/Sample-MP4_v1-Risa-complete.mp4'
def cmd(args):return subprocess.check_output(list(map(str,args)))
def probe(p):return json.loads(cmd(['ffprobe','-v','error','-show_streams','-show_format','-of','json',p]))
def audio_hash(p):return cmd(['ffmpeg','-v','error','-i',p,'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip()
def frame(p,t):
    import io
    return Image.open(io.BytesIO(cmd(['ffmpeg','-v','error','-ss',t,'-i',p,'-frames:v','1','-f','image2pipe','-c:v','png','-'])))
def main():
    a,b=probe(original),probe(final)
    decode=subprocess.run(['ffmpeg','-v','error','-threads','4','-i',str(final),'-f','null','-'],capture_output=True)
    report={'original':str(original),'final':str(final),'probe':b,'decode_exit':decode.returncode,'decode_errors':decode.stderr.decode(),'original_audio_hash':audio_hash(original),'final_audio_hash':audio_hash(final)}
    report['audio_identical']=report['original_audio_hash']==report['final_audio_hash']
    assert decode.returncode==0 and not decode.stderr
    assert int(b['streams'][0]['nb_frames'])==29733
    assert report['audio_identical'], 'Copied audio packets differ'
    rows=list(csv.DictReader((P/'code_edit/sample_v1/timeline.csv').open(encoding='utf-8-sig')))
    narr=[r for r in rows if r['type']=='narration']
    sheet=Image.new('RGB',(1440,5*290),(24,24,24));d=ImageDraw.Draw(sheet)
    for i,r in enumerate(narr):
        t=float(r['timeline_in'])+3
        for j,(label,path) in enumerate((('original',original),('with Risa',final))):
            im=frame(path,t);im.thumbnail((480,270));sheet.paste(im,(j*480,i*290+20));d.text((j*480+5,i*290+3),f"{r['id']} {t:.3f}s {label}",fill='white')
        im=frame(final,t).crop((1255,80,1680,530));im.thumbnail((450,270));sheet.paste(im,(960,i*290+20))
    sheet.save(OUT/'narration_contact_sheet.jpg',quality=94)
    (OUT/'technical_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='probe'},indent=2))
if __name__=='__main__':main()
