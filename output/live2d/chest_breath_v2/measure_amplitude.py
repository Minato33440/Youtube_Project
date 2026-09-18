"""Compare rendered v1/v2 shoulder silhouettes and chest texture movement."""
import numpy as np
from PIL import Image
from build_preview import OUT,write

def img(label,i):return np.array(Image.open(OUT/f'calibration/{label}_{i}.png'))
def shoulder(a,x0,x1):
    # This strip is outside the hair; first opaque pixel is jacket silhouette.
    return np.array([np.flatnonzero(a[:,x,3]>245)[0] for x in range(x0,x1)])
def match(a,b,box):
    x,y,w,h=box
    ref=a[y:y+h,x:x+w,:3].astype(float)
    best=(float('inf'),0,0)
    for dy in range(-50,11):
        for dx in range(-15,16):
            target=b[y+dy:y+dy+h,x+dx:x+dx+w,:3].astype(float)
            err=float(np.mean((ref-target)**2))
            if err<best[0]:best=(err,dx,dy)
    return {'dx_px':best[1],'dy_px':best[2],'matching_mse':best[0]}
report={}
for label in ['before','after']:
    a,b=img(label,0),img(label,3)
    report[label]={
      'left_shoulder_rise_px':float(np.median(shoulder(a,145,160)-shoulder(b,145,160))),
      'right_shoulder_rise_px':float(np.median(shoulder(a,605,615)-shoulder(b,605,615))),
      'jacket_brooch':match(a,b,(507,545,45,40)),
      'chest_fabric':match(a,b,(340,660,80,55))}
write(OUT/'amplitude_comparison.json',{'scope':'ParamBreath 0 to 1 on native rigs at identical 1080px preview scale. Template matching estimates local movement; silhouette median measures shoulder rise. This is not the actual narration range.','v1':report['before'],'v2':report['after']})
print(report)
assert report['after']['left_shoulder_rise_px']>=3*report['before']['left_shoulder_rise_px']
assert report['after']['right_shoulder_rise_px']>=3*report['before']['right_shoulder_rise_px']
