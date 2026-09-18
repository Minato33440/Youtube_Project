"""Check the exported sample, unchanged timing, source audio, and visible motion."""
import csv, json, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from build_sample import OUT, SOURCE, MEDIA, EXPORT, COUNT, FPS, CHANNELS, write_json, sha

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)]))['streams']

def decode_frames(path, indices):
    expr='+'.join(f'eq(n\\,{n})' for n in indices)
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf',f"select='{expr}'",'-fps_mode','passthrough','-pix_fmt','rgb24','-f','rawvideo','-'])
    arr=np.frombuffer(raw,np.uint8).reshape(len(indices),1080,1920,3)
    return dict(zip(indices,arr))

def mono(path):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar','16000','-f','f32le','-'])
    return np.frombuffer(raw,'<f4').astype(np.float64)

def main():
    before=list(csv.DictReader((SOURCE/'performance_curve.csv').open(encoding='utf-8-sig')))
    after=list(csv.DictReader((OUT/'performance_curve.csv').open(encoding='utf-8-sig')))
    assert len(before)==len(after)==COUNT
    for b,a in zip(before,after):
        for key in ['frame','time_s','eye_l_open','eye_r_open','breath','phoneme','mora']:
            assert a[key]==b[key],key
        assert abs(float(a['mouth_open_y'])-float(b['mouth_open_y'])*1.2)<.000001
        assert abs(float(a['angle_z'])-float(b['angle_z'])*2)<.000001
        form=float(b['mouth_form'])
        assert abs(float(a['mouth_form'])-form*(.55 if form<0 else 1))<.000001
    streams=probe(EXPORT); v=next(s for s in streams if s['codec_type']=='video'); audio=next(s for s in streams if s['codec_type']=='audio')
    assert (v['width'],v['height'],int(v['nb_frames']),v['r_frame_rate'])==(1920,1080,COUNT,'30/1')
    assert float(v['start_time'])==float(audio['start_time'])==0
    assert abs(float(v['duration'])-float(audio['duration']))<1/FPS
    decoded=subprocess.run(['ffmpeg','-v','error','-i',str(EXPORT),'-f','null','-'],capture_output=True,text=True)
    assert decoded.returncode==0 and not decoded.stderr,decoded.stderr
    x,y=mono(MEDIA/'audio/N01.wav'),mono(EXPORT)
    n=min(len(x),len(y)); x=x[:n]; y=y[:n]
    correlation=float(np.corrcoef(x,y)[0,1])
    fft_size=1<<(2*n-1).bit_length()
    cross=np.fft.irfft(np.fft.rfft(y,fft_size)*np.conj(np.fft.rfft(x,fft_size)),fft_size)
    lags=np.arange(-1600,1601)
    peak_lag=int(lags[np.argmax(cross[lags%fft_size])])
    assert correlation>.99 and abs(peak_lag)<=1,(correlation,peak_lag)
    assert sha(OUT/'N01.wav')==sha(MEDIA/'audio/N01.wav')
    picked={0,COUNT-1,80,249,411}
    for key,fun in [('mouth_open_y',max),('mouth_form',min),('angle_z',min),('angle_z',max)]:
        picked.add(int(fun(after,key=lambda r:float(r[key]))['frame']))
    indices=sorted(picked)
    frames=decode_frames(EXPORT,indices)
    backgrounds=decode_frames(MEDIA/'backgrounds/N01.mp4',indices)
    means=[]; sources=[]; masks=[]; background_errors=[]
    sheet=Image.new('RGB',(430*3,390*3),'#dddddd'); draw=ImageDraw.Draw(sheet)
    for j,n in enumerate(indices):
        src=np.array(Image.open(OUT/f'frames/{n:05d}.png').resize((576,450),Image.Resampling.LANCZOS))
        mask=src[:,:,3]>=250
        roi=frames[n][70:520,1180:1756,:]
        means.append(float(np.abs(roi[mask].astype(float)-src[:,:,:3][mask]).mean()))
        sources.append(roi); masks.append(mask)
        # All cards and captions are below the overlay; inspect this region independently.
        background_errors.append(float(np.abs(frames[n][545:,:,:].astype(float)-backgrounds[n][545:,:,:].astype(float)).mean()))
        face=Image.fromarray(frames[n]).crop((1270,70,1670,420)).resize((400,350))
        xx,yy=j%3*430,j//3*390; sheet.paste(face,(xx,yy+35))
        r=after[n]
        draw.text((xx+5,yy+3),f'{n/FPS:.2f}s  Open {float(r["mouth_open_y"]):.3f}  Form {float(r["mouth_form"]):.3f}',fill='black')
        draw.text((xx+5,yy+18),f'AngleZ {float(r["angle_z"]):.3f}',fill='black')
    differences=[]
    for a,b,ma,mb in zip(sources,sources[1:],masks,masks[1:]):
        common=ma&mb
        differences.append(float(np.abs(a[common].astype(float)-b[common].astype(float)).mean()))
    assert max(means)<10,means
    assert np.mean(differences)>.1,differences
    assert max(background_errors)<2,background_errors
    sheet.save(OUT/'face_neck_review.jpg',quality=95)
    opened=max(indices,key=lambda n:float(after[n]['mouth_open_y']))
    Image.fromarray(frames[opened]).save(OUT/'layout_preview.jpg',quality=95)
    report={'passed':True,'video':{'width':1920,'height':1080,'frames':COUNT,'fps':30,'duration_s':float(v['duration']),'full_decode_passed':True},
            'audio':{'source_wav_identical':True,'zero_offset_correlation':correlation,'peak_lag_ms':peak_lag/16,'video_audio_start':0},
            'requested_multipliers_verified':True,'blink_breath_phoneme_timing_unchanged':True,
            'ranges':{k:[min(float(r[k]) for r in after),max(float(r[k]) for r in after)] for k in CHANNELS.values()},
            'export_model_mean_pixel_error_by_sample':means,'model_only_temporal_mean_pixel_difference':differences,
            'cards_subtitles_mean_pixel_error_by_sample':background_errors,
            'sampled_frame_indices':indices,'human_audiovisual_acceptance':'pending',
            'scope':'All frames decoded, all curves checked; appearance comparisons use selected frames and do not replace listening/viewing.'}
    write_json(OUT/'verification.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
