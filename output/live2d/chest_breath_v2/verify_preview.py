"""Verify model-only MP4s, independent chest motion, and preserved speech curves."""
import csv,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from build_preview import OUT,PREVIOUS,EXPORTS,write,sha

def frames(path,indices):
    expr='+'.join(f'eq(n\\,{i})' for i in indices)
    b=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf',f"select='{expr}'",'-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','-'])
    return np.frombuffer(b,np.uint8).reshape(len(indices),1080,1080,3)

def sound(path):
    b=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar','16000','-f','f32le','-'])
    return np.frombuffer(b,'<f4').astype(float)

def main():
    assert sha(PREVIOUS/'performance_curve.csv')==sha(OUT/'performance_curve.csv')
    assert sha(PREVIOUS/'N01.wav')==sha(OUT/'N01.wav')
    curves=list(csv.DictReader((OUT/'performance_curve.csv').open(encoding='utf-8-sig')))
    main_indices=sorted(set([0,80,166,280,411,478,int(max(curves,key=lambda r:float(r['breath']))['frame'])]))
    configs=[('speaking','Risa_ModelOnly_ChestBreath_v2.mp4',479,main_indices),
             ('breath_only','Risa_ModelOnly_BreathOnly_v2.mp4',241,[0,30,60,90,120,180,240])]
    result={}
    for label,name,count,indices in configs:
        path=EXPORTS/name
        streams=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)]))['streams']
        v=next(s for s in streams if s['codec_type']=='video')
        assert v['width']==v['height']==1080 and int(v['nb_frames'])==count and v['r_frame_rate']=='30/1'
        decoded=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],capture_output=True,text=True)
        assert decoded.returncode==0 and not decoded.stderr
        sampled=frames(path,indices)
        errors=[]
        for idx,im in zip(indices,sampled):
            src=np.array(Image.open(OUT/label/f'{idx:05d}.png'))
            errors.append(float(np.abs(src.astype(float)-im.astype(float)).mean()))
        assert max(errors)<3,errors
        temporal=[float(np.abs(a[450:810,360:740].astype(float)-b[450:810,360:740].astype(float)).mean()) for a,b in zip(sampled,sampled[1:])]
        assert max(temporal)>.2,temporal
        data={'frames':count,'fps':30,'duration_s':float(v['duration']),'full_decode_passed':True,
              'reference_frame_mean_pixel_error':errors,'chest_region_temporal_mean_pixel_difference':temporal,
              'checked_frame_indices':indices}
        if label=='speaking':
            a=next(s for s in streams if s['codec_type']=='audio')
            assert abs(float(a['duration'])-float(v['duration']))<1/30
            assert float(a['start_time'])==float(v['start_time'])==0
            x,y=sound(OUT/'N01.wav'),sound(path);n=min(len(x),len(y));x=x[:n];y=y[:n]
            corr=float(np.corrcoef(x,y)[0,1]);size=1<<(2*n-1).bit_length()
            c=np.fft.irfft(np.fft.rfft(y,size)*np.conj(np.fft.rfft(x,size)),size)
            lags=np.arange(-1600,1601);lag=int(lags[np.argmax(c[lags%size])])
            assert corr>.99 and abs(lag)<=1
            data['audio']={'source_identical':True,'correlation':corr,'peak_offset_ms':lag/16}
            Image.fromarray(sampled[3]).save(OUT/'preview.jpg',quality=95)
        else:
            assert not any(s['codec_type']=='audio' for s in streams)
            # First and final frames of the two breathing cycles should match.
            data['loop_endpoint_mean_pixel_difference']=float(np.abs(sampled[0].astype(float)-sampled[-1].astype(float)).mean())
            assert data['loop_endpoint_mean_pixel_difference']<1
            panel=Image.new('RGB',(360*3,380*2),'#dddddd');d=ImageDraw.Draw(panel)
            for j,(i,im) in enumerate(zip(indices[:6],sampled[:6])):
                xx=j%3*360;yy=j//3*380
                panel.paste(Image.fromarray(im).resize((360,360)),(xx,yy+20))
                d.text((xx+5,yy+3),f'Breath only: {i/30:.1f}s',fill='black')
            panel.save(OUT/'breath_sequence_review.jpg',quality=95)
        result[label]=data
    # At identical parameters, the new chest rig preserves the entire face
    # above the raised collar (crop y < 340) in all six calibration poses.
    face_errors=[]
    for i in range(6):
        a=np.array(Image.open(OUT/f'calibration/before_{i}.png')).astype(int)
        b=np.array(Image.open(OUT/f'calibration/after_{i}.png')).astype(int)
        face_errors.append(int(np.abs(a[:340]-b[:340]).max()))
    assert max(face_errors)==0
    report={'passed':True,'previous_speech_head_blink_breath_curves_identical':True,
            'same_parameter_face_max_pixel_differences':face_errors,'outputs':result,
            'appearance_scope':'Selected frames visually reviewed; full audiovisual human acceptance pending.'}
    write(OUT/'verification.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

