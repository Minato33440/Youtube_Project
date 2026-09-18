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
    parser.add_argument('--smoke', action='store_true')
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
    model.LoadModelJson(str(ROOT / 'model/Risa_compat.model3.json'))
    model.Resize(*size)
    model.SetAutoBlinkEnable(False)
    model.SetAutoBreathEnable(False)
    print('canvas', model.GetCanvasSizePixel(), 'parameters', model.GetParameterCount(), flush=True)
    out = ROOT / ('calibration' if args.calibrate else ('smoke' if args.smoke else 'frames'))
    out.mkdir(exist_ok=True)
    if args.calibrate:
        values = [0, .15, .3, .45, .6, .75, .9]
    elif args.smoke:
        values = [0, .5, 1]
    else:
        rows = list(csv.DictReader((ROOT / 'mouth_curve.csv').open(encoding='utf-8-sig')))
        print('columns', list(rows[0]), flush=True)
        values = [float(r['mouth_open_y']) for r in rows]
    for i, value in enumerate(values):
        pygame.event.pump()
        model._model.Update(1 / 30)
        model.SetParameterValue('ParamMouthOpenY', value)
        model.SetParameterValue('ParamEyeLOpen', 1)
        model.SetParameterValue('ParamEyeROpen', 1)
        model.SetParameterValue('ParamAngleZ', 0)
        model.SetParameterValue('ParamBreath', 0)
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
