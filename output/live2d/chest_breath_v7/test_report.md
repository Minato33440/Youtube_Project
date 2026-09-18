# リサ — 喉の内部の皺を強めた呼吸v7

2026-09-16。Bossはv6を「ほとんど動いていない感じ」と評価。中央へ寄せる方向を維持し、喉元の内部の変形量を増やした比較候補。v5で評価された腹部の動きは継続する。v7の視認性・自然さはBossの視聴待ち。

## 成果物

- [喉〜胸部のv6/v7左右比較・約8秒／無音](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Throat_Folds_Compare_v6_v7.mp4)：左A=v6、右B=v7。1920×1040、30fps、241フレーム。
- [v7単独・呼吸のみ約8秒](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v7.mp4)：1080×1080、30fps、241フレーム。
- [v7単独・既存音声付き約16秒](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v7.mp4)：1080×1080、30fps、479フレーム。
- [編集用cmo3](Risa_chest_breath.cmo3)、SDK用 `Risa_chest_breath.model3.json` / `.moc3` / `.2048/texture_00.png`、演技付き `Risa_chest_performance.model3.json`。

v6を複製しCubism 5.3.04 FREEで編集、SDK 5.0向けに出力。原画テクスチャのSHA256は既存版と同一：`4ED9B44B7BCEEF663FC66E01377BBAE015716D887397F13C9C374362ED90D2F4`。既存版・Filmora・全編動画を保持した。

## 変更

Body_ClothesのParamBreath=1で、左右2つの内部頂点をさらに中央へ動かした。75%表示時の操作座標は左(1057,231)→(1063,231)、右(1109,227)→(1103,227)。v3から加えた横方向のキー変位は各3pxから9px、約3倍。これは編集画面上の値であり、動画全域の移動が一律3倍という意味ではない。

上下座標・内部中央・襟上端・外周を保持。胸・肩の局所デフォーマ、腹部の3頂点、口・目・首・呼吸の時系列は維持。原画の皺を左右から寄せ、下襟から胸骨上部にかけて曲線の変化を強めた。

## 検証

`calibration_verification.json`：呼吸0/0.3/0.6/1、および最大呼吸＋口0.958・すぼめ-0.55・首±8.4の6姿勢。中立姿勢はv3と同じ。呼吸のみで顔の画素差0、襟上端の推定移動0px、衣服内部の新しい透過穴0。

`local_motion_verification.json`：同じ1080px描画倍率で最大吸気をv3と比較した局所模様照合。

| 対象 | v6 | v7 |
| --- | --- | --- |
| 内部の皺・左の中央方向への推定変位 | 約2px | 約9px |
| 内部の皺・右の中央方向への推定変位 | 約2px | 約7px |
| 腹部のv6との画素差 | — | 0 |
| 上部ニット領域外のv6との画素差 | — | 0 |
| 外形マスク変化（アルファ閾値1/127/240） | — | 全て0画素 |
| 肩の最大上昇 | 左右各16px | 左右各16px |
| 胸の白い生地の横幅 | 269→282px | 269→282px |

左右の内部模様の推定上下変位は1px/0px。広い中央領域では上へ1pxという最良照合になるが、頂点の上下座標を追加変更したものではない。模様の変形から得る近似的な照合結果であり、物理的な移動量や奥行きではない。アルファ値の最大差は内部補間による1段階、外形マスクは3閾値とも同一。

呼吸のみはParamBreath 0.15〜0.85、ナレーションは最大約0.594で、最大域検査より実際の振幅は小さい。比較は同じ曲線・時刻・倍率で喉〜胸部を拡大している。

動画検証の結果は `verification.json` / `render_verification.json` / `comparison_verification.json`、ハッシュは `manifest.json` を参照。技術検査・代表画像の確認と、Bossによる自然さの通し視聴評価を区別する。

3本とも指定寸法・フレーム数・全フレームデコード検査に合格。音声相関0.9999816、相関ピークのずれ0ms。比較版は左右4時点を参照PNGと照合し、平均画素誤差は最大2.726/255以下。v6/v7の呼吸曲線ハッシュは同一。呼吸のみのループ始終の平均画素差0.226/255。最大吸気PNG、6時点の呼吸シーケンス、左右の拡大比較画像を目視確認し、明らかな襟・首元の破綻は認めなかった。全編の人間による通し視聴の代わりとは扱わない。

## 再生成

ネイティブモデルを変更した場合はCubismでSDKモデルを同フォルダーに書き出す。プロジェクトルートから実行する。

```powershell
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v7/build_preview.py --calibrate
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v7/measure_local_motion.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v7/build_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v7/verify_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v7/build_comparison.py
```

v3のSDKモデル、v6の較正PNG・呼吸MP4・参照PNG・motion3を必要とする。演技入力は `../narration_adjustment_v1/`。親AstraがGUI・コード・検証を担当。子Agent0、forkなし。推論強度の実効値・契約使用量・所要時間は未計測。PRO試用は開始していない。
