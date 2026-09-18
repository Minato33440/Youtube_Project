# Risa 約16秒ナレーション口パクテスト（2026-09-14）

Boss提供の `C:/Users/Setona/Desktop/Voicd-Sample.mp4` を基準に、音声抽出、実Cubismモデルの音量駆動、確認MP4の合成まで実施した。元動画・原画・既存のneckfixモデルは上書きしていない。

## 見るファイル

- `Risa_narration_composite.mp4`：元動画の右上に上半身を配置。説明カード・字幕・クレジットを避けた仮配置。
- `Risa_lipsync_closeup.mp4`：口元を確認しやすい拡大版。同じ音声・同じ口パク時刻。
- `audio_stereo_44100_pcm16.wav`：元MP4から抽出した音声。音量変更・末尾削除なし。
- `audio_mono_44100_pcm16.wav`：口パク解析用。元MP4を同条件でデコードしたPCMと完全一致。
- `Risa_voice_test.cmo3`：テクスチャアトラスを追加したテスト用の編集モデル。
- `model/Risa_compat.model3.json`：今回実際に再生した組込み用モデル。対応するmoc3と `Risa_compat.2048` フォルダーを一緒に保持する。
- `frames/`：768×1024、透過PNG、478フレーム。再編集用の独立レイヤー。MP4自体に透明背景や編集レイヤーはない。
- `mouth_curve.csv` / `mouth_curve.json`：各フレームの時刻、音量、口開閉値。
- `voice_sync.motion3.json`：口開閉のMotion3形式データ。今回の動画はCSVを直接パラメーターへ適用して描画したため、このMotion3のアプリ読み込みは未検証。
- `manifest.json`：配置・時刻・モデル参照。`verification.json`：機械検査結果。

## 同期調整

動画は1280×720、30fps、478フレーム、15.933333秒。デコード音声は44.1kHz、15.939048秒。入力先頭を0秒として同期し、出力映像は478フレームに揃えた。AACの末尾パディング相当の差は約5.7ms。

33.3ms窓のRMSから開口量を作り、最大値を0.85に抑えた。開き60ms／閉じ80msの平滑化とゲートで、無音付近の細かな振動を抑制している。固定の映像・音声オフセットは0。滑らかさのための応答時間はあり、音素単位の手付け同期ではない。

原ナレーション `Politics_Economics/2026-09-09_fiscal_policy/speech/sample_v1/N01.wav` と抽出音声を照合。8サンプル間引きで相互相関を取り、約+0.000726秒、重なりの相関約0.97586を確認。N01の長さ15.600884秒に対し、約15.8667秒に別の短い音声成分があった。この成分による口の開き直しを避けるため、15.602秒以後は新たな開口入力を止めた。抽出音声とMP4音声はそのまま残しており、その短い音の種類は聴取確認が必要。

## 実モデルと互換性

元モデル：`C:/Users/Setona/Desktop/AI Works/Youtube-Project/Live-2D/v2/Risa_Live2D_v2_basic_rig_neckfix.cmo3`。

Cubism FREE上で2048×2048のテクスチャアトラスを作り、別名保存後、SDK 5.0形式で書き出した。live2d-py 0.7.0.4 / Cubism Core 5.1.0で実描画している。最初のSDK 5.3形式はこのランタイムで非対応のためクラッシュしたが、SDK 5.0書き出しで解消した。`model/Risa.model3.json` はその初回の5.3形式であり、今回の再生には使わない。

口は実モデルの `ParamMouthOpenY` を使用。閉口0／中間0.5／開口1の描画を確認した。原画の差し替えや口画像の後付け合成ではない。今回の検査用映像では目を開き、首傾き0、呼吸0に固定し、口だけの同期を評価できるようにした。

## 検証済みと未確認

- 両MP4の全フレームをFFmpegでデコードし、エラーなし。
- 両MP4は30fps・478フレーム。音声と映像の開始時刻は一致。
- 出力音声と元音声のオフセット0での相関は0.99998以上（AAC再エンコードあり）。
- 全478枚の透過PNGを検査し、変化は口元の範囲だけ。開閉曲線が0のフレームは閉口画像に一致。口元画像変化と開閉曲線の相関は、前後3フレーム内で遅延0が最大。
- 合成版・拡大版の代表画像、閉口／最大開口／無音時／末尾の比較画像を目視確認。
- 技術的な同期と代表フレームの検査を実施した。動画全編を人が音声付きで視聴した品質確認は未実施。Bossには拡大版で発話の立ち上がり・語尾・開口の強さを確認してもらう。
- 母音別の「あ・い・う・え・お」、顎の連動、今回固定したまばたき・首・呼吸の組合せは本テストの評価範囲外。
- Cubism Editor用の音声入りアニメーションプロジェクト（can3）やFilmoraプロジェクトは今回未作成。再合成に必要な音声、透過連番、曲線、配置、スクリプトは保持。

## 再生成

プロジェクトルート `C:/Python/REX_AI/Youtube_Project` で実行する。各コマンドはこのテスト出力のみ更新する。

```powershell
& 'output/live2d/runtime_venv/Scripts/python.exe' 'output/live2d/voice_sync_v1/build_mouth_curve.py' --input 'output/live2d/voice_sync_v1/audio_mono_44100_pcm16.wav' --output-dir 'output/live2d/voice_sync_v1'
& 'output/live2d/runtime_venv/Scripts/python.exe' 'output/live2d/voice_sync_v1/render_model.py'
& 'output/live2d/runtime_venv/Scripts/python.exe' 'output/live2d/voice_sync_v1/compose_video.py'
& 'output/live2d/runtime_venv/Scripts/python.exe' 'output/live2d/voice_sync_v1/verify_outputs.py'
```

## 工程記録

親がCubism書き出し・実描画・合成・最終検査を担当。音声抽出と初期曲線生成を子Agent 1名（Terra、Medium指定、forkなし）に委任した。独立した音声処理と直列のCubism操作を並行できるため。末尾ゲートの調整は親が実施。親のモデル・推論強度の実効値、契約枠使用量、厳密な工程別所要時間は計測していない。手戻りはSDK互換性と透明背景設定、末尾の再開口修正。技術検査と視聴による好みの評価を分けている。

参照：[Live2Dモデル書き出し](https://docs.live2d.com/en/cubism-editor-manual/export-moc3-motion3-files/)、[live2d-py](https://github.com/EasyLive2D/live2d-py)。
