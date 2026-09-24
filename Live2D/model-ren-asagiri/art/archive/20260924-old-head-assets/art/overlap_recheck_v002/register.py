exec((__import__('pathlib').Path(__file__).parent/'review.py').read_text().split('rows=[];snap=')[0])
sys.path.insert(0,str(ROOT/'art/processing_v001/tools/pylib'))
import cv2
from collections import Counter
results={}
for n in names[:6]:
 old=np.array(Image.open(OLD/'source_snapshot'/(n+'.png')).convert('RGBA'));new=np.array(images[n]);candidates=[]
 for y in range(0,old.shape[0]-35,25):
  for x in range(0,old.shape[1]-35,25):
   t=old[y:y+35,x:x+35]
   if t[:,:,3].min()<250 or t[:,:,:3].std()<10:continue
   score=cv2.matchTemplate(new[:,:,:3],t[:,:,:3],cv2.TM_CCOEFF_NORMED);_,v,_,p=cv2.minMaxLoc(score)
   if v>.96:candidates.append((p[0]-x,p[1]-y,v))
 clusters=Counter((round(x/2)*2,round(y/2)*2) for x,y,v in candidates)
 if not clusters:results[n]={'error':'no match'};continue
 best,count=clusters.most_common(1)[0];group=[(x,y,v) for x,y,v in candidates if abs(x-best[0])<=2 and abs(y-best[1])<=2]
 dx,dy=[int(round(float(x))) for x in np.median(np.array(group)[:,:2],axis=0)]
 results[n]={'texture_offset_in_new':[dx,dy],'position':[pos[n][0]-dx,pos[n][1]-dy],'matched_tiles':len(group),'candidates':len(candidates),'mean_similarity':float(np.mean(np.array(group)[:,2]))}
(OUT/'registration.json').write_text(json.dumps(results,indent=2),encoding='utf8');print(json.dumps(results))
