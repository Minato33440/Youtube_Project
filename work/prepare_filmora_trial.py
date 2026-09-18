"""Prepare the observed working prototype import container; native Save As required.

Run after `python work/build_risa_filmora.py --prototype`.
This never overwrites the final, natively saved Risa_Layered_Trial_20260915.wfp.
The exact metadata field causing minimal-container rejection remains unresolved.
"""
import json,zipfile
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'Politics_Economics/2026-09-09_fiscal_policy/filmora'
def main():
    out=P/'Risa_prototype_native_prepared.wfp'
    with zipfile.ZipFile(P/'fiscal_policy_narration_v2.wfp') as old, zipfile.ZipFile(P/'Risa_layered_prototype.wfp') as new:
        oi=json.loads(old.read('ProjectFolder/project_info.json'))['timeline_mediaId']
        ni=json.loads(new.read('ProjectFolder/project_info.json'))['timeline_mediaId']
        files={i.filename:old.read(i) for i in old.infolist()}
        for n in new.namelist():
            if n=='ProjectFolder/project_info.json' or '/Anon/' in n:continue
            files[n.replace(ni,oi)]=new.read(n).replace(ni.encode(),oi.encode())
    with zipfile.ZipFile(out,'w') as dest:
        for n,b in files.items():dest.writestr(n,b)
    print(out)
    print('Open in Filmora, Save As to a new name, reopen, export and verify before delivery.')
if __name__=='__main__':main()
