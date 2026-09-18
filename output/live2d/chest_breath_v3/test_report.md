# リサ — 首元を固定した胸部・肩の局所呼吸 v3

2026-09-16。Bossのv2試聴評価「体幹上部全体が上下に動いており頸部の上下動きが不自然」を受け、胸の膨らみと肩の動きに集約した候補。自然さの最終受入はBossの試聴待ち。

## 変更内容と保存先

- 編集用: `Risa_chest_breath.cmo3`。既存v4の `../voice_sync_v4/Risa_coordinated.cmo3` から別名コピーを作り、Cubism 5.3.04 FREEで編集。
- SDK 5.0出力: `Risa_chest_breath.moc3`、`.model3.json`、`.cdi3.json`、`.2048/texture_00.png`。
- 再生用: `Risa_chest_performance.model3.json`、`performance.motion3.json`、`breath_only.motion3.json`。
- モデル単独・音声付き: `../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v3.mp4`（1080×1080、30fps、479フレーム、約16秒）。
- モデル単独・呼吸のみ: `../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v3.mp4`（1080×1080、30fps、241フレーム、約8秒、無音）。

口・目・首・呼吸の6軸の時系列と音声は、受入済み `../narration_adjustment_v1/` のCSV/WAVをそのまま使用。首の傾き演技は保持し、呼吸による全体の伸縮だけを停止した。Filmora・全編動画への反映は今回の対象外。

## ネイティブリグ

`Breath_Base` の吸気キーの拡大率を100.6%から100%へ変更。新しい `Chest_Local_Breath`（Warp4）はその子、`Body_Clothes`だけを配下に持つ。変換とベジェの分割はともに8×9、ParamBreathは0/1の2キー。計6デフォーマ。

吸気時、肩の外側の制御点を6〜7エディター画素上げ、胸部の左右を水平方向へ各6画素、下胸部を各4画素広げた。胸部中央の上下移動、首・襟中央の制御点、腰以下の制御点は加えていない。38.4%表示時の操作座標は、肩(994,319)→(994,313)、(1024,319)→(1024,312)、(1144,319)→(1144,312)、(1174,319)→(1174,313)。胸(1054,369)→(1048,369)、(1114,369)→(1120,369)。下胸部(1054,420)→(1050,420)、(1114,420)→(1118,420)。これらは再構築の参考値であり、映像の移動量ではない。

衣服の旧メッシュは局所変形を表現するには粗く、細かいデフォーマだけを追加した最初の候補では、襟と胸中央が約2px上がり肩も2pxしか動かなかった。ParamBreath=0でBody_Clothesを選択し、自動メッシュの「変形度合い（大）」を適用して再構成。設定は内外点間隔25、外マージン3、内マージン2、最小マージン2、最小点数5、透過アルファ0。メッシュ密度とデフォーマ密度をセットで見直す必要があった。

8×12のグリッドはFREE版の変換分割上限9×9を超えて作成できず、8×9へ修正した。PRO試用は開始していない。

## 検証と失敗境界

`calibration_verification.json` は呼吸0/0.3/0.6/1と、最大呼吸＋口0.958・すぼめ-0.55・首±8.4の姿勢を描画。v2との同じ入力での画像差分は参考記録であり、合否判定はv3内で呼吸だけを変えた比較を使う。全体伸縮を止めたため、v2と顔の画素が一致するという旧検査は今回には適用しない。

`local_motion_verification.json` の最大可動域（呼吸0→1、1080pxサンプル倍率）の結果:

| 対象 | v3の計測結果 |
| --- | ---: |
| 襟中央の上下・左右移動（テンプレート推定） | 0px / 0px |
| 胸中央の上下移動（テンプレート推定） | 0px |
| 左右肩の上昇（不透明輪郭の中央値） | 各16px |
| 胸位置の白い生地の横幅（行600〜650の中央値） | 269→282px |
| 顔上部の画素差（呼吸だけを変更） | 0 |
| 中央襟領域の平均画素差（最大吸気） | 約0.017 / 255 |
| 衣服内部に新しくできた透過の穴 | 全6姿勢で0 |

肩16pxは最大域であり、ナレーションの呼吸値は最大約0.594、呼吸のみ版は0.15〜0.85。全時間帯で16px動くわけではない。テンプレート照合と色境界は局所変化の推定であり、胸の奥行きの物理計測ではない。透過検査は中立姿勢の輪郭を31px侵食した領域のうちy>=350が対象で、動く輪郭近傍まで保証しない。

最初の粗いメッシュで襟の固定検査が失敗した後、メッシュを再構成して同じ検査を通過した。旧v2との透過差16画素は、上げ過ぎていた輪郭を戻したことを含むため、v3自身の中立姿勢からの内部穴検査と区別する。旧版比較の差分欄だけを合否と誤読しない。

動画の機械検査は `verification.json` で合格。両MP4の全フレームデコード、1080×1080/30fps/指定フレーム数、各7フレームの描画参照との照合、胸部の時間変化を確認。音声相関0.9999816、相関ピークのずれ0ms。SDK実再生の最大パラメーター誤差0.001247未満（許容0.003）、`render_verification.json` に保存。入力・成果物ハッシュは `manifest.json`。テクスチャのSHA-256はv2と同一。`preview.jpg`、`breath_sequence_review.jpg` と最大吸気の透過画像で首・襟・肩・胸のつながりを目視した。自然さの通し試聴による最終判断はBossへ委ねる。

## 再生成

cmo3を変更した場合は先にCubismでmoc3を再出力する。プロジェクトルートで以下を実行する。

```powershell
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v3/build_preview.py --calibrate
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v3/measure_local_motion.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v3/build_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v3/verify_preview.py
```

親AstraがGUI、コード、検証を担当。推論強度の実効値は未確認。子Agent0、forkなし。メッシュ修正前に1候補が襟固定検査で失敗し、修正後に再検査した。所要時間・契約使用量は未計測。既存v1/v2、原画、Filmoraプロジェクトは保持。
