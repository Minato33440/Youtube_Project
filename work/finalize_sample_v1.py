"""Write the handoff subtitles and measured review report after final QA."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
OUT=P/'code_edit/sample_v1'
m=json.loads((OUT/'render_manifest.json').read_text(encoding='utf-8'))
q=json.loads((OUT/'qa_results.json').read_text(encoding='utf-8'))
g=json.loads((P/'speech/sample_v1/generation_manifest.json').read_text(encoding='utf-8'))
assert q['all_audio_placement_passed'] and q['all_headers_present']

def stamp(t):
    ms=round(t*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'

cues=[]
for n in g['narrations']:
    offset=next(row['timeline_in'] for row in m['segments'] if row['id']==n['id'])
    for a,b,text in n['cues']:
        cues.append(f'{len(cues)+1}\n{stamp(offset+a)} --> {stamp(offset+b)}\n{text}')
(P/'subtitles/sample_v1/narration_global.srt').write_text('\n\n'.join(cues)+'\n',encoding='utf-8')
size=Path(m['output']).stat().st_size
report=f'''# Sample MP4 v1 検査記録

2026-09-10。状態：構成確認用MP4作成完了。機械検査と代表フレーム確認を実施。聴取・通し視聴は未実施。

## 実測

- 出力：`exports/Sample-MP4_v1.mp4`
- 尺：{m['actual_duration_seconds']:.3f}秒（16分31秒）。予定991.100秒との差は約1ミリ秒。
- 映像：1920×1080、H.264、yuv420p、名目30fps、{m['planned_frames']}フレーム。最終フレーム総数は構成表と一致。
- 元素材の解像度は混在。1080p出力は元素材にない精細さの復元を意味しない。
- 音声：AAC 48kHzステレオ。区間単位の音量調整はloudnorm I=-18 / TP=-2 / LRA=11を指定。目標値であり、聴感の均一性を保証する測定結果ではない。
- ファイルサイズ：{size:,} bytes（約{size/1e6:.1f}MB）。
- 21区間：切り抜き16区間（冒頭抜粋・元の7本の再編集・追加原典4区間）と新規ナレーション5区間。
- 新規ナレーション合計：{sum(n['duration'] for n in g['narrations']):.3f}秒。各設定・文別API query・WAVを保存。

## 合格した検査

- FFprobeによる映像・音声ストリーム、解像度、フレーム数、尺の照合。
- FFmpeg `-xerror` を付けた全編デコード。エラーなし。
- 全21区間の開始2秒後から3秒間を、完成MP4と対応する元動画/WAVで音声波形照合。最小相関係数{min(x['normalized_correlation'] for x in q['audio_placement']):.4f}、最大時間差{max(abs(x['lag_seconds']) for x in q['audio_placement'])*1000:.3f}ミリ秒。別区間の音声混入や大きな配置ずれを検査するもので、全編リップシンクや聞き取りやすさを保証しない。
- 全切り抜きの代表フレームで上部の出典表示領域に描画があることを機械確認。
- 9画面の一覧と拡大フレームでナレーション字幕、見出し、出典表示の配置を目視確認。全文の各表示時点をすべて目視したわけではない。

## 手戻りと修正

- 子Agentの初稿を親がレビューし、映像と音声に同じ元動画IN/OUTを適用するよう修正してから書き出した。
- ナレーション字幕の不自然な文末折返しを見つけ、句読点を優先して改行を調整。
- MKVのミリ秒単位の時刻による平均fpsの微差を、名目fps・全フレーム数・総尺の検査と合わせて扱うよう検査条件を修正。
- 出典見出しが表示されない問題を実画像で発見。ASS字幕での描画へ切り替え、映像を再書き出しして再検査。

## 残る視聴確認

このセッションでは音声入力を利用できないため、声の抑揚、読みの自然さ、文間の間、音量の体感差、カット境界の聞こえ方、通し視聴での理解・テンポは未確認。API生成と波形照合を試聴済みとは扱わない。

生成した原WAVの16bitフルスケール到達サンプルは合計{sum(s['full_scale_samples'] for s in g['sentences'])}。その数だけで可聴歪みの有無は判定しない。元WAVを保存し、採用前の試聴で確認する。

## 制作配分・再編集

- 親Astra：原稿、API音声生成、構成仕様、子Agent初稿レビュー、修正、出力検査・画像確認。実行中の推論強度は確認できておらずMedium実行済みとは記録しない。
- 子Agent：Terra、Medium指定、1体、fork_turns="none"。書き出しスクリプト初稿のみ担当。目的・入出力・禁止変更・検査条件を明示して委任。親は並行して音声とカードを準備。
- 実使用トークン・料金・工程別の正確な所要時間は取得していない。生成manifestのgeneration_wall_secondsはキャッシュ再利用を含む直近の準備実行時間であり、初回合成全体の所要時間ではない。
- 再編集素材・音声設定・原稿・SRT/ASS・CSV/JSONを保持。新しいFilmora編集プロジェクトはこのコード試作では作成していない。
- チャンネル紹介は未確定のため未挿入。編集判断・原典の扱いは `EDIT_NOTES.md` を参照。
'''
(OUT/'test_report.md').write_text(report,encoding='utf-8')
print(f'FINALIZED {size:,} bytes',flush=True)
