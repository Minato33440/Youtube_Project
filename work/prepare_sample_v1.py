"""Generate T3 narration, editable narration cards/subtitles and sample render spec."""
from pathlib import Path
import array
import hashlib
import json
import math
import re
import time
import urllib.parse
import urllib.request
import wave

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "Politics_Economics/2026-09-09_fiscal_policy"
SPEECH = P / "speech/sample_v1"
CARDS = P / "media/sample_v1/cards"
SUBS = P / "subtitles/sample_v1"
EDIT = P / "code_edit/sample_v1"
for folder in (SPEECH, CARDS, SUBS, EDIT):
    folder.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:10101"
SPEAKER = 135718976
SETTINGS = dict(speedScale=1.17, intonationScale=1.0, tempoDynamicsScale=1.15,
                pitchScale=0.0, volumeScale=1.0, prePhonemeLength=.12,
                postPhonemeLength=.15, pauseLengthScale=1.0,
                outputSamplingRate=44100, outputStereo=False)


def api_post(endpoint, params, body=None, timeout=30):
    data=json.dumps(body).encode() if body is not None else b""
    req=urllib.request.Request(BASE+endpoint+"?"+urllib.parse.urlencode(params),data=data,
                               headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read()


NARRATIONS = [
    dict(id="N01", chapter="INTRODUCTION", title="国の借金があると、\n減税はできない？",
         points=["財源の見方", "成長への投資", "暮らしへのつながり"],
         sentences=["減税をするなら、財源はどうするのか。", "よく聞くこの問いに、会田卓司さんは経済成長という視点から答えています。", "国債への不安と、私たちの暮らしを支える政策は、どうつながるのでしょうか。", "発言を順に見ていきます。"]),
    dict(id="N02", chapter="01 / お金の流れ", title="企業と政府の支出は、\n暮らしにどう届く？",
         points=["借換えと利払い", "企業＋政府の収支", "家計に回る所得"],
         sentences=["借換えは、満期の国債に対応して新しい国債を発行する仕組みで、債務が消えるわけではありません。", "ここからは、企業と政府の支出を合わせて見る考え方です。", "二千二十五年十一月公開の解説で、経済全体のお金の流れを確認します。"]),
    dict(id="N03", chapter="02 / 減税の財源", title="経済が成長したら、\n税収の見方は変わる？",
         points=["−5％は会田氏の提案", "輸入物価などの条件", "成長と税収の関係"],
         sentences=["ここでのマイナス五パーセントは、会田さんが示す政策運営の目安です。", "輸入物価などの条件も合わせて考える必要があります。", "では、経済が成長したときの税収は、どう考えるのか。", "次は、減税の財源についての対談です。"]),
    dict(id="N04", chapter="03 / 投資と暮らし", title="投資の成果が届くまで、\n家計をどう支える？",
         points=["成果が届くまでの時間", "その間の家計支援", "減税の方法をめぐる違い"],
         sentences=["投資を増やしても、すぐに給料が上がるとは限りません。", "その間の暮らしをどう支えるのか。", "減税の具体的な方法では、二人の意見の違いにも注目してください。"]),
    dict(id="N05", chapter="SUMMARY", title="成長と暮らしを、\nつなげて考える。",
         points=["国債を何に使うか", "成長と家計支援を両立", "条件を確かめ、実行へ"],
         sentences=["今回のポイントは、三つです。", "一つ目は、国債の残高だけでなく、何に使い、将来の所得につながるかを見ること。", "二つ目は、経済成長と税収、そして家計の負担を、つなげて考えること。", "三つ目は、投資の成果が届くまで、暮らしを支えることです。", "会田さんは、企業と政府の支出に注目して、成長と家計支援を進める道筋を示しています。", "ただし、物価や金利への影響、投資の成果、予算が実行されるかも確かめる必要があります。", "財源があるかという問いから、成長の力をどう暮らしへ届けるかへ。", "今回の発言を、その視点から考えてみてください。"]),
]


def font(size, bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/meiryob.ttc" if bold else "C:/Windows/Fonts/meiryo.ttc", size)


def make_card(n):
    im = Image.new("RGB", (1920, 1080), "#101c2a")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 22, 1080), fill="#d5ad62")
    d.text((100, 75), "POLITICS & ECONOMY  /  構成確認版", font=font(25), fill="#95abba")
    d.text((100, 156), n["chapter"], font=font(35), fill="#d5ad62")
    d.multiline_text((96, 245), n["title"], font=font(76, True), fill="#f5f3ed", spacing=16)
    for i, text in enumerate(n["points"]):
        x = 100+i*580
        d.rounded_rectangle((x, 545, x+540, 720), radius=18, fill="#1d3042")
        d.text((x+26, 560), f"0{i+1}", font=font(30), fill="#d5ad62")
        size = 32
        while d.textbbox((0, 0), text, font=font(size, True))[2] > 490:
            size -= 1
        d.text((x+26, 628), text, font=font(size, True), fill="#f5f3ed")
    d.line((100, 760, 1820, 760), fill="#3e5364", width=2)
    d.text((100, 1012), "音声：Tαkoe:AivisSpeech:楽町音穏（T3モデル）", font=font(23), fill="#9eb0bd")
    dest=CARDS/(n["id"]+".png")
    im.save(dest)
    return dest


def stamp(t, ass=False):
    if ass:
        cs=round(t*100); return f"{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}"
    ms=round(t*1000); return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"


def wrap(s, width=32):
    # Break at punctuation where feasible; retain every character.
    lines=[]
    while len(s)>width:
        line_count=math.ceil(len(s)/width)
        minimum=max(8,len(s)-width*(line_count-1))
        target=len(s)/line_count
        breaks=[i+1 for i,c in enumerate(s[:width]) if c in "、。" and i+1>=minimum]
        k=min(breaks,key=lambda x:abs(x-target)) if breaks else round(target)
        lines.append(s[:k]);s=s[k:]
    if s:lines.append(s)
    return lines


manifest={"version":"sample_v1", "engine":"AivisSpeech", "speaker":"楽町音穏_T3モデル",
          "style_id":SPEAKER,"settings":SETTINGS,"settings_authority":"User screenshot and subsequent approval; overrides stale default.aisp pitch/pre-silence.",
          "listened":False,"sentences":[],"narrations":[]}
start_run=time.monotonic()
for n in NARRATIONS:
    chunks=[]; cues=[]; cursor=0
    for i,text in enumerate(n["sentences"],1):
        cid=f"{n['id']}_{i:02}"
        spoken=text.replace("会田卓司", "あいだたくじ").replace("会田", "あいだ")
        fingerprint=hashlib.sha256(json.dumps([spoken,SPEAKER,SETTINGS],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        dest=SPEECH/(cid+".wav");meta=SPEECH/(cid+".json")
        if not (dest.exists() and meta.exists() and json.loads(meta.read_text(encoding="utf-8"))["fingerprint"]==fingerprint):
            query=json.loads(api_post("/audio_query",{"text":spoken,"speaker":SPEAKER}));query.update(SETTINGS)
            data=api_post("/synthesis",{"speaker":SPEAKER},body=query,timeout=180)
            dest.write_bytes(data)
            meta.write_text(json.dumps({"fingerprint":fingerprint,"text":text,"spoken_text":spoken,"query":query},ensure_ascii=False,indent=2),encoding="utf-8")
        with wave.open(str(dest),"rb") as w:
            assert w.getsampwidth()==2 and w.getnchannels()==1 and w.getframerate()==44100
            data=w.readframes(w.getnframes()); duration=w.getnframes()/w.getframerate()
        samples=array.array("h",data)
        manifest["sentences"].append({"id":cid,"text":text,"spoken_text":spoken,"duration":duration,
            "peak_dbfs":20*math.log10(max(1,max(abs(x) for x in samples))/32768),
            "full_scale_samples":sum(abs(x)>=32767 for x in samples)})
        cues.append((cursor,cursor+duration,text));cursor+=duration;chunks.append(data)
    wav=SPEECH/(n["id"]+".wav")
    with wave.open(str(wav),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes(b"".join(chunks))
    ass_header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Meiryo,44,&H00FFFFFF,&H00FFFFFF,&H002A1C10,&H002A1C10,0,0,0,0,100,100,0,0,1,1,0,2,110,110,130,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass=SUBS/(n["id"]+".ass")
    ass.write_text(ass_header+"\n".join(f"Dialogue: 0,{stamp(a,True)},{stamp(b,True)},Default,,0,0,0,,"+r"\N".join(wrap(t)) for a,b,t in cues)+"\n",encoding="utf-8-sig")
    (SUBS/(n["id"]+".srt")).write_text("\n\n".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n"+"\n".join(wrap(t)) for i,(a,b,t) in enumerate(cues,1))+"\n",encoding="utf-8")
    card=make_card(n)
    manifest["narrations"].append({"id":n["id"],"duration":cursor,"wav":str(wav),"cues":cues})
    print(n["id"],round(cursor,3),flush=True)

manifest["generation_wall_seconds"]=time.monotonic()-start_run
(SPEECH/"generation_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
(SPEECH/"narration.md").write_text("# Sample MP4 v1 ナレーション\n\n設定はユーザーの最終スクリーンショットに準拠。チャンネル紹介は未確定のため省略。\n\n"+"\n\n".join(f"## {n['id']} {n['title'].replace(chr(10),'')}\n\n"+"".join(n["sentences"]) for n in NARRATIONS),encoding="utf-8")
(SPEECH/"CREDITS.md").write_text("# 音声クレジット\n\n音声：Tαkoe:AivisSpeech:楽町音穏（T3モデル）\n\nモデルの同梱規約スナップショットは ../t3_audition/model_policy_snapshot.txt。今回の合成はローカルAPI。公開時には採用版の概要欄にも記載する。\n",encoding="utf-8")

sources={"HDIBA7-83yE":"三橋TV｜2025-12-13公開", "LRcGT_xzWpY":"三橋TV｜2026-09-06公開", "YXQjMSHSWEo":"三橋TV｜2026-05-03公開", "VdKZeKSmo8o":"三橋TV｜2026-09-05公開", "FjHO1E_QLVo":"ニュースの争点｜2025-11-05公開・当時の説明"}
segments=[]
def v(cid,vid,a,b,chapter):
    segments.append(dict(id=cid,type="video",source=f"media/sources/{vid}.mp4",source_in=a,source_out=b,chapter=chapter,source_label=sources[vid]))
def n(cid):
    item=next(x for x in NARRATIONS if x["id"]==cid)
    segments.append(dict(id=cid,type="narration",wav=f"speech/sample_v1/{cid}.wav",card=f"media/sample_v1/cards/{cid}.png",subtitles=f"subtitles/sample_v1/{cid}.ass",chapter=item["chapter"],text="".join(item["sentences"])))
v("HOOK","HDIBA7-83yE",150.16,171.60,"注目発言｜成長への投資を、どう考える？")
n("N01")
v("C01a","HDIBA7-83yE",142.24,179.60,"01｜国債・財政への不安")
v("C01b","HDIBA7-83yE",200.60,216.35,"01｜国債・財政への不安")
v("C02a","LRcGT_xzWpY",882.12,921.60,"01｜借換えと利払いの論点")
v("C02b","LRcGT_xzWpY",934.12,962.30,"01｜借換えと利払いの論点")
v("C02c","LRcGT_xzWpY",1010.48,1029.80,"01｜借換えと利払いの論点")
n("N02")
for cid,a,b in [("ND01",1508.24,1595.48),("ND02",1701,1767.5),("ND03",1794.28,1813.44),("ND04",1832.4,1894.5)]:
    v(cid,"FjHO1E_QLVo",a,b,"01｜ネット資金需要：会田氏の分析・提案")
n("N03")
v("C03","YXQjMSHSWEo",795.24,955.45,"02｜成長と減税の財源")
v("C04","HDIBA7-83yE",935.88,991.18,"03｜企業の投資と、暮らし")
v("C05a","VdKZeKSmo8o",617.68,646.00,"03｜成長への投資と、その条件")
v("C05b","VdKZeKSmo8o",661.48,716.55,"03｜成長への投資と、その条件")
n("N04")
v("C06","VdKZeKSmo8o",858.12,984.90,"03｜成果が届くまでの家計支援")
v("C07","VdKZeKSmo8o",1086.16,1149.16,"03｜予算を実行へ：2026年9月の対談")
n("N05")
spec=dict(version="sample_v1",width=1920,height=1080,fps=30,output="exports/Sample-MP4_v1.mp4",segments=segments)
(P/"code_edit/sample_v1_spec.json").write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding="utf-8")
print("SPEC READY",len(segments),flush=True)
