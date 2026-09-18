"""Freeze accepted trial configuration as provisional reuse records; no asset mutation."""
from pathlib import Path
import csv,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Live2D/presets'
TRIAL=ROOT/'output/live2d/punctuation_pause_v1'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def write(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
meta={'version':1,'recorded_date':'2026-09-17','status':'provisional',
      'reference_character':'Risa','evaluation':'Boss accepted more natural speech gaps and breathing in PunctuationPause v1; other voices/characters untested',
      'auto_loaded_by_existing_builders':False}
speech={**meta,'id':'japanese_speech_breath_v1','scope':'Japanese synthesized narration; production-side timing policy, not engine defaults',
 'pause_seconds':{'comma':.12,'period':.50,'question_or_major_semantic_boundary':.70,'verified_implicit_clause_pause':.12},
 'pause_semantics':'Total observed pause duration; preserve speech and inspect alignment before editing',
 'breathing_timing':{'inhale_at':'sentence/meaning boundaries with enough verified silence','inhale_at_short_comma':False,
    'inhale_target_seconds':.36,'fps_reference':30,'inhale_frames_reference':11,'inhale_actual_seconds_reference':11/30,
    'pause_end_guard_seconds':.05,'minimum_pause_start_guard_seconds':.03,
    'rounding':'end=floor((pause_end-0.05)*fps); start=end-round(0.36*fps); check start guard',
    'curve':'s(x)=x*x*(3-2*x), x in [0,1]; lo+(hi-lo)*s(x)',
    'exhale_at':'between inhales, including speech and short commas','initial_pose':'already inhaled','final_pose':'hold last exhaled level'},
 'calibration_ref':'human_motion_v1.json','reference_ref':'risa_reference_v1.json',
 'unvalidated':['other TTS models','other speaking rates','long idle breathing','unbroken long-sentence breath replenishment','major topic transition as distinct test case']}
mouth=read('output/live2d/voice_sync_v3/mouth_form_profile.json')
human={**meta,'id':'human_motion_v1','scope':'Risa-derived initial calibration for human-shaped models; not universal safe limits',
 'speech_preset_ref':'japanese_speech_breath_v1.json',
 'parameters':{'mouth_open':'ParamMouthOpenY','mouth_form':'ParamMouthForm','left_eye':'ParamEyeLOpen','right_eye':'ParamEyeROpen','breathing':'ParamBreath','neck_tilt':'ParamAngleZ'},
 'mouth':{'open_semantics':'0=closed; increasing opens; calibration required','mouth_form_semantics':mouth['semantics'],
   'provisional_vowel_form_targets':{'a':0,'e':.35,'i':.9,'u':-.396,'o':-.55},
   'target_basis':'v3 vowel targets, negative targets multiplied once by 0.55; actual curve is smoothed',
   'neutralization':mouth['neutralization'],'closed_lips':'m/b/p and silence ease toward neutral; reference opening algorithm in risa_reference_v1.json'},
 'blink':{'parameter_open':1,'parameter_closed':0,'profile_at_30fps':[1,.45,0,0,.25,.6,.84,1],
   'duration_seconds':7/30,'candidate':'sentence boundaries','minimum_center_spacing_seconds':2.2,
   'retiming':'move center, preserve duration; recheck spacing for new audio'},
 'neck':{'reference_pulse_half_width_seconds':.34,'reference_emphasis_peak_magnitudes':[6.4,8.4,7.6,6.2],
   'units':'ParamAngleZ values, not measured geometric degrees','placement':'select emphasis from meaning, not fixed timestamps','safe_range':'calibrate per model'},
 'breath_values':{'parameter':'ParamBreath','increasing':'inhalation','decreasing':'exhalation','floor':.18,'peak':.593756,
   'exhale_drop_rate_coefficient_per_second':.11,'maximum_drop_per_exhale_segment':.36,
   'valley_formula':'max(floor, level-min(maximum_drop, coefficient*segment_seconds))',
   'interpolation':'smoothstep; coefficient controls total drop, not constant instantaneous velocity'},
 'rig_intent':{'stable':['face','upper collar edge','outer collar silhouette','belt'],
   'moving':['localized chest expansion','shoulders','abdominal knit folds','internal throat and upper collar folds'],
   'avoid':'whole upper torso and neck vertical bobbing'},
 'risa_reference_ref':'risa_reference_v1.json','per_character_required':['parameter range and sign calibration','mouth closure and shapes','neck and collar gap test','breathing visibility and silhouette','audio visual listening review']}
paths=['output/live2d/punctuation_pause_v1/build_sample.py','output/live2d/punctuation_pause_v1/pause_profile.json',
 'output/live2d/punctuation_pause_v1/time_map.json','output/live2d/punctuation_pause_v1/breath_events.json',
 'output/live2d/punctuation_pause_v1/performance_curve.csv','output/live2d/punctuation_pause_v1/performance.motion3.json',
 'output/live2d/punctuation_pause_v1/N01.wav','output/live2d/punctuation_pause_v1/verification.json',
 'output/live2d/punctuation_pause_v1/model/Risa_chest_breath.cmo3','output/live2d/punctuation_pause_v1/model/Risa_chest_breath.moc3',
 'output/live2d/punctuation_pause_v1/model/Risa_chest_breath.2048/texture_00.png',
 'output/live2d/voice_sync_v2/refine_mouth_curve.py','output/live2d/voice_sync_v3/mouth_form_profile.json',
 'output/live2d/full_sample_v1/N01/performance_profile.json','output/live2d/narration_adjustment_v1/adjustment_profile.json',
 'Politics_Economics/2026-09-09_fiscal_policy/speech/sample_v1/N01_01.json',
 'Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_PunctuationPause_v1.mp4']
rows=list(csv.DictReader((TRIAL/'performance_curve.csv').open(encoding='utf-8')))
channels=['mouth_open_y','mouth_form','eye_l_open','eye_r_open','breath','angle_z']
reference={**meta,'id':'risa_reference_v1','paths_relative_to':'Youtube_Project repository root',
 'shared_ref':'japanese_speech_breath_v1.json','human_ref':'human_motion_v1.json',
 'accepted_trial':'output/live2d/punctuation_pause_v1','rig_version':'chest_breath_v8',
 'measured_trial_ranges':{k:{'min':min(float(r[k]) for r in rows),'max':max(float(r[k]) for r in rows)} for k in channels},
 'range_note':'Observed range of this clip, not rig safety limits or universal defaults',
 'risa_adjustment_snapshot':read('output/live2d/narration_adjustment_v1/adjustment_profile.json'),
 'multiplier_warning':'Relative to full_sample_v1/N01 base curve. Apply once only; not gains to apply to an arbitrary new rig or the already adjusted curve.',
 'layout_note':'1920x1080 narration layout is Risa/video-specific, not a human archetype default',
 'tts_reference':{'model':'楽町音穏_T3','style_id':135718976,'speedScale':1.17,'tempoDynamicsScale':1.15,'prePhonemeLength':.12,'postPhonemeLength':.15,
   'note':'Risa reference voice settings, not shared TTS defaults; punctuation gaps subsequently edited'},
 'provenance':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in paths]}
for filename,data in [('japanese_speech_breath_v1.json',speech),('human_motion_v1.json',human),('risa_reference_v1.json',reference)]:write(filename,data)
print('Recorded 3 presets; verified',len(paths),'source paths and hashes.')
