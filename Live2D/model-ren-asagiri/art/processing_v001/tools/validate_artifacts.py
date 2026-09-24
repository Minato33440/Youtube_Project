"""Check source preservation, layer bounds and neutral alpha reconstruction."""
from pathlib import Path
import hashlib, json
import numpy as np
from PIL import Image

out=Path(__file__).resolve().parents[1]
root=Path(__file__).resolve().parents[3]
hashes=json.loads((out/'source_hashes.json').read_text(encoding='utf-8'))
changed=[n for n,h in hashes.items() if hashlib.sha256((root/'art_assets'/n).read_bytes()).hexdigest()!=h]
report={'sourcesUnchanged':not changed,'changedSources':changed,'views':{}}
for view in ['front','back']:
    m=json.loads((out/view/'manifest.json').read_text(encoding='utf-8'))
    names=[]
    for l in m['layers']:
        im=Image.open(out/view/l['path'])
        assert im.mode=='RGBA' and im.getchannel('A').getbbox(),l['name']
        assert l['left']>=0 and l['top']>=0 and l['left']+im.width<=4000 and l['top']+im.height<=6000,l['name']
        names.append(l['name'])
    assert len(names)==len(set(names))
    src=np.array(Image.open(root/'art_assets'/f'ren-stand-pony-{view}-4000x6000.png').convert('RGBA'))
    dst=np.array(Image.open(out/view/'assembled.png').convert('RGBA'))
    delta=np.abs(dst.astype(np.int16)-src.astype(np.int16))
    visible=src[:,:,3]>0
    alpha_count=int(np.count_nonzero(delta[:,:,3]))
    report['views'][view]={'canvas':[4000,6000],'layers':len(names),'visibleLayers':sum(bool(l['visible']) for l in m['layers']),
      'alphaDifferentPixels':alpha_count,'missingSourcePixels':int(np.count_nonzero(visible&(dst[:,:,3]==0))),
      'outsideSourcePixels':int(np.count_nonzero((~visible)&(dst[:,:,3]>0))),
      'visibleRgbDifferentPixels':int(np.count_nonzero(np.any(delta[:,:,:3]>0,axis=2)&visible)),
      'visibleRgbDifferenceOver30Pixels':int(np.count_nonzero(np.any(delta[:,:,:3]>30,axis=2)&visible)),
      'note':'Skin/ear underfills may change a small number of semi-transparent boundary colors; source alpha must stay identical.'}
    assert alpha_count==0,(view,alpha_count)
assert not changed,changed
(out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
