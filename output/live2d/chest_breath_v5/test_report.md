# リサ — ニットの上下方向だけを反転した比較候補v5

2026-09-16。Bossの依頼「先ずは比較用の上下方向反転版のSample」を実装。吸気時、v4の首元下向き・腹部上向きを、首元上向き・腹部下向きへ反転。方向の比較段階であり、採用や自然さの最終評価は未確定。

## 成果物

- [左右同時比較・無音約8秒](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Breath_Direction_Compare_v4_v5.mp4)：左A=v4、右B=v5。同じ倍率・フレーム・呼吸曲線、1920×1040/30fps/241フレーム。
- [反転版単独・呼吸のみ約8秒](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v5.mp4)：1080×1080/30fps/241フレーム、無音。
- [反転版単独・既存ナレーション約16秒](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v5.mp4)：1080×1080/30fps/479フレーム。
- [編集用Cubismモデル](Risa_chest_breath.cmo3)、SDK用 `Risa_chest_breath.model3.json` / `.moc3` / `.2048/texture_00.png`。演技付きは `Risa_chest_performance.model3.json`。

元のv4を複製してCubism 5.3.04 FREEで編集し、SDK 5.0向けに出力した。原画テクスチャはv4とSHA-256一致。既存v4、Filmora、全編動画は変更していない。

## 変更した頂点

Body_ClothesのParamBreath=1の6頂点のみを操作。75%表示、v4の位置から以下の位置へ移動した。v3を基準に追加したv4の上下変位を反転するため、v4からの操作距離は元の上下変位の2倍となる。左右座標は同じ。ParamBreath=0、親デフォーマ、胸・肩の動きは維持。

| 部位 | v4 → v5（エディター上の座標） |
| --- | --- |
| 腹部中央 | (1078,433) → (1078,441) |
| 腹部左 | (1022,436) → (1022,442) |
| 腹部右 | (1133,432) → (1133,438) |
| 襟内部中央 | (1074,195) → (1074,187) |
| 胸骨上部左 | (1052,233) → (1052,229) |
| 胸骨上部右 | (1114,229) → (1114,225) |

左右への広がりや皺の湾曲の追加調整は行っていない。呼吸のみの曲線はv4とファイルハッシュ一致。ナレーションの6軸CSV・WAVも元の入力と同一。比較のため、呼吸の強さ・周期・表示倍率を固定した。

## 検証と限界

`calibration_verification.json`：呼吸0/0.3/0.6/1、最大呼吸＋口0.958・すぼめ-0.55・首±8.4の6姿勢。中立姿勢はv3と一致。顔は呼吸値を変えても画素差0、襟上端は移動0px、ベルト以下のv3との差0。衣服内部の透過穴は6姿勢すべて0。

`local_motion_verification.json`：最大域でのテンプレート推定は、首元v4下4px→v5上4px、腹部v4上3px→v5下4px。画素単位の推定なので、操作量が同じでも変形・補間・模様により1px程度の差が出る。左右変位のテンプレート値も生地全体の平行移動を意味しない。変更した6頂点の左右座標は保持した。ニットの2領域外ではv4/v5の最大画素差0。肩各16px・胸の白い生地の横幅269→282pxはv4と同じ。

これらは最大呼吸値1での検査。呼吸のみサンプルは0.15〜0.85、ナレーションは最大約0.594なので、動画中の実振幅は小さい。物理的な奥行きを測ったものではなく、既存原画の皺の変形による見え方の比較。

動画は `verify_preview.py`、左右比較は `build_comparison.py` で検査合格。全フレームデコード・寸法・フレーム数・代表フレームの参照画像照合を通過した。音声相関0.9999816、相関ピークのずれ0ms。SDK最大誤差0.001247未満。左右比較の参照画素誤差は最大2.191/255、呼吸曲線のハッシュ一致。結果は `verification.json` / `render_verification.json` / `comparison_verification.json`、ハッシュは `manifest.json` に保持した。最大吸気画像、比較画像、呼吸シーケンス画像を目視し、襟・ニット・ベルトのつながりと左右比較の配置を確認した。自然さの通し視聴・採用判断はBossの確認待ち。

## 再生成

cmo3を変更した場合は先にCubismからこのフォルダーへSDK出力する。プロジェクトルートで実行する。

```powershell
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v5/build_preview.py --calibrate
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v5/measure_local_motion.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v5/build_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v5/verify_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v5/build_comparison.py
```

比較検査はv4の `calibration/after_3.png`、`breath_only.motion3.json`、`breath_only/`の参照PNG、およびv4の呼吸のみMP4も参照する。

親AstraがGUI・スクリプト・検証を担当。推論強度実効値は未確認。子Agent0、forkなし。所要時間・契約使用量未計測。PRO試用は開始していない。
