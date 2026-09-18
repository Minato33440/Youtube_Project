# リサ — タートルネック上部の皺を追加調整したv8

2026-09-16。Bossはv7で「大分動きは出てきてる」と評価し、タートルネック上部の皺だけ追加するよう依頼。v7のコピーをCubism 5.3.04 FREEで編集し、上部内部の折れ目の曲がり方に呼吸変形を追加した。v8の自然さ・視認性はBossの視聴待ち。

## 成果物

- [v7/v8拡大比較・約8秒](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Throat_Folds_Compare_v7_v8.mp4)：左A=v7、右B=v8。同じ呼吸曲線・時刻・倍率、1920×1040、30fps、無音。
- [v8単独・呼吸のみ約8秒](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v8.mp4)：1080×1080、30fps、241フレーム。
- [v8単独・既存音声付き約16秒](../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v8.mp4)：1080×1080、30fps、479フレーム。
- [編集用cmo3](Risa_chest_breath.cmo3)、SDKモデル、演技付き `Risa_chest_performance.model3.json`、モーション、入力音声、CSV、ハッシュ `manifest.json`。

## 調整と確認

Body_ClothesのParamBreath=1で、上部内部の1頂点を75%表示時(1074,191)→(1080,191)へ移動。左寄りの折れ目を襟の中央方向へ寄せ、曲がり方を変える。上下座標は同じ。前回の下襟の左右2頂点、胸・肩の局所デフォーマ、腹部3頂点、演技の時系列は保持した。原画の描き替えは行っていない。

`calibration_verification.json` と `local_motion_verification.json` の検査結果：

- 呼吸0/0.3/0.6/1と最大呼吸＋口・首±8.4の6姿勢で透過穴0。顔の呼吸による画素差0。
- 襟上端の推定移動0px。v7/v8のアルファ差0、外形マスク3閾値で差0。
- v7との変更は内部領域x280:480/y380:510に収まり、領域外の最大画素差0。胸・肩・腹部を含むy510以降の差0。
- 上部の皺の局所照合は最大吸気で横約6px・縦約-1px。模様の変形に対する近似照合で、上下頂点を追加移動した値ではない。
- 肩の最大上昇は左右各16px、胸の白い生地の横幅269→282pxで前回と同じ。
- 原画テクスチャSHA256は `4ED9B44B7BCEEF663FC66E01377BBAE015716D887397F13C9C374362ED90D2F4` で前回と一致。

上記の移動量はParamBreath 0〜1での較正。呼吸のみ動画は0.15〜0.85、ナレーションは最大約0.594で、実際の振幅は小さい。技術検査と人間による通し視聴の判定を区別する。動画検査は `verification.json`、SDK値照合は `render_verification.json`、比較動画検査は `comparison_verification.json`。

## 再生成

3本のMP4は全フレームデコード、寸法、30fps、フレーム数の検査に合格。比較動画は左右4時点の同時刻PNGと照合し、平均画素誤差は最大2.729/255未満。呼吸曲線はv7とハッシュ一致。音声相関0.9999816、相関ピークのずれ0ms。呼吸ループの始終差0.230/255。最大吸気画像・6時点の呼吸シーケンス・拡大比較画像を目視し、襟外形や首元に明らかな破綻は見られなかった。最終的な動きの自然さは通し視聴で判断する。

ネイティブ変更後はSDK 5.0向けモデルを同じフォルダーに出力する。プロジェクトルートから順に実行：

```powershell
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v8/build_preview.py --calibrate
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v8/measure_local_motion.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v8/build_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v8/verify_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v8/build_comparison.py
```

v3のSDK、v7の較正PNG・呼吸MP4・参照PNG・motion3、`../narration_adjustment_v1/` の演技入力を必要とする。親AstraがGUI・コード・検証を担当、子Agent0、forkなし。実効推論強度・契約使用量・所要時間は未計測。既存版、Filmora、全編動画は保持。PRO試用は開始していない。
