"""Independent PSD read and layer-composite checks; originals remain read-only."""
from pathlib import Path
import sys,json,hashlib
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image
import numpy as np
from psd_tools import PSDImage

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

manifest=json.loads((OUT/'manifest.json').read_text())
psd=PSDImage.open(OUT/'Ren_front.psd')
assert psd.size==(4000,6000)
assert len(psd)==41
assert psd.depth==8 and int(psd.color_mode)==3
layers=list(psd)
for spec,layer in zip(manifest['layers'],layers):
    assert layer.name==spec['name']
    assert (layer.left,layer.top)==(spec['left'],spec['top'])
    assert layer.is_visible()==spec['visible']
    source=Image.open(OUT/spec['path']).convert('RGBA')
    embedded=layer.topil().convert('RGBA')
    assert source.size==embedded.size
    aa=np.asarray(source);bb=np.asarray(embedded)
    # Transparent RGB is also retained by the exporter; inspect all channels.
    assert np.array_equal(aa,bb),spec['name']
    assert sha(OUT/spec['path'])==spec['sha256']

flat=Image.open(OUT/'Ren_front.png').convert('RGBA')
pyflat=Image.open(OUT/'review/python_composite.png').convert('RGBA')
stats=[]
# Tile the full canvas to bound reader/composite memory.
for top in range(0,6000,500):
    box=(0,top,4000,min(top+500,6000))
    rendered=psd.composite(viewport=box,force=True).convert('RGBA')
    if top==500:
        pass
    actual=np.asarray(rendered).astype(np.float32)
    expected=np.asarray(flat.crop(box)).astype(np.float32)
    manual=np.asarray(pyflat.crop(box)).astype(np.float32)
    assert actual.shape==expected.shape
    bg=np.array([80,105,110],dtype=np.float32)
    def display(a):return a[:,:,:3]*(a[:,:,3:]/255)+bg*(1-a[:,:,3:]/255)
    delta=np.abs(display(actual)-display(expected))
    py_delta=np.abs(display(manual)-display(expected))
    stats.append({'top':top,'maxReaderDisplayDifference':float(delta.max()),
                  'readerPixelsDifferenceOver2':int(np.any(delta>2,axis=2).sum()),
                  'maxPythonDisplayDifference':float(py_delta.max())})
    assert not np.any(delta>2),stats[-1]
    assert not np.any(py_delta>2),stats[-1]

# Use a fresh forced layer render for visual QA (not the saved PSD thumbnail).
box=(1400,70,2600,1750)
rendered=psd.composite(viewport=box,force=True).convert('RGBA')
b=Image.new('RGBA',rendered.size,(80,105,110,255));b.alpha_composite(rendered)
b.convert('RGB').save(OUT/'review/psd_readback_head_neck.png')
report={'status':'pass','reader':'psd-tools','canvas':list(psd.size),'layerCount':len(layers),
        'RGB8bit':True,'allLayerNamesPositionsVisibilityAndRGBAExact':True,
        'all41SourcesUnchanged':True,'fullCanvasForceCompositeTiles':stats,
        'PSDsha256':sha(OUT/'Ren_front.psd'),
        'CubismImportTested':False,'deformationTested':False}
(OUT/'independent_verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({'status':'pass','layers':41,'maxIndependentDisplayDifference':max(s['maxReaderDisplayDifference'] for s in stats),'pixelsOver2':sum(s['readerPixelsDifferenceOver2'] for s in stats)}))
