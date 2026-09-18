from pathlib import Path
import json
import csv
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent

def main():
    aligned=json.loads((ROOT/'alignment/phonemes.json').read_text(encoding='utf8'))
    rows=list(csv.DictReader((ROOT/'mouth_curve.csv').open(encoding='utf8')))
    im=Image.new('RGB',(1600,1240),'#f7f8fa'); d=ImageDraw.Draw(im)
    font=ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc',17)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
    d.text((40,15),'口開閉曲線：青 = 音量連動 v1 / オレンジ = 発音位置と閉口を調整した v2',font=font,fill='#263445')
    for n,s in enumerate(aligned['sentences']):
        top=60+n*295
        start,end=s['concat_start_s'],s['concat_end_s']
        width=1480
        def xp(t): return 80+(t-start)/(end-start)*width
        d.text((40,top),s['text'],font=font,fill='#172334')
        y0=top+215
        for val in [0,.25,.5,.75,1]:
            y=y0-val*145;d.line((80,y,1560,y),fill='#d4dbe2');d.text((40,y-7),str(val),font=small,fill='#667788')
        for p in aligned['phonemes']:
            if p['sentence'] != s['sentence']: continue
            x1,x2=xp(p['start_s']),xp(p['end_s'])
            col='#efd9c6' if p['phoneme'] in ['a','i','u','e','o'] else '#dce5ec'
            d.rectangle((x1,top+37,x2,top+58),fill=col,outline='white')
            d.text((x1+2,top+40),p['phoneme'],font=small,fill='#263445')
        for field,col in [('v1_open','#3e86c8'),('mouth_open_y','#d46b24')]:
            points=[(xp(float(r['time_s'])),y0-float(r[field])*145) for r in rows if start<=float(r['time_s'])<=end]
            if len(points)>1:d.line(points,fill=col,width=3)
        for k in range(7):
            t=start+(end-start)*k/6;x=xp(t)
            d.text((x-18,y0+10),f'{t:.2f}s',font=small,fill='#536474')
    im.save(ROOT/'curve_review.png')

if __name__=='__main__':main()
