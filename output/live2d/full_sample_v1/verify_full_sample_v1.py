"""Mechanical acceptance checks for the five full Sample v1 Live2D assets."""
from pathlib import Path
import csv, json, subprocess
from PIL import Image

ROOT=Path(__file__).resolve().parent
PLAN={"N01":479,"N02":540,"N03":530,"N04":343,"N05":1285}
CHANNELS={"ParamMouthOpenY":"mouth_open_y","ParamMouthForm":"mouth_form","ParamEyeLOpen":"eye_l_open","ParamEyeROpen":"eye_r_open","ParamBreath":"breath","ParamAngleZ":"angle_z"}
def probe(path):
    return json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-of","json",str(path)]))
def main():
    report={"pass":True,"items":{}}
    for name,count in PLAN.items():
        folder=ROOT/name; rows=list(csv.DictReader((folder/"performance_curve.csv").open(encoding="utf-8-sig")))
        assert len(rows)==count
        assert list(rows[0])[:8] == ["frame","time_s","mouth_open_y","mouth_form","eye_l_open","eye_r_open","breath","angle_z"]
        motion=json.loads((folder/"performance.motion3.json").read_text(encoding="utf-8")); assert motion["Meta"]["Fps"]==30 and motion["Meta"]["Loop"] is False and motion["Meta"]["CurveCount"]==6
        assert {x["Id"] for x in motion["Curves"]}==set(CHANNELS)
        for curve in motion["Curves"]:
            seg=curve["Segments"]; values=[seg[1],*seg[4::3]]; times=[seg[0],*seg[3::3]]; expected=[float(r[CHANNELS[curve["Id"]]]) for r in rows]
            assert len(values)==count and all(abs(a-b)<1e-6 for a,b in zip(values,expected)) and all(abs(t-i/30)<1e-6 for i,t in enumerate(times))
        assert all(0<=float(r[k])<=1 for r in rows for k in ["mouth_open_y","eye_l_open","eye_r_open","breath"])
        assert all(-1<=float(r["mouth_form"])<=1 and -6<=float(r["angle_z"])<=6 for r in rows)
        frames=sorted((folder/"frames").glob("frame_*.png")); assert len(frames)==count
        first=Image.open(frames[0]); assert first.size==(768,1024) and first.mode=="RGBA" and first.getpixel((0,0))[3]==0
        mov=folder/f"{name}_alpha_512x560.mov"; streams=probe(mov)["streams"]; video=next(s for s in streams if s["codec_type"]=="video")
        assert (int(video["width"]),int(video["height"]))==(512,560) and video["pix_fmt"].startswith("yuva444p") and video["r_frame_rate"]=="30/1" and int(video["nb_frames"])==count
        decoded=subprocess.run(["ffmpeg","-v","error","-i",str(mov),"-f","null","-"],capture_output=True,text=True); assert decoded.returncode==0 and not decoded.stderr
        report["items"][name]={"frames":count,"motion_duration_s":motion["Meta"]["Duration"],"png_canvas":"768x1024 RGBA straight-alpha","mov":{"name":mov.name,"size":"512x560","pix_fmt":video["pix_fmt"],"fps":video["r_frame_rate"],"decode_pass":True},"ranges":{k:[min(float(r[k]) for r in rows),max(float(r[k]) for r in rows)] for k in CHANNELS.values()}}
    (ROOT/"verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
