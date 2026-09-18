"""Verify local breath motion without treating changed pixels as naturalness."""
import json
import numpy as np
from PIL import Image,ImageFilter
from build_preview import OUT,write

def match(a,b,box):
    x,y,w,h=box
    ref=a[y:y+h,x:x+w,:3].astype(float)
    best=(float('inf'),0,0)
    for dy in range(-25,26):
        for dx in range(-20,21):
            target=b[y+dy:y+dy+h,x+dx:x+dx+w,:3].astype(float)
            error=float(np.mean((ref-target)**2))
            if error<best[0]:best=(error,dx,dy)
    return dict(dx_px=best[1],dy_px=best[2],mse=best[0])

def shoulder(a,x0,x1):
    return np.array([np.flatnonzero(a[:,x,3]>245)[0] for x in range(x0,x1)])

def fabric_width(a):
    widths=[]
    for y in range(600,651):
        row=a[y,200:560,:3]
        # Cream fabric contrasted with dark jacket, measured at chest height.
        xs=np.flatnonzero(np.all(row>150,axis=1))
        widths.append(int(xs[-1]-xs[0]+1))
    return float(np.median(widths))

def main():
    a=np.array(Image.open(OUT/'calibration/after_0.png'))
    b=np.array(Image.open(OUT/'calibration/after_3.png'))
    # Only the top edge is anchored. Interior collar folds now intentionally move.
    collar=match(a,b,(350,350,70,30))
    chest=match(a,b,(340,660,80,55))
    previous=np.array(Image.open(OUT/'calibration/before_3.png'))
    added_delta=np.abs(previous.astype(float)-b.astype(float))
    upper=match(previous,b,(350,410,70,60))
    lower=match(previous,b,(330,750,100,55))
    original=np.array(Image.open(OUT.parent/'chest_breath_v7/calibration/after_3.png'))
    original_upper=match(previous,original,(350,410,70,60))
    original_lower=match(previous,original,(330,750,100,55))
    pair_delta=np.max(np.abs(original.astype(float)-b.astype(float)),axis=2)
    outside=pair_delta.copy()
    outside[380:510,280:480]=0
    assert outside.max()<=1,float(outside.max())
    left_fold=match(previous,b,(324,441,40,48))
    right_fold=match(previous,b,(404,435,40,48))
    original_left=match(previous,original,(324,441,40,48))
    original_right=match(previous,original,(404,435,40,48))
    upper_detail=match(original,b,(345,395,50,30))
    report={'scope':'ParamBreath 0 to 1, fixed head at 1080px preview scale; not actual narration amplitude.',
            'top_collar':collar,'chest_center':chest,
            'added_upper_fold_motion_vs_v3_at_breath_1':upper,
            'added_lower_fold_motion_vs_v3_at_breath_1':lower,
            'original_v7_upper_fold_motion_vs_v3':original_upper,
            'original_v7_lower_fold_motion_vs_v3':original_lower,
            'original_v7_left_fold':original_left,
            'original_v7_right_fold':original_right,
            'left_internal_fold_vs_v3':left_fold,
            'right_internal_fold_vs_v3':right_fold,
            'upper_crease_added_motion_vs_v7':upper_detail,
            'upper_crease_mean_rgb_change_vs_v7':float(np.abs(original.astype(float)-b.astype(float))[390:435,335:410,:3].mean()),
            'chest_and_abdomen_max_difference_v7_v8':float(pair_delta[510:].max()),
            'outside_upper_knit_max_difference_v7_v8':float(outside.max()),
            'abdomen_max_difference_v7_v8':float(pair_delta[700:].max()),
            'silhouette_alpha_max_difference_v7_v8':int(np.abs(original[:,:,3].astype(int)-b[:,:,3].astype(int)).max()),
            'silhouette_mask_changed_pixels':{str(t):int(np.sum((original[:,:,3]>t)!=(b[:,:,3]>t))) for t in [1,127,240]},
            'upper_fold_mean_rgb_change_vs_v3':float(added_delta[400:510,320:450,:3].mean()),
            'lower_fold_mean_rgb_change_vs_v3':float(added_delta[730:815,280:500,:3].mean()),
            'belt_and_lower_body_max_difference_vs_v3':int(added_delta[850:1000,200:570].max()),
            'left_shoulder_rise_px':float(np.median(shoulder(a,145,160)-shoulder(b,145,160))),
            'right_shoulder_rise_px':float(np.median(shoulder(a,605,615)-shoulder(b,605,615))),
            'cream_chest_width_neutral_px':fabric_width(a),
            'cream_chest_width_inhale_px':fabric_width(b)}
    assert collar['dx_px']==collar['dy_px']==0,report
    assert abs(upper['dy_px'])<=1 and lower['dy_px']>0,report
    assert left_fold['dx_px']>0 and right_fold['dx_px']<0,report
    assert abs(left_fold['dy_px'])<=1 and abs(right_fold['dy_px'])<=1,report
    assert upper_detail['dx_px']>=3 and abs(upper_detail['dy_px'])<=1,report
    assert report['upper_crease_mean_rgb_change_vs_v7']>1,report
    assert report['chest_and_abdomen_max_difference_v7_v8']==0,report
    assert report['abdomen_max_difference_v7_v8']==0,report
    # Near-opaque interior interpolation can differ by one alpha value.
    # Test the visible silhouette separately at multiple thresholds.
    assert report['silhouette_alpha_max_difference_v7_v8']<=1,report
    assert max(report['silhouette_mask_changed_pixels'].values())==0,report
    assert report['upper_fold_mean_rgb_change_vs_v3']>.3,report
    assert report['lower_fold_mean_rgb_change_vs_v3']>.3,report
    assert report['belt_and_lower_body_max_difference_vs_v3']==0,report
    assert abs(chest['dy_px'])<=1,report
    assert 8<=report['left_shoulder_rise_px']<=22 and 8<=report['right_shoulder_rise_px']<=22,report
    assert report['cream_chest_width_inhale_px']>report['cream_chest_width_neutral_px']+5,report
    # Check for new holes well inside the neutral silhouette. Outside edges
    # are allowed to move; opaque interior should remain filled.
    mask=np.array(Image.fromarray(a[:,:,3]).filter(ImageFilter.MinFilter(31)))>250
    holes=[]
    for i in range(6):
        im=np.array(Image.open(OUT/f'calibration/after_{i}.png'))
        # Face pose changes in the final two cases; inspect collar/body only.
        holes.append(int(np.sum(mask[350:]&(im[350:,:,3]<240))))
    report['new_body_interior_transparency_pixels']=holes
    assert max(holes)==0,report
    report['passed']=True
    write(OUT/'local_motion_verification.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
