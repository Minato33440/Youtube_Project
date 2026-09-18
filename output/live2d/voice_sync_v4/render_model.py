"""Render the exported Cubism model at deterministic frame times (no screen capture)."""
import argparse
import csv
import json
import os
from pathlib import Path

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import numpy as np
from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE, glFinish
from PIL import Image
import live2d.v3 as live2d

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['blink','breath','all'], default='all')
    parser.add_argument('--calibrate', action='store_true')
    args = parser.parse_args()
    print('display init', flush=True)
    pygame.display.init()
    print('live2d init', flush=True)
    live2d.init()
    size = (768, 1024)
    print('GL context', flush=True)
    pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
    pygame.display.set_mode(size, pygame.OPENGL | pygame.DOUBLEBUF | pygame.HIDDEN)
    print('glInit', flush=True)
    live2d.glInit()
    print('model construct', flush=True)
    model = live2d.LAppModel()
    print('model load', flush=True)
    model.LoadModelJson(str(ROOT / 'model/Risa_mouth_shapes.model3.json'))
    model.Resize(*size)
    model.SetAutoBlinkEnable(False)
    model.SetAutoBreathEnable(False)
    print('canvas', model.GetCanvasSizePixel(), 'parameters', model.GetParameterCount(), flush=True)
    if args.calibrate:
        cases = []
        for eye in [1, .75, .5, .25, 0]:
            cases.append(dict(mouth_open_y=.4, mouth_form=0, eye_l_open=eye, eye_r_open=eye, breath=0, angle_z=0))
        for angle in [-30, -6, 0, 6, 30]:
            cases.append(dict(mouth_open_y=.8, mouth_form=-1, eye_l_open=0, eye_r_open=0, breath=1, angle_z=angle))
        out = ROOT / 'calibration'
        (ROOT/'calibration_cases.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')
    else:
        cases = list(csv.DictReader((ROOT / 'performance_curve.csv').open(encoding='utf-8-sig')))
        out = ROOT / ('frames' if args.stage == 'all' else f'frames_{args.stage}')
    out.mkdir(exist_ok=True)
    values = [float(r['mouth_open_y']) for r in cases]
    forms = [float(r['mouth_form']) for r in cases]
    for i, value in enumerate(values):
        pygame.event.pump()
        model._model.Update(1 / 30)
        model.SetParameterValue('ParamMouthOpenY', value)
        model.SetParameterValue('ParamMouthForm', forms[i])
        model.SetParameterValue('ParamEyeLOpen', float(cases[i]['eye_l_open']))
        model.SetParameterValue('ParamEyeROpen', float(cases[i]['eye_r_open']))
        model.SetParameterValue('ParamAngleZ', float(cases[i]['angle_z']) if args.calibrate or args.stage == 'all' else 0)
        model.SetParameterValue('ParamBreath', float(cases[i]['breath']) if args.calibrate or args.stage != 'blink' else 0)
        live2d.clearBuffer(0, 0, 0, 0)
        model.Draw()
        glFinish()
        pixels = glReadPixels(0, 0, *size, GL_RGBA, GL_UNSIGNED_BYTE)
        # OpenGL renders premultiplied color onto transparent black. PNG stores
        # straight alpha so that later editing/compositing does not darken edges.
        rgba = np.frombuffer(pixels, dtype=np.uint8).reshape(size[1], size[0], 4).copy()
        alpha = rgba[:, :, 3:4].astype(np.float32)
        rgba[:, :, :3] = np.clip(np.rint(rgba[:, :, :3].astype(np.float32) * 255 / np.maximum(alpha, 1)), 0, 255).astype(np.uint8)
        im = Image.fromarray(rgba).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        im.save(out / f'{i:05d}.png')
        if i % 100 == 0:
            print('frame', i, 'mouth', value, 'bbox', im.getbbox(), flush=True)
    model.DestroyRenderer()
    del model
    live2d.dispose()
    pygame.quit()

if __name__ == '__main__':
    main()
