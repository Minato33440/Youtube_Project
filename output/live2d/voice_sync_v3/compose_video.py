"""Compose the real Cubism render with the supplied narration clip."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = Path('C:/Users/Setona/Desktop/Voicd-Sample.mp4')
FPS, FRAMES = 30, 478
DURATION = FRAMES / FPS

def run(*args):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *map(str, args)], check=True)

def main():
    frames = ROOT / 'frames/%05d.png'
    audio = ROOT / 'audio_stereo_44100_pcm16.wav'
    encode = ['-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-t', DURATION, '-movflags', '+faststart']
    run('-i', SOURCE, '-framerate', FPS, '-i', frames,
        '-filter_complex', '[1:v]crop=512:560:128:0,scale=256:280:flags=lanczos[avatar];[0:v][avatar]overlay=850:66:alpha=straight:shortest=1[v]',
        '-map', '[v]', '-map', '0:a:0', *encode, ROOT / 'Risa_narration_composite.mp4')
    run('-f', 'lavfi', '-i', f'color=c=0x101e2b:s=1280x720:r={FPS}:d={DURATION}',
        '-framerate', FPS, '-i', frames, '-i', audio,
        '-filter_complex', '[1:v]crop=360:400:204:0,scale=648:720:flags=lanczos[avatar];[0:v][avatar]overlay=316:0:alpha=straight:shortest=1[v]',
        '-map', '[v]', '-map', '2:a:0', *encode, ROOT / 'Risa_lipsync_closeup.mp4')
    font = "fontfile='C\\:/Windows/Fonts/arial.ttf'"
    run('-framerate', FPS, '-i', ROOT.parent / 'voice_sync_v2/frames/%05d.png',
        '-framerate', FPS, '-i', frames, '-i', audio,
        '-f', 'lavfi', '-i', f'color=c=0x101e2b:s=1280x720:r={FPS}:d={DURATION}',
        '-filter_complex',
        '[0:v]crop=360:400:204:0,scale=576:640:flags=lanczos[left];'
        '[1:v]crop=360:400:204:0,scale=576:640:flags=lanczos[right];'
        '[3:v][left]overlay=32:64:alpha=straight:shortest=1[bg];[bg][right]overlay=672:64:alpha=straight:shortest=1[both];'
        f"[both]drawtext={font}:text='V2 - approved timing':x=28:y=22:fontsize=26:fontcolor=white,drawtext={font}:text='V3 - width / roundness':x=668:y=22:fontsize=26:fontcolor=white[v]",
        '-map', '[v]', '-map', '2:a:0', *encode, ROOT / 'Risa_lipsync_comparison.mp4')
    # Transparent individual PNG frames remain the lossless editable layer.
    manifest = {
        'source_video': str(SOURCE), 'fps': FPS, 'frame_count': FRAMES,
        'duration_seconds': DURATION, 'source_audio_offset_seconds': 0,
        'model': 'model/Risa_mouth_shapes.model3.json', 'editor_model': 'Risa_mouth_shapes.cmo3',
        'audio': audio.name, 'curve': 'mouth_curve.csv', 'motion_reference': 'voice_sync.motion3.json',
        'rgba_frames': 'frames/%05d.png', 'alpha_mode': 'straight',
        'overlay': {'source_crop_xywh': [128, 0, 512, 560], 'size': [256, 280], 'xy': [850, 66]},
        'mouth_driver': 'ParamMouthOpenY locked to approved v2; ParamMouthForm from Japanese vowel design and coarticulation',
        'alignment': '../voice_sync_v2/alignment/phonemes.json',
        'fixed_parameters': {'ParamEyeLOpen': 1, 'ParamEyeROpen': 1, 'ParamAngleZ': 0, 'ParamBreath': 0},
        'outputs': ['Risa_narration_composite.mp4', 'Risa_lipsync_closeup.mp4', 'Risa_lipsync_comparison.mp4'],
    }
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
