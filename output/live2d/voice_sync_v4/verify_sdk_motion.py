"""Load and play the exported motion in Cubism SDK; compare six actual channels."""
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import csv
import json
from pathlib import Path
import numpy as np
import pygame
import live2d.v3 as live2d

ROOT=Path(__file__).resolve().parent
CHANNELS={'ParamMouthOpenY':'mouth_open_y','ParamMouthForm':'mouth_form','ParamEyeLOpen':'eye_l_open',
          'ParamEyeROpen':'eye_r_open','ParamBreath':'breath','ParamAngleZ':'angle_z'}

def main():
    rows=list(csv.DictReader((ROOT/'performance_curve.csv').open(encoding='utf-8-sig')))
    pygame.display.init();live2d.init()
    pygame.display.set_mode((64,64),pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN)
    live2d.glInit();model=live2d.LAppModel()
    model.LoadModelJson(str(ROOT/'model/Risa_performance.model3.json'))
    model.SetAutoBlinkEnable(False);model.SetAutoBreathEnable(False)
    ids=model.GetParamIds();indices=[ids.index(k) for k in CHANNELS]
    model.StartMotion('Performance',0,3)
    actual=[]
    for i in range(len(rows)):
        model._model.Update(0 if i==0 else 1/30)
        actual.append([model.GetParameterValue(j) for j in indices])
    expected=np.array([[float(r[v]) for v in CHANNELS.values()] for r in rows])
    errors=np.max(np.abs(np.array(actual)-expected),axis=0)
    report={'pass':bool(np.max(errors)<.002),'tolerance':.002,'motion_groups':model.GetMotionGroups(),'frames':len(rows),'max_absolute_parameter_error':dict(zip(CHANNELS,map(float,errors))),
            'auto_blink_breath':False,'fade_in_out_seconds':0,'scope':'SDK motion playback values; audio remains a separately synchronized WAV.'}
    (ROOT/'sdk_motion_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    model.DestroyRenderer();del model;live2d.dispose();pygame.quit()
    print(json.dumps(report,indent=2))
    assert np.max(errors)<.002, 'SDK motion timing/value discrepancy'

if __name__=='__main__':main()
