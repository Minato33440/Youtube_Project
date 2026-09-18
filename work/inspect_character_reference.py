from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'movie_works/日本覚醒チャンネル/ゆっくり解説/Movie/【ゆっくり解説】グローバリズム経済の終焉と日本の真の役割.mp4'
OUT=ROOT/'Politics_Economics/2026-09-09_fiscal_policy/code_edit/character_reference'
OUT.mkdir(parents=True,exist_ok=True)
times=[3,20,60,120,240,360,480,650]
sheet=Image.new('RGB',(1280,1576),'#101c2a')
d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc',22)
for i,t in enumerate(times):
    path=OUT/f'frame_{t:03}.png'
    subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',str(SOURCE),'-map','0:v:0','-frames:v','1','-y',str(path)],check=True)
    im=Image.open(path).resize((640,360))
    x=(i%2)*640;y=(i//2)*394
    sheet.paste(im,(x,y+34));d.text((x+10,y+3),f'{t//60:02}:{t%60:02}',font=font,fill='white')
sheet.save(OUT/'reference_contact_sheet.jpg',quality=93)
print(OUT)
