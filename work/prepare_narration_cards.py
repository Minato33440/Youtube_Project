import json, pathlib, math, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
SPEECH=BASE/'speech'
OUT=BASE/'media/narration_v2'
OUT.mkdir(exist_ok=True,parents=True)
manifest=json.loads((SPEECH/'nemo_generation_manifest.json').read_text(encoding='utf-8'))
font='C:/Windows/Fonts/YuGothM.ttc'
titles=['減税の財源を、成長から考える','経済の成長と、税負担の増え方','投資の成果が届くまで、暮らしを支える']
lines=[['減税の話になると、必ず問われる財源。','しかし、経済が成長して税収が増える可能性は、','どう考えられているのでしょうか。'],['ここからは、経済の成長より税負担が','速く増えていないか、という話です。'],['投資の成果が給料に届くまでには時間がかかる。','その間の暮らしをどう支えるかが、次の論点です。']]
for i,item in enumerate(manifest['items']):
    im=Image.new('RGB',(1920,1080),(16,29,43));d=ImageDraw.Draw(im)
    d.rectangle((130,220,220,226),fill=(95,201,191))
    d.text((130,135),'対談を読み解く',font=ImageFont.truetype(font,32),fill=(145,177,190))
    d.text((130,280),titles[i],font=ImageFont.truetype(font,64),fill=(247,247,239))
    for j,line in enumerate(lines[i]):d.text((130,470+85*j),line,font=ImageFont.truetype(font,43),fill=(220,230,236))
    d.text((130,953),'ナレーション：VOICEVOX Nemo',font=ImageFont.truetype(font,26),fill=(145,177,190))
    png=OUT/(item['id']+'.png'); im.save(png)
    frames=math.ceil(item['duration_seconds']*30)
    mp4=OUT/(item['id']+'.mp4')
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-loop','1','-framerate','30','-i',str(png),'-i',item['wav'],'-t',str(frames/30),'-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-af','apad','-movflags','+faststart',str(mp4)],check=True)
    item['card_mp4']=str(mp4);item['timeline_frames']=frames
    print(item['id'],frames,'frames',flush=True)
(OUT/'cards_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
