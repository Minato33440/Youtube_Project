"""Repair only video time maps in the saved trial, preserving the original file."""
import json,zipfile
from pathlib import Path
from build_risa_filmora import normal_speed,dumps
P=Path(__file__).resolve().parents[1]/'Politics_Economics/2026-09-09_fiscal_policy/filmora'
source=P/'Risa_Layered_Trial_20260915.wfp'
output=P/'Risa_Trial_Motion_Repair_Input.wfp'
with zipfile.ZipFile(source) as z:
    entries={n:z.read(n) for n in z.namelist()}
    name=next(n for n in entries if n.endswith('/timeline.wesproj'))
    d=json.loads(entries[name])
    count=0
    for timeline in d['timelineInfos']:
        for track in timeline['trackInfos']:
            if track['trackType']!=1:continue
            for clip in track['clipList']:
                duration=(clip['outPoint']-clip['inPoint'])/1e7
                assert duration>0 and clip['inPoint']==0
                clip['speed']=normal_speed(duration);count+=1
    entries[name]=dumps(d).encode()
with zipfile.ZipFile(output,'w') as z:
    for n,b in entries.items():z.writestr(n,b)
print(f'Repaired {count} video time maps: {output}')
