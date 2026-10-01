"""Read-only inventory of this project's CAFF CMO3 files. Never writes CMO3.

The archive reader is verified against Cubism 5.3.04 files in this audit;
it is an internal-format inspection helper, not a supported Cubism SDK.
"""
from pathlib import Path
import hashlib
import io
import json
import struct
import zlib
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent.parent
LIVE = MODEL.parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

class Cmo:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        b = self.data
        assert b[:4] == b'CAFF', self.path
        key = struct.unpack_from('>I', b, 14)[0]
        self.ck = key & 255
        self.table = bytes(i ^ self.ck for i in range(256))
        n = struct.unpack_from('>I', b, 54)[0] ^ key
        assert 0 < n < 10000
        p = 58
        self.entries = {}
        for _ in range(n):
            strings = []
            for j in range(2):
                size = b[p] ^ self.ck
                p += 1
                strings.append(b[p:p+size].translate(self.table).decode('utf-8'))
                p += size
            zero, offset, size = [struct.unpack_from('>I', b, p+j)[0] ^ key for j in (0,4,8)]
            p += 22
            assert 0 <= offset <= offset+size <= len(b)
            assert strings[0] not in self.entries
            self.entries[strings[0]] = (offset, size)
        assert min(x[0] for x in self.entries.values()) == p
        payload = self.entry('main.xml')
        assert payload[:4] == b'PK\x03\x04'
        nl,xl = struct.unpack_from('<HH', payload,26)
        self.xml = zlib.decompress(payload[30+nl+xl:],-15)
        self.root = ET.fromstring(self.xml)
        self.refs = {x.get('xs.id'):x for x in self.root.iter() if x.get('xs.id')}
        self.main = self.root.find('main/CModelSource')
        self.params = {}
        self.param_by_guid = {}
        for x in self.objects('CParameterSource'):
            d = dict(id=self.val(x,'id'), name=self.val(x,'name'),
                     min=self.val(x,'minValue'), max=self.val(x,'maxValue'),
                     default=self.val(x,'defaultValue'))
            self.params[d['id']] = d
            self.param_by_guid[self.val(x,'guid')] = d['id']
        self.images = {self.val(x,'guid'):x for x in self.objects('CModelImage')}
        self.deformer_names = {self.val(x.find('ACDeformerSource'),'guid'):self.name(x)
            for tag in ('CWarpDeformerSource','CRotationDeformerSource') for x in self.objects(tag)}

    def entry(self,name):
        offset,size = self.entries[name]
        return self.data[offset:offset+size].translate(self.table)

    def res(self,x):
        if x is None: return None
        return self.refs[x.get('xs.ref')] if x.get('xs.ref') else x

    def field(self,x,name):
        x=self.res(x)
        if x is None: return None
        return self.res(next((v for v in x if v.get('xs.n')==name),None))

    def val(self,x,name=None):
        x=self.field(x,name) if name is not None else self.res(x)
        if x is None: return None
        for a in ('uuid','idstr','v','path'):
            if x.get(a) is not None:return x.get(a)
        t=x.text or ''
        if x.tag in ('i','l','f','d'):return float(t) if x.tag in ('f','d') else int(t)
        if x.tag=='b': return t=='true'
        return t.strip()

    def objects(self,tag):
        return [x for x in self.root.iter(tag) if not x.get('xs.ref') and len(x)]

    def name(self,x):
        a=next(x.iter('ACParameterControllableSource'),None)
        return self.val(a,'localName')

    def binding(self,b):
        b=self.res(b)
        return {'parameter':self.param_by_guid.get(self.val(b,'parameterGuid'),self.val(b,'parameterGuid')),
                'keys':[self.val(k) for k in self.field(b,'keys')]}

    def forms(self,x):
        forms=self.field(x,'keyforms')
        if forms is None:return []
        out=[]
        for f in forms:
            f=self.res(f)
            d={'guid':self.val(next(f.iter('CFormGuid'),None))}
            d['form_attributes']={k:v for k,v in f.attrib.items() if not k.startswith('xs.')}
            for q in f.iter():
                n=q.get('xs.n')
                if q.tag in ('float-array','double-array'):
                    d[n+'_sha256']=sha((q.text or '').strip().encode())
                    nums=np.array((q.text or '').split(),dtype=float)
                    if n in ('positions','points','point') and len(nums)%2==0:
                        p=nums.reshape(-1,2)
                        d[n+'_count']=len(p)
                        d[n+'_bbox']=[*p.min(0),*p.max(0)]
                elif q.tag in ('f','i','b') and n:
                    d[n]=self.val(q)
            out.append(d)
        return out

    def image(self,mi):
        resource=self.field(mi,'_filteredImage')
        if resource is None:return None
        file=next(resource.iter('file'),None)
        return Image.open(io.BytesIO(self.entry(file.get('path')))).convert('RGBA')

    def summarize(self):
        out={'path':str(self.path),'file_sha256':sha(self.data),'xml_sha256':sha(self.xml),
             'parameters':self.params,'meshes':[],'deformers':[],'physics':[], 'layered_sources':[]}
        for tag in ('CArtMeshSource','CWarpDeformerSource','CRotationDeformerSource'):
            for x in self.objects(tag):
                ctl=next(x.iter('ACParameterControllableSource'))
                src=x.find('ACDrawableSource' if tag=='CArtMeshSource' else 'ACDeformerSource')
                g=self.field(ctl,'keyformGridSource')
                d={'name':self.name(x),'id':self.val(src,'id'),'type':tag,
                   'parent':self.deformer_names.get(self.val(src,'targetDeformerGuid'),'ROOT'),
                   'visible':self.val(ctl,'isVisible'),
                   'bindings':[self.binding(k) for k in self.field(g,'keyformBindings')],
                   'forms':self.forms(x),'grid':[]}
                for kg in self.field(g,'keyformsOnGrid'):
                    kg=self.res(kg)
                    ks=[]
                    for kp in kg.iter('KeyOnParameter'):
                        bind=self.binding(self.field(kp,'binding'))
                        ind=self.val(kp,'keyIndex')
                        ks.append([bind['parameter'],bind['keys'][ind]])
                    d['grid'].append({'keys':ks,'form':self.val(kg,'keyformGuid')})
                if tag=='CArtMeshSource':
                    ep=next(x.iter('GEditableMesh2'),None)
                    if ep is not None:
                        p=self.field(ep,'point'); d['vertices']=int(p.get('count'))//2
                        d['editable_mesh_sha256']=sha(ET.tostring(ep))
                    ind=self.field(x,'indices'); d['triangles']=int(ind.get('count'))//3
                    d['clips']=[self.val(k) for k in self.field(src,'clipGuidList')]
                    ext=self.res(next(x.iter('CTextureInputExtension'),None))
                    inp=self.field(ext,'currentTextureInputData')
                    mi=self.images.get(self.val(inp,'_modelImageGuid'))
                    if mi is not None:
                        im=self.image(mi)
                        d['image']={'name':self.val(mi,'name'),'size':list(im.size),
                                    'rgba_sha256':sha(im.tobytes()),
                                    'placement':self.field(mi,'_materialLocalToCanvasTransform').attrib}
                    out['meshes'].append(d)
                else:
                    d['cols']=self.val(x,'col');d['rows']=self.val(x,'row')
                    out['deformers'].append(d)
        for x in self.objects('CPhysicsSettingsSource'):
            d={'name':self.val(x,'name'),'inputs':[],'outputs':[],'vertices':[]}
            for tag,fld,pname in [('CPhysicsInput','inputs','source'),('CPhysicsOutput','outputs','destination'),('CPhysicsVertex','vertices',None)]:
                for q in x.iter(tag):
                    e={v.get('xs.n'):self.val(v) for v in q if v.tag in ('f','i','b','CPhysicsSourceType')}
                    if pname:e['parameter']=self.param_by_guid.get(self.val(q,pname))
                    d[fld].append(e)
            out['physics'].append(d)
        for x in self.objects('CLayeredImage'):
            out['layered_sources'].append({q.get('xs.n'):self.val(q) for q in x if q.tag in ('s','file')})
        tex=self.field(self.main,'textureManager')
        out['atlas_count']=len(self.field(tex,'_textureAtlases'))
        out['texture_manager_xml']=ET.tostring(tex,encoding='unicode')
        return out

def latest_comparison(cmo):
    mf=MODEL/'art/psd_front/manifest.json'
    layers=json.loads(mf.read_text(encoding='utf-8'))['layers']
    out=[]
    for l in layers:
        p=(mf.parent/l['path']).resolve()
        src=Image.open(p).convert('RGBA')
        ims=[x for x in cmo.images.values() if cmo.val(x,'name')==l['name']]
        row={'name':l['name'],'source':str(p),'current_sha256':sha(p.read_bytes()),
             'manifest_sha256':l['sha256'],'manifest_current':sha(p.read_bytes())==l['sha256'],
             'size':list(src.size),'embedded_matches':[]}
        for mi in ims:
            im=cmo.image(mi)
            v={'size':list(im.size),'rgba_equal':False,'visible_equal':False}
            if im.size==src.size:
                a,b=np.array(im),np.array(src)
                v['rgba_equal']=bool(np.array_equal(a,b))
                alphaeq=bool(np.array_equal(a[:,:,3],b[:,:,3]))
                v['alpha_equal']=alphaeq
                mask=(a[:,:,3]>0)|(b[:,:,3]>0)
                v['visible_equal']=alphaeq and bool(np.array_equal(a[:,:,:3][mask],b[:,:,:3][mask]))
                diff=np.abs(a.astype(int)-b.astype(int))
                v['max_channel_delta']=int(diff.max())
                v['differing_visible_pixels']=int(np.count_nonzero(np.any(diff[:,:,:3]>0,axis=2)&mask))
            row['embedded_matches'].append(v)
        out.append(row)
    return out

def used_asset_comparison(cmo):
    """Compare textures actually selected by ArtMeshes, including mouth additions."""
    mf=MODEL/'art/psd_front/manifest.json'
    layers=json.loads(mf.read_text(encoding='utf-8'))['layers']
    sources={l['name']:(mf.parent/l['path']).resolve() for l in layers}
    out=[]
    for mesh in cmo.summarize()['meshes']:
        name=mesh['name']
        path=sources.get(name,MODEL/'art/expression_rig/parts'/(name+'.png'))
        im=Image.open(path).convert('RGBA')
        out.append({'mesh':name,'artmesh_id':mesh['id'],'source':str(path),
                    'png_sha256':sha(path.read_bytes()),'size':list(im.size),
                    'rgba_sha256':sha(im.tobytes()),
                    'active_embedded_rgba_equal':list(im.size)==mesh['image']['size'] and sha(im.tobytes())==mesh['image']['rgba_sha256']})
    return out

def run():
    work=LIVE/'Traning/Lesson_PSD_Import/work'
    paths={
        'candidate':work/'Ren_deformer.cmo3',
        'candidate0':work/'Ren_deformer0.cmo3',
        'lesson09_pre_atlas':work/'Ren_training_L09_deformer01.cmo3',
        'accepted_reference':LIVE/'Traning/Lesson_PSD_Import/reference/Ren_front_completed_reference.cmo3',
        'head_neck_hair_working':MODEL/'model/head_neck_hair/Ren_front.cmo3',
        'basic_expression':MODEL/'model/basic_expression/Ren_front.cmo3',
    }
    summaries={}
    archives={}
    for label,path in paths.items():
        c=Cmo(path)
        archives[label]=c
        s=c.summarize()
        (HERE/(label+'_inventory.json')).write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
        summaries[label]={'sha256':s['file_sha256'],'meshes':len(s['meshes']),
            'deformers':len(s['deformers']),'parameters':len(s['parameters']),
            'physics_groups':len(s['physics'])}
        if label=='candidate':
            (HERE/'latest_asset_comparison.json').write_text(json.dumps(latest_comparison(c),ensure_ascii=False,indent=2),encoding='utf-8')
            (HERE/'used_asset_comparison.json').write_text(json.dumps(used_asset_comparison(c),ensure_ascii=False,indent=2),encoding='utf-8')
    comparisons={}
    for label in ('candidate0','lesson09_pre_atlas'):
        a,b=archives['candidate'],archives[label]
        comparisons[label]={'main_xml_equal':a.xml==b.xml,'archive_entry_names_equal':set(a.entries)==set(b.entries),
             'non_xml_payloads_equal':all(k in b.entries and a.entry(k)==b.entry(k) for k in a.entries if k!='main.xml')}
    (HERE/'candidate_equivalence.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
    a=archives['candidate']
    s=a.summarize()
    usage={k:[] for k in s['parameters']}
    for item in s['meshes']+s['deformers']:
        for binding in item['bindings']:
            usage[binding['parameter']].append(item['name'])
    checks={
        'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Read-only CMO3 structure and active embedded textures; GUI observations are in README.',
        'input_files_unchanged_during_read':{k:sha(c.path.read_bytes())==sha(c.data) for k,c in archives.items()},
        'audit_copy_matches_candidate':sha((HERE/'Ren_deformer_audit.cmo3').read_bytes())==sha(a.data),
        'parameter_bound_objects':usage,
        'parameter_ids_without_keyform_bindings':[k for k,v in usage.items() if not v],
        'used_png_count':len(used_asset_comparison(a)),
        'all_used_pngs_rgba_equal':all(x['active_embedded_rgba_equal'] for x in used_asset_comparison(a)),
        'training_psd_equals_current_psd':sha((work/'Ren_front_training_L01.psd').read_bytes())==sha((MODEL/'art/psd_front/Ren_front.psd').read_bytes()),
        'atlas_count':s['atlas_count'],
        'missing_linked_source_paths':[x['psdFile'] for x in s['layered_sources'] if not Path(x['psdFile']).exists()],
        'gui_export_or_runtime_retest':False,
    }
    assert all(checks['input_files_unchanged_during_read'].values())
    assert checks['all_used_pngs_rgba_equal']
    assert checks['audit_copy_matches_candidate']
    (HERE/'verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    (HERE/'summary.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summaries,ensure_ascii=False,indent=2))

if __name__=='__main__':run()
