# リサ — 胸部呼吸リグとモデル単独サンプル v1

2026-09-16。Bossが前段の配置・顔から首の動きを「概ね良くなった」と評価した後、呼吸による胸部の動きを追加した比較候補。旧モデル、原画、前回の動画、Filmoraプロジェクトは保持している。

## 成果物

- `../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v1.mp4` — 1080×1080 / 30fps / 479フレーム / 15.966667秒。モデル単独・無地背景、N01のナレーション音声付き。
- `../../../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v1.mp4` — 1080×1080 / 30fps / 241フレーム / 8.033333秒。口・首の強調・まばたきを止め、呼吸だけを確認する無音版。0.15〜0.85のParamBreathを4秒周期で2回。最後の1フレームはループ終端比較用。
- `Risa_chest_breath.cmo3` — 胸部呼吸を追加したCubism編集用モデル。
- `Risa_chest_breath.moc3` / `Risa_chest_breath.model3.json` / `Risa_chest_breath.2048/texture_00.png` — 新しいリグのSDK書き出し。
- `Risa_chest_performance.model3.json` — `Performance` と `BreathOnly` モーションを登録した再生用設定。対応するmotion3とN01.wavは同じフォルダー内に保持。

## ネイティブリグの変更

Cubism Editor 5.3.04 FREEで `voice_sync_v4/Risa_coordinated.cmo3` のコピーを編集した。PROトライアルは開始していない。

1. `Body_Clothes` の親にワープデフォーマ `Chest_Breath`（ID `Warp4`）を追加。親は既存の `Breath_Base`。腕・顔・首・別レイヤーのTurtleneckを新デフォーマの子にはしていない。
2. 変換の分割5×5、ベジェの分割4×5。標準パラメーター `ParamBreath` の0と1にキーを追加。
3. 0は元の形状。1で上から2段目の胸部制御点を持ち上げ、左右を少し広げた。38.4％表示時の操作量は、左から順に概ね(-1,-2),(-3,-5),(0,-7),(+3,-5),(+1,-2) px。これはGUI操作量であり、実行モデルのピクセル変位や物理単位ではない。
4. 襟に近い上端と腰以下の制御点は動かしていない。胸の上昇・横方向の広がりを衣服と肩側へ緩やかにつなぐ。既存 `Breath_Base` の微小な全体伸縮は保持している。
5. cmo3を保存、SDK 5.0形式で書き出し、cmo3を閉じて再読込。胸部デフォーマの保持を確認した。

新しい原画・テクスチャは生成していない。新旧テクスチャのSHA-256は一致。

## 演技データ

音声付きサンプルの `performance_curve.csv` は、直前にBossが確認した `narration_adjustment_v1` とSHA-256まで一致する。口の開閉1.2倍、首2倍、すぼめ55％を含む6軸すべての値・時刻を保持した。胸部の動きは新しいリグが同じ `ParamBreath` に応答することで追加される。

別途、動きを切り分けて確認できる `breath_only.motion3.json` を作成した。呼吸のみ版は本編の発話時刻に対応する演技ではなく、形状確認用の周期運動。

## 検証

- 旧リグと新リグを同じパラメーター値で描画し、呼吸0 / 0.3 / 0.6 / 1、さらに呼吸1＋口開閉0.958＋すぼめ-0.55＋首±8.4の6姿勢を比較。
- 呼吸0の中立画像は新旧で一致。全6姿勢で襟より上の顔領域（クロップ画像y<360）の最大ピクセル差0。胸部では変化を検出。
- 旧リグのアルファを21pxの最小値フィルタで内側へ絞った領域に、新しい透過の穴は検出されなかった。輪郭付近や全ての任意姿勢の保証ではない。
- `calibration_review.jpg` と透過の最大吸気画像を目視。胸元の布の動き、肩側へのつながり、襟元と顔の重なりを確認。この範囲で目立つ裂け・隙間は認めなかった。
- 新しいmoc3にmotion3を実際にSDK再生して描画。自動まばたき・自動呼吸を無効化。CSVに対する最大パラメーター誤差は音声付き版0.001247未満、呼吸のみ版は0.00001未満、許容0.003。頭上・左右の切れも検査した。
- 2本とも全フレームデコード成功。代表各7フレームで書き出しMP4と元の描画フレームを照合し、胸部領域の時間差分を検出。背景変化で動作ありと判定していない。
- 音声付き版の入力WAVは前回と一致。AAC出力との相関0.999982、相関ピークのずれ0ms。音声・映像開始0、尺の差は1フレーム未満。
- `preview.jpg` と `breath_sequence_review.jpg` を目視。字幕・説明カード・切り抜き映像を含めないモデル単独表示を確認。
- Bossによる通し視聴・自然さの受入は未実施。親の目視確認はフレーム画像であり、音声付き通し試聴とは区別する。

検査結果は `calibration_verification.json`、`render_verification.json`、`verification.json`。成果物ハッシュは `manifest.json`。

## 再生成

プロジェクトルートで実行する。最初のコマンドは旧モデルとの独立した形状比較。続く2つで今回のサンプルと検査結果を同名で再生成する。

```powershell
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v1/build_preview.py --calibrate
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v1/build_preview.py
output/live2d/runtime_venv/Scripts/python.exe output/live2d/chest_breath_v1/verify_preview.py
```

cmo3の形状を変更した場合はCubismでmoc3を再書き出ししてから実行する。スクリプトはcmo3の編集を自動再現するものではない。

作業記録: 親AstraがCubism GUI編集、コード描画、検証、静止フレーム確認を担当。実効推論強度は未確認。子Agent0、forkなし。新規パッケージ追加なし。UIは起動直後とダイアログ終了時にウィンドウ取得エラーがあったが、再取得して状態確認し復帰。総所要時間・契約使用量は未計測。Filmoraへの反映や全編の再出力は今回の範囲外。
