# リサ — 胸部・肩の呼吸を強めたモデル単独サンプル v2

2026-09-16。Bossがv1を通し確認し「胸部の動きも肩の動きもほとんど分からない」と評価したため、ネイティブの変形量を再調整した候補。v1と既存のFilmora・全編MP4は保持。

## 成果物と入力

- `Risa_chest_breath.cmo3` — Cubism編集用。v1のコピーをCubism 5.3.04 FREEで編集。
- `Risa_chest_breath.moc3` / `.model3.json` / `.cdi3.json` / `.2048/texture_00.png` — SDK 5.0出力。
- `Risa_chest_performance.model3.json` / `performance.motion3.json` / `breath_only.motion3.json` — 再生用設定と動作。
- `../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v2.mp4` — モデル単独・音声付き、1080×1080 / 30fps / 479フレーム、約16秒。
- `../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v2.mp4` — モデル単独・呼吸のみ・無音、1080×1080 / 30fps / 241フレーム、約8秒。

ナレーション、口・首・目・呼吸の6軸CSVは前回と同一。呼吸の速さや休止位置を変えず、同じParamBreathに対するモデルの変形量を増やした。呼吸のみ版は従来どおり0.15〜0.85、4秒周期×2。背景・表示サイズもv1と同一。

## リグの調整

`Chest_Breath`（Warp4、親Breath_Base、子Body_Clothes）のParamBreath=1キーを編集した。0キーは保持。顔・髪・腕・別レイヤーTurtleneckは同じデフォーマの子に追加していない。

38.4%表示時に、上から2段目の中央を(1084,352)→(1084,313)、左を(1021,354)→(1007,319)、右を(1147,354)→(1161,319)へ変更。上端の肩側を左(1024,267)→(1022,237)、右(1144,267)→(1146,237)へ変更。上端中央・腰以下の制御点は編集していない。座標はGUI操作の概略で、出力映像の移動量とは異なる。

これにより胸元の持ち上がり・横幅の変化と、肩の輪郭の上昇を増やした。Body_Clothes全体に補間されるので、襟を含む衣服の一部も追従する。全身を別途映像加工して揺らす処理は追加していない。

## 動きの量と形状の検証

`calibration_verification.json`はv1とv2を同じパラメーターで比較。呼吸0/0.3/0.6/1、および最大呼吸＋口0.958＋すぼめ-0.55＋首±8.4の6姿勢を確認。呼吸0は新旧一致。全6姿勢で顔の上部領域y<340は同一。衣服の上昇がy347から始まるため、従来のy360までの顔検査領域は今回に限り襟を含まないy340に限定した。顔全パーツの個別頂点検査ではない。

旧リグの不透明領域を21px侵食した範囲で、新しい透過の穴は0。輪郭近傍の全姿勢を保証する検査ではない。比較静止フレームで襟・肩・胸部を目視した。

`amplitude_comparison.json`はParamBreath=0→1の最大可動域を、1080pxサンプルと同じ描画倍率で計測する。左右肩は髪の外側のアルファ輪郭の中央値、胸部は布地・ブローチのテンプレート照合による推定。

| 計測対象 | v1 | v2 |
| --- | ---: | ---: |
| 画面左肩の上昇 | 4px | 19px |
| 画面右肩の上昇 | 5px | 20.5px |
| ブローチの上昇（推定） | 3px | 16px |
| 胸中央の布地の上昇（推定） | 2px | 14px |

これらは最大可動域であり、ナレーション中の呼吸は最大約0.594なので常にこの量が動くわけではない。呼吸のみ版の0.15〜0.85も最大域より小さい。倍率の単純な主張ではなく、部位ごとの変位として残す。

最初のv2候補は肩10〜11.5pxにとどまり、3倍以上という今回の検査目安に届かなかったため、書き出し前に再度増量した。最終版で肩の3倍以上の検査を通過。画像処理パッケージの追加インストールは行っていない。

動画の最終検査結果は`verification.json`で合格。2本とも全フレームデコード、1080×1080・30fps・指定フレーム数、代表各7フレームの照合、胸部の時間差分を確認。音声付き版は元音声と相関0.999982、相関ピークのずれ0ms。SDK実再生の最大誤差は0.001247未満（許容0.003）、`render_verification.json`に保存。入力・出力ハッシュは`manifest.json`。v1とv2のテクスチャSHA-256は一致した。

`preview.jpg`と`breath_sequence_review.jpg`の抽出フレームで、モデル単独の表示・胸部と肩の変化・襟のつながりを確認。技術検査とBossによる自然さ・強度の受入は分ける。親の視覚確認は抽出フレームであり、通し視聴の代替とはしない。

## 再生成

プロジェクトルートで以下を実行。cmo3を編集した場合は先にCubismでmoc3を再出力する。

```powershell
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v2/build_preview.py --calibrate
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v2/measure_amplitude.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v2/build_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v2/verify_preview.py
```

親AstraがGUI・コード・検証を担当。推論強度の実効値は未確認。子Agent0、forkなし。試作1回を増量し直した。総時間・契約使用量は未計測。PRO試用の開始、原画の生成、Filmora変更、全編への反映は行っていない。
