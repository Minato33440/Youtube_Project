import csv,json
import numpy as np
from verify_risa_final import frame,original,final,P,OUT
rows=list(csv.DictReader((P/'code_edit/sample_v1/timeline.csv').open(encoding='utf-8-sig')))
checks=[]
for r in rows:
    if r['type']!='narration':continue
    start=round(float(r['timeline_in'])*30);end=start+int(r['planned_frames'])
    for f,wanted in ((start-1,False),(start,True),(start+1,True),(end-1,True),(end,False)):
        if f>=29733:continue
        # Seek just before the target presentation timestamp. Decimal seconds
        # may otherwise round above the frame and select its successor.
        t=max(0,f/30-0.001)
        a=np.asarray(frame(original,t).convert('RGB'),dtype=np.float32)[99:519,1275:1659]
        b=np.asarray(frame(final,t).convert('RGB'),dtype=np.float32)[99:519,1275:1659]
        count=int((np.max(np.abs(a-b),axis=2)>30).sum());present=count>5000
        checks.append(dict(id=r['id'],frame=f,time=t,expected_model=wanted,measured_model=present,changed_pixels=count,passed=present==wanted))
report=dict(passed=all(c['passed'] for c in checks),checks=checks)
(OUT/'boundary_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
assert report['passed']
