"""Build per-narration Live2D motions and straight-alpha renders for Sample v1.

The mouth aperture/form rules are the approved v2/v3 rules, generalized to
each original VoiceVox utterance.  Julius measures phone timing separately for
every source utterance; eye, breath, and neck remain deliberately modest
editorial performance curves.  This file never changes original speech or the
approved v1-v4 folders.
"""
from __future__ import annotations

import csv, json, math, re, shutil, subprocess, sys, wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
SPEECH = PROJECT / "Politics_Economics/2026-09-09_fiscal_policy/speech/sample_v1"
AUTHORITATIVE_AUDIO = PROJECT / "Politics_Economics/2026-09-09_fiscal_policy/media/sample_v1_risa/audio"
TIMELINE = PROJECT / "Politics_Economics/2026-09-09_fiscal_policy/code_edit/sample_v1/timeline.csv"
V4 = ROOT.parent / "voice_sync_v4"
KIT = ROOT.parent / "alignment_tools/segmentation-kit"
JULIUS, HMM, HLIST = KIT / "bin/julius-4.3.1.exe", KIT / "models/hmmdefs_ptm_gid.binhmm", KIT / "models/logicalTri"
FPS = 30
REVISION = "v2_sentence_boundaries_and_keyword_beats"
VOWEL_OPEN = {"a": .80, "e": .64, "o": .59, "i": .43, "u": .38}
VOWEL_FORM = {"a": 0.0, "e": .35, "i": .9, "u": -.72, "o": -1.0}
CLOSED, SILENCE = {"m", "b", "p", "cl"}, {"sil", "silb", "sile", "sp", "pau"}
ALIGN_RE = re.compile(r"^\[\s*(\d+)\s+(\d+)\]\s+[0-9.\-]+\s+(.*)$")

def wav_duration(path):
    with wave.open(str(path)) as w: return w.getnframes() / w.getframerate()

def load_tokens(part):
    data = json.loads((SPEECH / f"{part}.json").read_text(encoding="utf-8-sig"))
    tokens=[]
    for phrase in data["query"]["accent_phrases"]:
        for mora in phrase["moras"]:
            if mora["vowel"] == "pau": tokens.append(("sp", mora["text"]))
            else:
                if mora["consonant"]: tokens.append((mora["consonant"], mora["text"]))
                tokens.append((mora["vowel"], mora["text"]))
    return tokens

def make_grammar(tokens, prefix):
    # VoiceVox calls the Japanese geminate closure `cl`; this Julius acoustic
    # model exposes the corresponding phone as `q`.  Keep `cl` in the output
    # labels so the approved mouth-closure rule still applies.
    words=["silB", *["silB" if p == "sp" else "q" if p == "cl" else p for p,_ in tokens], "silE"]
    end=len(words)-1
    prefix.with_suffix(".dfa").write_text("\n".join(f"{i} {end-i} {i+1} 0 {1 if i==0 else 0}" for i in range(len(words)))+f"\n{len(words)} -1 -1 1 0\n", encoding="ascii")
    prefix.with_suffix(".dict").write_text("\n".join(f"{i} [w_{i}] {p}" for i,p in enumerate(words))+"\n", encoding="ascii")

def dither_zeros(source, dest):
    with wave.open(str(source)) as w:
        params=w.getparams(); values=np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").copy()
    values[values == 0] = 1
    with wave.open(str(dest), "wb") as w: w.setparams(params); w.writeframes(values.astype("<i2").tobytes())

def align_part(part, work):
    tokens=load_tokens(part); converted=work/f"{part}_16k.wav"; input_wav=work/f"{part}_input.wav"; prefix=work/part
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(SPEECH/f"{part}.wav"),"-ac","1","-ar","16000","-c:a","pcm_s16le",str(converted)], check=True)
    dither_zeros(converted,input_wav); make_grammar(tokens,prefix)
    done=subprocess.run([str(JULIUS),"-h",str(HMM),"-hlist",str(HLIST),"-dfa",str(prefix.with_suffix(".dfa")),"-v",str(prefix.with_suffix(".dict")),"-palign","-input","file","-nostrip"], input=str(input_wav)+"\n", text=True, capture_output=True, cwd=str(KIT))
    log=done.stdout+"\n--- STDERR ---\n"+done.stderr; (work/f"{part}.log").write_text(log, encoding="utf-8")
    if done.returncode: raise RuntimeError(f"Julius failed for {part}")
    entries=[]; active=False
    for line in log.splitlines():
        if "begin forced alignment" in line: active=True; continue
        if "end forced alignment" in line: active=False
        if active and (m:=ALIGN_RE.match(line)): entries.append((int(m.group(1)),int(m.group(2))))
    entries=entries[1:-1]
    if len(entries) != len(tokens): raise RuntimeError(f"{part}: Julius {len(entries)} tokens, expected {len(tokens)}")
    rows=[]
    for (bf,ef),(phone,mora) in zip(entries,tokens):
        rows.append({"start_s_source":round(bf*.01+(.0125 if bf else 0),7),"end_s_source":round((ef+1)*.01+.0125,7),"phoneme":phone,"mora":mora,"part":part})
    return rows

def smooth(values, sigma=.014, rate=1000):
    x=np.arange(-round(sigma*rate*3), round(sigma*rate*3)+1)/rate; k=np.exp(-.5*(x/sigma)**2); return np.convolve(values,k/k.sum(),mode="same")

def pulse(values, center, width, amp):
    for i in range(len(values)):
        d=abs(i/FPS-center)
        if d <= width: values[i] += amp*.5*(1+math.cos(math.pi*d/width))

def segments(values):
    out=[0.0,round(float(values[0]),6)]
    for i,v in enumerate(values[1:],1): out += [0,round(i/FPS,6),round(float(v),6)]
    return out

def narration_rows():
    rows=list(csv.DictReader(TIMELINE.open(encoding="utf-8-sig")))
    return [r for r in rows if r["type"] == "narration"]

# Values are restrained v4-style editorial pulses.  Fractions locate the
# stated phrase inside its original VoiceVox sentence after measured placement;
# they are not facial-capture claims.
KEYWORD_BEATS={
 "N01":[("財源",0,.66,3.2),("経済成長",1,.47,-4.2),("国債への不安",2,.12,3.8),("暮らしを支える政策",2,.54,-3.1)],
 "N02":[("借換え",0,.12,3.2),("企業と政府",1,.32,-4.2),("お金の流れ",2,.62,3.8)],
 "N03":[("マイナス五パーセント",0,.36,3.2),("経済成長",2,.38,-4.2),("減税の財源",3,.48,3.8)],
 "N04":[("投資",0,.13,3.2),("暮らし",1,.46,-4.2),("減税の具体的な方法",2,.37,3.8)],
 "N05":[("国債を何に使うか",1,.48,3.2),("経済成長と税収",2,.36,-4.2),("暮らしを支える",3,.51,3.8),("成長と家計支援",4,.61,-3.2),("物価や金利",5,.31,3.2),("成長の力をどう暮らしへ",6,.58,-3.2)]}

def build_one(item, render):
    name=item["id"]; audio=AUTHORITATIVE_AUDIO/f"{name}.wav"; count=int(item["planned_frames"]); duration=count/FPS
    out=ROOT/name; work=out/"alignment_work"; out.mkdir(parents=True,exist_ok=True); work.mkdir(exist_ok=True)
    parts=sorted(p.stem for p in SPEECH.glob(f"{name}_*.wav"))
    aligned=[]; offset=0.0
    for part in parts:
        phones=align_part(part,work)
        for p in phones:
            p["start_s"]=round(p["start_s_source"]+offset,7); p["end_s"]=round(p["end_s_source"]+offset,7); aligned.append(p)
        offset += wav_duration(SPEECH/f"{part}.wav")
    # The parent extracted these PCM tracks from the approved intermediate
    # renders.  Decode to mono for energy only; the original stereo PCM is not
    # altered or copied by this builder.
    rate=44100; sound=np.frombuffer(subprocess.check_output(["ffmpeg","-v","error","-i",str(audio),"-ac","1","-ar",str(rate),"-f","s16le","-"]),dtype="<i2").astype(float)/32768
    def rms(a,b):
        a,b=max(0,round(a*rate)),min(len(sound),round(b*rate)); return float(np.sqrt(np.mean(sound[a:b]**2))) if b>a else 0.
    t=np.arange(0,duration+.1,.001); target=np.zeros(len(t)); vowel_energy=[]
    for p in aligned:
        key=p["phoneme"].lower().rstrip(":")
        if key in VOWEL_OPEN: vowel_energy.append(rms(p["start_s"],p["end_s"]))
    reference=float(np.percentile(vowel_energy,85)) if vowel_energy else 1.
    for ix,p in enumerate(aligned):
        raw=p["phoneme"]; key=raw.lower().rstrip(":"); energy=rms(p["start_s"],p["end_s"])
        if key in SILENCE or raw in CLOSED: value=0.
        elif key in VOWEL_OPEN: value=VOWEL_OPEN[key]*(.84+.16*np.clip(energy/max(reference,.0001),0,1))*(.72 if raw.isupper() else 1)
        elif raw == "N": value=.14
        elif raw in {"s","sh","z","j","ch","ts","f"}: value=.12 if raw=="f" else .19
        else:
            following=next((q["phoneme"].lower().rstrip(":") for q in aligned[ix+1:ix+4] if q["phoneme"].lower().rstrip(":") in VOWEL_OPEN),"u"); value=VOWEL_OPEN[following]*.56
        target[(t>=max(0,p["start_s"]-.020))&(t<p["end_s"]-.020)]=value
    # observed acoustic quiet runs override uncertain alignment.
    quiet=np.array([rms(b,b+.01)<.001 for b in np.arange(0,duration,.01)])
    start=None
    for i in range(len(quiet)+1):
        active=i<len(quiet) and quiet[i]
        if active and start is None: start=i
        if not active and start is not None:
            if i-start >= 4: target[(t>=max(0,start*.01-.02))&(t<i*.01-.02)]=0
            start=None
    times=np.arange(count)/FPS; opening=np.interp(times,t,smooth(target)); opening[opening<.025]=0
    for p in aligned:
        if p["phoneme"] in CLOSED and p["end_s"]-p["start_s"]>=.035:
            ix=round(((p["start_s"]+p["end_s"])/2-.02)*FPS)
            if 0<=ix<count: opening[ix]=0
    for i in range(1,count): opening[i]=min(opening[i],opening[i-1]+.34)
    for i in range(count-2,-1,-1): opening[i]=min(opening[i],opening[i+1]+.34)
    # V3 mouth form: interpolated vowels, neutralized around silence/closures.
    centers=[((p["start_s"]+p["end_s"])/2,VOWEL_FORM[p["phoneme"].lower().rstrip(":")]) for p in aligned if p["phoneme"].lower().rstrip(":") in VOWEL_FORM]
    form=np.zeros_like(t) if not centers else np.interp(t,*zip(*centers),left=0,right=0); form=smooth(form,.040)
    neutral=np.zeros_like(t,dtype=bool)
    for p in aligned:
        k=p["phoneme"].lower().rstrip(":")
        if k in SILENCE or p["phoneme"] in CLOSED: neutral|=(t>=p["start_s"])&(t<p["end_s"])
    if neutral.any():
        near=np.flatnonzero(neutral); dist=np.array([np.min(np.abs(j-near)) for j in range(len(t))])*.001; x=np.clip(dist/.09,0,1); form*=x*x*(3-2*x)
    form=np.clip(np.interp(times,t,form),-1,1); form[np.abs(form)<.004]=0
    # v4's bilateral eight-sample blink profile, but placed at real joins
    # between independently synthesized sentences.  The output rests through
    # the final padding; it never repeats a 16-s performance loop.
    bounds=[]
    for part in parts:
        ps=[p for p in aligned if p["part"]==part]
        bounds.append((part,min(p["start_s"] for p in ps),max(p["end_s"] for p in ps)))
    eye=np.ones(count); blink_times=[]
    for _,start,end in bounds[:-1]:
        candidate=round(end-.17,3)
        if .8<candidate<duration-.8 and (not blink_times or candidate-blink_times[-1]>=2.2): blink_times.append(candidate)
    profile=[1,.45,0,0,.25,.6,.84,1]
    for bt in blink_times:
        for d,v in enumerate(profile):
            ix=round(bt*FPS)+d
            if ix<count: eye[ix]=min(eye[ix],v)
    breath=np.array([.38+.10*math.sin(2*math.pi*(i/FPS-.67)/4) for i in range(count)])
    for p in aligned:
        if p["phoneme"].lower().rstrip(":") in SILENCE and p["end_s"]-p["start_s"]>=.3: pulse(breath,(p["start_s"]+p["end_s"])/2,max(.7,(p["end_s"]-p["start_s"])/2),.12)
    for i in range(count): breath[i]*=min(1,(i/FPS)/.5,max(0,((count-1)/FPS-i/FPS)/.6))
    # Sentence-relative, named editorial beats; signs/width match v4 rules.
    angle=np.zeros(count)
    beat_events=[]
    by_part={part:(start,end) for part,start,end in bounds}
    for label,part_ix,fraction,amplitude in KEYWORD_BEATS[name]:
        part,start,end= bounds[part_ix]; at=start+(end-start)*fraction
        pulse(angle,at,.34,amplitude); beat_events.append({"text":label,"part":part,"time_s":round(at,6),"angle_z":amplitude,"basis":"manual editorial phrase placement within measured sentence bounds"})
    if count>=4: eye[-4:]=1; angle[-4:]=0
    fields=["frame","time_s","mouth_open_y","mouth_form","eye_l_open","eye_r_open","breath","angle_z","phoneme","mora"]
    rows=[]
    for i,ts in enumerate(times):
        p=next((p for p in aligned if p["start_s"]<=ts<p["end_s"]),{})
        rows.append(dict(frame=i,time_s=f"{ts:.6f}",mouth_open_y=f"{opening[i]:.6f}",mouth_form=f"{form[i]:.6f}",eye_l_open=f"{eye[i]:.6f}",eye_r_open=f"{eye[i]:.6f}",breath=f"{np.clip(breath[i],0,1):.6f}",angle_z=f"{np.clip(angle[i],-6,6):.6f}",phoneme=p.get("phoneme","sil"),mora=p.get("mora","")))
    with (out/"performance_curve.csv").open("w",encoding="utf-8",newline="") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    channels=[("ParamMouthOpenY","mouth_open_y"),("ParamMouthForm","mouth_form"),("ParamEyeLOpen","eye_l_open"),("ParamEyeROpen","eye_r_open"),("ParamBreath","breath"),("ParamAngleZ","angle_z")]
    motion={"Version":3,"Meta":{"Duration":duration,"Fps":FPS,"Loop":False,"CurveCount":6,"TotalSegmentCount":(count-1)*6,"TotalPointCount":count*6,"AreBeziersRestricted":True},"Curves":[{"Target":"Parameter","Id":a,"Segments":segments([float(r[b]) for r in rows])} for a,b in channels],"UserData":[]}
    (out/"performance.motion3.json").write_text(json.dumps(motion,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    profile_meta={"revision":REVISION,"source_audio":str(audio),"source_audio_duration_s":wav_duration(audio),"timeline_planned_frames":count,"timeline_duration_s":duration,"alignment":"Julius 4.3.1 forced Viterbi, separately per VoiceVox source utterance; measured part offsets are recorded in audio_alignment_report.json.","mouth":"Approved v2 aperture and v3 form rules adapted to the separately aligned source utterances; editorial approximation, not face tracking.","performance":{"blink_profile_samples":[1,.45,0,0,.25,.6,.84,1],"blink_times_s":blink_times,"blink_basis":"real source-sentence joins with >=2.2s spacing","breath":"v4 baseline and long-pause rule","neck_events":beat_events,"neck_rule":"v4 pulse width 0.34 seconds, restrained parameter amplitudes"},"n01_v4_copy_status":"not copied: audio_alignment_report.json finds v4 audio correlation 0.0028 with the current N01 intermediate; copy condition is not met."}
    (out/"performance_profile.json").write_text(json.dumps(profile_meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"phonemes.json").write_text(json.dumps({"phonemes":aligned},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if render: render_frames(out, rows, name)
    return {"id":name,"revision":REVISION,"frames":count,"motion_duration_s":duration,"audio_duration_s":wav_duration(audio),"aligned_phone_count":len(aligned),"blink_count":len(blink_times),"beats":beat_events}

def render_frames(out, rows, name):
    import os; os.environ["PYGAME_HIDE_SUPPORT_PROMPT"]="1"
    import pygame
    from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE, glFinish
    from PIL import Image
    import live2d.v3 as live2d
    frames=out/"frames"; frames.mkdir(exist_ok=True); size=(768,1024)
    mov=out/f"{name}_alpha_512x560.mov"
    # A prior complete render is immutable for this build; this makes resumed
    # long batch rendering safe after a host timeout.
    old_manifest=json.loads((out/"render_manifest.json").read_text(encoding="utf-8")) if (out/"render_manifest.json").exists() else {}
    if old_manifest.get("revision")==REVISION and len(list(frames.glob("frame_*.png"))) == len(rows) and mov.exists() and mov.stat().st_size > 1_000_000:
        return
    pygame.display.init(); live2d.init(); pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE,8); pygame.display.set_mode(size,pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN); live2d.glInit()
    model=live2d.LAppModel(); model.LoadModelJson(str(V4/"model/Risa_performance.model3.json")); model.Resize(*size); model.SetAutoBlinkEnable(False); model.SetAutoBreathEnable(False)
    for i,r in enumerate(rows):
        pygame.event.pump(); model._model.Update(1/FPS)
        for param,key in [("ParamMouthOpenY","mouth_open_y"),("ParamMouthForm","mouth_form"),("ParamEyeLOpen","eye_l_open"),("ParamEyeROpen","eye_r_open"),("ParamBreath","breath"),("ParamAngleZ","angle_z")]: model.SetParameterValue(param,float(r[key]))
        live2d.clearBuffer(0,0,0,0); model.Draw(); glFinish(); px=glReadPixels(0,0,*size,GL_RGBA,GL_UNSIGNED_BYTE); rgba=np.frombuffer(px,dtype=np.uint8).reshape(size[1],size[0],4).copy(); alpha=rgba[:,:,3:4].astype(np.float32); rgba[:,:,:3]=np.clip(np.rint(rgba[:,:,:3].astype(np.float32)*255/np.maximum(alpha,1)),0,255).astype(np.uint8)
        Image.fromarray(rgba).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(frames/f"frame_{i:06d}.png")
        if i%100==0: print(name,"frame",i,flush=True)
    model.DestroyRenderer(); live2d.dispose(); pygame.quit()
    subprocess.run(["ffmpeg","-y","-v","error","-framerate","30","-i",str(frames/"frame_%06d.png"),"-vf","crop=512:560:128:0","-c:v","prores_ks","-profile:v","4","-pix_fmt","yuva444p10le",str(mov)],check=True)
    (out/"render_manifest.json").write_text(json.dumps({"revision":REVISION,"frames_dir":"frames","frame_pattern":"frame_%06d.png","straight_alpha_png":True,"source_canvas_px":[768,1024],"mov":mov.name,"mov_crop_xywh":[128,0,512,560],"codec":"ProRes 4444 with alpha (ffprobe reports yuva444p12le)","fps":FPS,"frame_count":len(rows)},indent=2)+"\n",encoding="utf-8")

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--render",action="store_true"); args=ap.parse_args()
    result=[build_one(item,args.render) for item in narration_rows()]
    (ROOT/"build_report.json").write_text(json.dumps({"items":result,"rendered":args.render},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__ == "__main__": main()
