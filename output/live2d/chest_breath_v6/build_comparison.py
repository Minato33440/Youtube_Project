"""Synchronized A/B view: v5 vertical throat motion vs v6 internal convergence."""
import json,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from build_preview import OUT,EXPORTS,ffmpeg,write,sha

def extract(path,index):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf',f'select=eq(n\\,{index})','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
    return np.frombuffer(raw,np.uint8).reshape(1040,1920,3)

def main():
    old=EXPORTS/'Risa_ModelOnly_BreathOnly_v5.mp4'
    new=EXPORTS/'Risa_ModelOnly_BreathOnly_v6.mp4'
    target=EXPORTS/'Risa_Throat_Folds_Compare_v5_v6.mp4'
    header=Image.new('RGB',(1920,80),(24,32,44))
    draw=ImageDraw.Draw(header);font=ImageFont.load_default(size=34)
    draw.text((30,22),'A: v5 VERTICAL',font=font,fill='white')
    draw.text((990,22),'B: v6 INWARD FOLDS',font=font,fill='white')
    header.save(OUT/'comparison_header.png')
    ffmpeg(['-i',old,'-i',new,'-loop','1','-framerate','30','-i',OUT/'comparison_header.png',
            '-filter_complex','[0:v]crop=540:540:270:310,scale=960:960,setpts=PTS-STARTPTS[a];[1:v]crop=540:540:270:310,scale=960:960,setpts=PTS-STARTPTS[b];[a][b]hstack=inputs=2[body];[2:v][body]vstack=inputs=2[v]',
            '-map','[v]','-an','-frames:v','241','-r','30','-c:v','libx264','-crf','18','-preset','medium','-threads','8','-pix_fmt','yuv420p','-movflags','+faststart',target])
    streams=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(target)]))['streams']
    assert len(streams)==1
    v=streams[0]
    assert (v['width'],v['height'],int(v['nb_frames']),v['r_frame_rate'])==(1920,1040,241,'30/1')
    decoded=subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],capture_output=True,text=True)
    assert decoded.returncode==0 and not decoded.stderr
    # Decode both halves and match the corresponding exact-time PNG references.
    errors={}
    for index in [0,60,120,240]:
        image=extract(target,index)
        if index==60:Image.fromarray(image).save(OUT/'comparison_preview.jpg',quality=95)
        errors[str(index)]=[]
        for j,folder in enumerate([OUT.parent/'chest_breath_v5',OUT]):
            source=Image.open(folder/f'breath_only/{index:05d}.png').crop((270,310,810,850)).resize((960,960),Image.Resampling.LANCZOS)
            error=float(np.abs(image[80:,j*960:(j+1)*960].astype(float)-np.array(source).astype(float)).mean())
            assert error<3,error
            errors[str(index)].append(error)
    assert sha(OUT/'breath_only.motion3.json')==sha(OUT.parent/'chest_breath_v5/breath_only.motion3.json')
    write(OUT/'comparison_verification.json',{'passed':True,'output':str(target),'sha256':sha(target),
        'layout':'Left A=v5 vertical throat motion; right B=v6 inward folds. Same crop (270,310,810,850), enlarged to 960x960; same frames.',
        'breath_curve_identical':True,'frames':241,'fps':30,'full_decode_passed':True,'reference_frame_mae':errors})
    print(target)

if __name__=='__main__':main()
