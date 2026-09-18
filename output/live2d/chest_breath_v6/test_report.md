# リサ — 外形を保って喉の内部の皺を中央へ寄せるv6

2026-09-16。Bossはv5の腹部を「良い感じ」と評価し、喉元は上下移動よりも吸気時に中心方向へ皺を寄せる案を提示した。腹部はv5を維持し、喉の内部の皺と胸の膨らみのつながりを比較する候補を作成。喉元の新しい動きの採用・自然さはBossの視聴待ち。

## 成果物

- [喉〜胸部を拡大した左右比較・約8秒／無音](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Throat_Folds_Compare_v5_v6.mp4)：左A=v5の上下移動、右B=v6の中央寄せ。1920×1040/30fps/241フレーム。同一の呼吸曲線・フレーム・拡大倍率。
- [v6単独・呼吸のみ約8秒](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v6.mp4)：1080×1080/30fps/241フレーム、無音。
- [v6単独・既存ナレーション付き約16秒](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v6.mp4)：1080×1080/30fps/479フレーム。
- [編集用cmo3](Risa_chest_breath.cmo3)、SDK用 `Risa_chest_breath.model3.json` / `.moc3` / `.2048/texture_00.png`、演技付き `Risa_chest_performance.model3.json`。

v5を複製しCubism 5.3.04 FREEで編集、SDK 5.0向けに書き出し。既存版・Filmora・全編動画は保持。原画テクスチャは同一で、画像生成や描き替えを行っていない。

## 調整内容

Body_ClothesのParamBreath=1で、喉元の3頂点を変更。75%表示時の実際の操作座標。画面上の座標であり、モデル内座標や動画内の移動量ではない。

| 部位 | v5 → v6 | v3からの追加変形 |
| --- | --- | --- |
| 襟内部中央 | (1074,187) → (1074,191) | 上下移動を解除し元の位置へ |
| 胸骨上部寄り・内部左 | (1052,229) → (1057,231) | 上下移動を解除、中央へ3px |
| 胸骨上部寄り・内部右 | (1114,225) → (1109,227) | 上下移動を解除、中央へ3px |

襟上端・外周の頂点を動かさず、左右の内部頂点の間隔を狭めることで既存の横皺の間隔と湾曲を変える。中央・上側の固定点へ補間され、上端を引き上げずに襟内部が張って戻る。呼気で元の原画形状へ戻る。腹部の3頂点、胸・肩の8×9デフォーマ、首・口・目、呼吸曲線はv5を維持。

## 検証

`calibration_verification.json`：v3との同一入力比較（呼吸0/0.3/0.6/1、最大呼吸＋口0.958・すぼめ-0.55・首±8.4）。中立姿勢はv3と一致し、呼吸だけを変えた顔の画素差0。襟上端の移動0px、衣服内部の透過穴は6姿勢で0。

`local_motion_verification.json`：1080px描画倍率、最大吸気での局所テンプレート推定。

| 対象 | 結果 |
| --- | --- |
| 内部の皺・左 | 中央へ約2px、上下0px |
| 内部の皺・右 | 中央へ約2px、上下0px |
| 喉の中央領域の上下移動 | 0px（v5は上へ約4px） |
| 腹部のv5との画素差 | 0 |
| 上部ニット領域外のv5との画素差 | 0 |
| 外形マスクの変化 | アルファ閾値1/127/240のすべてで0画素 |
| 肩の上昇 | 左右各16px、既存設定を維持 |
| 胸の白い生地の横幅 | 269→282px、既存設定を維持 |

最初にアルファ値の完全一致を検査し、最大差1で不合格となった。調べると変化は内部の27画素、座標(414,462)〜(476,522)、アルファ252〜255の間の1段階だけだった。外周の位置変化ではなく、内部テクスチャの補間差だったため、アルファ差1以下に加え、3つの閾値で外形マスクの完全一致を検査する形へ修正して合格。輪郭移動や透過穴を許容したものではない。

変位は模様の局所照合による推定で、奥行きの物理計測ではない。呼吸のみ動画は0.15〜0.85、ナレーションは最大約0.594の呼吸値で、上記の最大域より実振幅は小さい。比較動画は元の1080×1080画像から(270,310)〜(810,850)の同じ領域を切り出し、左右それぞれ960×960へ拡大する。喉と胸のつながりを見やすくするための表示変更で、動き自体の増幅ではない。

動画検査は `verification.json`、SDK値照合は `render_verification.json`、左右比較検査は `comparison_verification.json`、成果物ハッシュは `manifest.json`。3つのMP4とも全フレームデコードと指定寸法・フレーム数の検査に合格。比較版の左右4時点の参照照合は最大平均画素誤差2.726/255で、同一時刻・同一倍率を確認。呼吸曲線のハッシュもv5と一致した。音声相関0.9999816、相関ピークのずれ0ms。呼吸のみの上下ニットに時間変化があり、ループ始終の平均画素差0.222/255。最大吸気画像、呼吸シーケンス、拡大比較画像を目視し、喉元・胸部のつながりと左右の配置を確認した。技術検査と自然さの最終通し視聴評価は分ける。

## 再生成

cmo3変更後はCubismからSDKモデルをこのフォルダーへ出力する。プロジェクトルートで実行する。

```powershell
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v6/build_preview.py --calibrate
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v6/measure_local_motion.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v6/build_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v6/verify_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v6/build_comparison.py
```

再検証にはv3のSDKモデル、v5の較正PNG・呼吸のみMP4・参照PNG・motion3も必要。演技入力は `../narration_adjustment_v1/`。親AstraがGUI・コード・検証を担当、子Agent0、forkなし。推論強度の実効値・契約使用量・所要時間は未計測。PRO試用は開始していない。
