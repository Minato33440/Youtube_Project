"""Validate reusable performance data and actual Cubism-rendered media."""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent
V3 = ROOT.parent / 'voice_sync_v3'
CHANNELS = {'ParamMouthOpenY': 'mouth_open_y', 'ParamMouthForm': 'mouth_form',
            'ParamEyeLOpen': 'eye_l_open', 'ParamEyeROpen': 'eye_r_open',
            'ParamBreath': 'breath', 'ParamAngleZ': 'angle_z'}
VIDEOS = ['Risa_stage_blink.mp4', 'Risa_stage_breath.mp4', 'Risa_performance_closeup.mp4',
          'Risa_performance_comparison.mp4', 'Risa_narration_composite.mp4']

def pcm(path):
    return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar','44100','-f','s16le','-']),dtype='<i2').astype(float)

def read_csv(path):
    with path.open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def main():
    rows=read_csv(ROOT/'performance_curve.csv');old=read_csv(V3/'mouth_curve.csv')
    assert len(rows)==len(old)==478
    assert all(a[k]==b[k] for a,b in zip(rows,old) for k in ['mouth_open_y','mouth_form','time_s'])
    motion=json.loads((ROOT/'performance.motion3.json').read_text(encoding='utf-8'))
    assert motion['Meta']['CurveCount']==6 and len(motion['Curves'])==6
    assert {c['Id'] for c in motion['Curves']}==set(CHANNELS)
    for curve in motion['Curves']:
        seg=curve['Segments']; val=np.array([seg[1],*seg[4::3]]);times=np.array([seg[0],*seg[3::3]])
        ref=np.array([float(r[CHANNELS[curve['Id']]]) for r in rows])
        assert len(val)==478 and np.all(np.isfinite(val))
        assert np.allclose(val,ref,atol=1e-6,rtol=0)
        assert np.allclose(times,np.arange(478)/30,atol=1e-6,rtol=0)
    ranges={k:[min(float(r[k]) for r in rows),max(float(r[k]) for r in rows)] for k in CHANNELS.values()}
    for k in ['eye_l_open','eye_r_open','breath']:
        assert 0<=ranges[k][0]<=ranges[k][1]<=1
    assert -6<=ranges['angle_z'][0]<=ranges['angle_z'][1]<=6
    assert all(float(rows[i][k])==v for i in [0,-1] for k,v in [('eye_l_open',1),('eye_r_open',1),('angle_z',0),('breath',0)])
    blink_groups=[]
    for i,r in enumerate(rows):
        if float(r['eye_l_open'])==0 and float(r['eye_r_open'])==0:
            if not blink_groups or i>blink_groups[-1][-1]+1: blink_groups.append([])
            blink_groups[-1].append(i)
    assert len(blink_groups)==4 and all(b[0]-a[0]>=66 for a,b in zip(blink_groups,blink_groups[1:]))
    report={'mouth_channels_verbatim_v3':True,'motion6_channels_match_csv':True,'ranges':ranges,
            'simultaneously_closed_blink_frames':blink_groups,'videos':{},'render':{}}
    refaudio=pcm(ROOT/'audio_mono_44100_pcm16.wav')
    assert np.array_equal(refaudio,pcm(Path('C:/Users/Setona/Desktop/Voicd-Sample.mp4')))
    for name in VIDEOS:
        p=ROOT/name;info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(p)]))
        v=next(s for s in info['streams'] if s['codec_type']=='video');a=next(s for s in info['streams'] if s['codec_type']=='audio')
        assert v['nb_frames']=='478' and v['r_frame_rate']=='30/1' and (v['width'],v['height'])==(1280,720)
        assert abs(float(v['duration'])-478/30)<.001 and abs(float(v['start_time'])-float(a['start_time']))<.001
        dec=subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],capture_output=True)
        assert dec.returncode==0 and not dec.stderr
        sample=pcm(p);n=min(len(sample),len(refaudio));corr=float(np.corrcoef(refaudio[:n],sample[:n])[0,1]);assert corr>.99
        report['videos'][name]={'frames':478,'fps':30,'duration_s':float(v['duration']),'decode_pass':True,'zero_offset_audio_correlation':corr,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    base=np.array(Image.open(V3/'frames/00000.png'))
    # Eroded solid silhouette excludes expected contour movement and hair gaps.
    # Any new transparency well inside it signals a potential seam/hole.
    inner=np.array(Image.fromarray(base[:,:,3]).filter(ImageFilter.MinFilter(21)))==255
    max_holes=0;max_non_eye=0;changes={stage:0 for stage in ['blink','breath','all']}
    prior_paths=sorted((V3/'frames').glob('*.png'))
    for stage in ['blink','breath','all']:
        folder=ROOT/('frames' if stage=='all' else f'frames_{stage}')
        paths=sorted(folder.glob('*.png'));assert len(paths)==478
        for i,path in enumerate(paths):
            arr=np.array(Image.open(path));prior=np.array(Image.open(prior_paths[i]))
            assert arr.shape==(1024,768,4) and arr[0,0,3]==0
            if stage=='all':
                max_holes=max(max_holes,int(np.count_nonzero(inner & (arr[:,:,3]<250))))
                if i in [0,477]:assert np.array_equal(arr,prior)
            diff=np.any(arr!=prior,axis=2);changes[stage]=max(changes[stage],int(diff.sum()))
            if stage=='blink':
                diff[125:180,315:450]=False
                max_non_eye=max(max_non_eye,int(diff.sum()))
    assert max_non_eye==0, f'Blink changed non-eye pixels: {max_non_eye}'
    assert max_holes==0, f'Potential interior transparency: {max_holes}'
    assert all(v>100 for v in changes.values())
    report['render']={'three_stages_478_each':True,'blink_changes_only_eye_roi':True,'eye_roi_xyxy':[315,125,450,180],
                      'max_new_interior_transparency_pixels':max_holes,'max_changed_pixels_vs_v3':changes,
                      'endpoints_pixel_identical_to_v3':True,
                      'scope':'Hole heuristic supplements visual calibration; it is not proof for every parameter combination.'}
    (ROOT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
