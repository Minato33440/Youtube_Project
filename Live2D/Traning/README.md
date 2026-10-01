# Live2D / Traning

MinatoによるCubism実装学習・検証データの保管場所。

このディレクトリでは、本番の `Live2D/model-ren-asagiri/` を直接編集せず、教材用コピーでCubism工程を検証する。

## 教材

- [Cubism Practical Production Lecture](Cubism_Practical_Production_Lecture.md) — Lesson 01〜10実習済み。Lesson 11に髪揺れの手動3点キーと自動生成の比較教材を追加。
- [Character Production Workflow](../CHARACTER_PRODUCTION_WORKFLOW.md) — Lectureから蒸留した、別キャラでも再利用する製造原則。
- [Lesson — PSD Import](Lesson_PSD_Import/README.md) — 初回教材と参照ファイル。

## 役割

- **Lecture**：実際に何を操作し、何に失敗し、どう直したかを残す。
- **Workflow**：Lessonから得た再利用可能な判断基準だけを残す。
- **各モデルREADME**：キャラ固有の素材・座標・実装・受入を残す。

## 原則

- 本番モデルを直接編集しない。
- 各Lessonは前工程のコピーから開始する。
- 操作前／操作後の保存名を分ける。
- 「動いた」だけでなく、何を変更したか・何を変更していないかを記録する。
- 失敗例も教材として残す。
- Bossの目視判断と、Agentによる機械検査を分けて記録する。
- Astra / Computer Useには階層・対象・変更可否・合格条件を明示する。

> ディレクトリ名 `Traning` は既存ルートをそのまま使用する。
