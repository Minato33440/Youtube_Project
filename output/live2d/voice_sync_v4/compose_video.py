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
        '-map', '[v]', '-map', '2:a:0', *encode, ROOT / 'Risa_performance_closeup.mp4')
    font = "fontfile='C\\:/Windows/Fonts/arial.ttf'"
    run('-framerate', FPS, '-i', ROOT.parent / 'voice_sync_v3/frames/%05d.png',
        '-framerate', FPS, '-i', frames, '-i', audio,
        '-f', 'lavfi', '-i', f'color=c=0x101e2b:s=1280x720:r={FPS}:d={DURATION}',
        '-filter_complex',
        '[0:v]crop=360:400:204:0,scale=576:640:flags=lanczos[left];'
        '[1:v]crop=360:400:204:0,scale=576:640:flags=lanczos[right];'
        '[3:v][left]overlay=32:64:alpha=straight:shortest=1[bg];[bg][right]overlay=672:64:alpha=straight:shortest=1[both];'
        f"[both]drawtext={font}:text='V3 - approved mouth':x=28:y=22:fontsize=26:fontcolor=white,drawtext={font}:text='V4 - coordinated motion':x=668:y=22:fontsize=26:fontcolor=white[v]",
        '-map', '[v]', '-map', '2:a:0', *encode, ROOT / 'Risa_performance_comparison.mp4')
    for stage in ['blink', 'breath']:
        run('-f', 'lavfi', '-i', f'color=c=0x101e2b:s=1280x720:r={FPS}:d={DURATION}',
            '-framerate', FPS, '-i', ROOT / f'frames_{stage}/%05d.png', '-i', audio,
            '-filter_complex', '[1:v]crop=360:400:204:0,scale=648:720:flags=lanczos[avatar];[0:v][avatar]overlay=316:0:alpha=straight:shortest=1[v]',
            '-map', '[v]', '-map', '2:a:0', *encode, ROOT / f'Risa_stage_{stage}.mp4')
    # Transparent individual PNG frames remain the lossless editable layer.
    manifest = {
        'source_video': str(SOURCE), 'fps': FPS, 'frame_count': FRAMES,
        'duration_seconds': DURATION, 'source_audio_offset_seconds': 0,
        'model': 'model/Risa_performance.model3.json', 'editor_model': 'Risa_coordinated.cmo3',
        'audio': audio.name, 'curve': 'performance_curve.csv', 'motion_reference': 'performance.motion3.json',
        'rgba_frames': 'frames/%05d.png', 'alpha_mode': 'straight',
        'overlay': {'source_crop_xywh': [128, 0, 512, 560], 'size': [256, 280], 'xy': [850, 66]},
        'mouth_driver': 'Both mouth channels locked to approved v3; blink, breath and AngleZ follow coordination_rules.json and events.json',
        'alignment': '../voice_sync_v2/alignment/phonemes.json',
        'performance_rules': 'coordination_rules.json', 'performance_events': 'events.json', 'auto_blink_breath': False,
        'outputs': ['Risa_narration_composite.mp4', 'Risa_performance_closeup.mp4', 'Risa_performance_comparison.mp4', 'Risa_stage_blink.mp4', 'Risa_stage_breath.mp4'],
    }
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
