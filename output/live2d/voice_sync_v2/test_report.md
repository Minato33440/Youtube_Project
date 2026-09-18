# Risa 発音に合わせた口開閉 v2

2026-09-14。Bossの「口の開閉に関して発音に対する自然さを詰める」という依頼に対し、約16秒のナレーションの駆動曲線を改訂した。v1を保持し、v2として別保存。原画・Cubism編集モデル・ナレーション音声は変更していない。

## 確認する映像

- `Risa_lipsync_closeup.mp4`：修正版の拡大表示。
- `Risa_narration_composite.mp4`：元動画へ同じ位置・サイズで重ねた修正版。
- `Risa_lipsync_comparison.mp4`：左v1（音量連動）、右v2（発音位置に基づく開閉）。音声は共通。

すべて1280×720、30fps、478フレーム、15.933333秒。修正内容はCSV/JSON/Motion3、透過連番PNG、合成設定と再現スクリプトに保持。再生モデルは `model/Risa_compat.model3.json`。編集元cmo3は `../voice_sync_v1/Risa_voice_test.cmo3` を参照する。今回の動きはCSVを実モデルへ適用して描画しており、cmo3にナレーション固有のモーションが埋め込まれたわけではない。

## 改善内容

1. 原4文の読みと実音声を、JuliusのPTM音響モデルで強制アラインメント。207音素・休止区間を取得。元のAivisSpeech JSONは音素長が0のため、時刻として流用していない。
2. 母音の目標開口量を「あ=.80、え=.64、お=.59、い=.43、う=.38」とし、音量は音素ごとの微調整に使用。これは現在の単一開閉リグに合わせた制作上の設定であり、五母音の口形を生成したものではない。
3. この音声に現れる3か所のmで閉口を明示。8.10秒の「ま」、14.80秒の「み」、15.20秒の「ま」で、v1の開口値約.642/.846/.694から0に修正。
4. 音素遷移を14msの中心化平滑化でつなぎ、20msの視覚的な先行を設定。1フレーム当たりの変化を最大.34に抑制。長い母音を音量だけで細かく上下させず、子音すべてを一律に完全閉口させない。
5. 40ms以上続く実測無音（10ms窓RMS<.001）は、推定音素より優先して閉口させる。特に「さんは」後の原稿にない休止を反映。文末で口が開いたまま残る時間を短縮。
6. 元クリップの約15.86秒の短い別音は、引き続き口パクの対象外。動画・WAV音声には手を加えていない。

## 時刻と推定の検査

初回のJulius既定設定ではゼロサンプル除去により時間軸が短くなる問題を検出。最終版では `-nostrip` を使い、入力16kHz WAVと処理サンプル数の一致を全4文で確認した（44988、90921、86449、27257）。旧結果は `alignment/initial_stripped` に保存。

原N01連結から提供クリップへのオフセットは+0.000726秒。音素推定の時間分解能は10ms。モノフォンモデルで「さんは」のa/Nに無音が吸収されたため、PTMモデルとの比較と、実測に基づく休止の追加で改善した。最終結果に300ms超の母音・非休止音素はない。

推定音素と低エネルギー区間が重なる箇所15件は `alignment/quality_report.json` に明示し、口開閉側では音声の無音ゲートを優先した。音素時刻は自動推定であり、手作業で確定した正解ラベルではない。

## 検証結果

- 3本のMP4を全編デコードし、エラーなし。478フレーム、映像と音声の開始時刻一致。
- 抽出WAVは元クリップを同条件でデコードしたPCMと完全一致。再圧縮されたMP4音声も元音声とのオフセット0での相関0.99998以上。
- 全478枚のPNGを検査し、口元以外の画素は固定。指定したmの閉口、曲線0時の閉口、末尾の閉口を確認。
- 実際に描画された口元の変化と曲線の対応は、前後3フレーム内で遅延0が最も高い相関。フレーム間変化は最大.34。
- 曲線全4文、比較映像の「み」の閉口フレーム、合成映像の無音時フレームを目視確認。`curve_review.png` と `comparison_preview.png` を保持。

上記は波形・発音推定・描画結果による調整と検査。人が音声付きで通し視聴した自然さの評価は実施していない。今回は既存の開閉パラメーターだけを調整しており、唇の横幅・丸め、顎連動は未追加。まばたき・首・呼吸は前回と同様に固定。Motion3ファイルの別アプリへの読み込みも未検証。

## 再現

プロジェクトルートで実行。最初のコマンドは音素推定を再実行する場合だけ必要。

```powershell
& 'output/live2d/runtime_venv/Scripts/python.exe' 'output/live2d/alignment_tools/run_julius_forced_alignment.py'
& 'output/live2d/runtime_venv/Scripts/python.exe' 'output/live2d/voice_sync_v2/refine_mouth_curve.py'
& 'output/live2d/runtime_venv/Scripts/python.exe' 'output/live2d/voice_sync_v2/render_model.py'
& 'output/live2d/runtime_venv/Scripts/python.exe' 'output/live2d/voice_sync_v2/compose_video.py'
& 'output/live2d/runtime_venv/Scripts/python.exe' 'output/live2d/voice_sync_v2/verify_outputs.py'
& 'output/live2d/runtime_venv/Scripts/python.exe' 'output/live2d/voice_sync_v2/plot_curve_review.py'
```

親：開口設計・時間軸の問題検出・曲線調整・描画・合成・検査。子Agent 1名：Terra/Medium指定、forkなしで独立した音素アラインメントを担当。親のモデル・推論強度の実効値、契約枠使用量、工程別の厳密な所要時間は未計測。主な手戻りはゼロサンプル除去と休止の誤吸収を修正したこと。既存品質を下げるためのモデル変更ではない。

参照：[Julius公式セグメンテーションキット](https://github.com/julius-speech/segmentation-kit)。
