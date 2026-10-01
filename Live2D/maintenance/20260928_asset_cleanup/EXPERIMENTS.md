# 角度・輪郭調整の実験と復旧点

2026-09-28、整理のために実ファイルと記録を照合した。新しいモデル実装・再描画・受入は行っていない。以下はすべて `Live2D/model-ren-asagiri/model/` を基準とする。

| 対象 | 位置 | 意味 |
| --- | --- | --- |
| 受入済み初期動作 | `head_neck_hair` の受入記録＋Git履歴のCMO3 | 基本表情・小さいAngleZ・顎首・髪揺れ。作業ツリーCMO3との差分は未確認 |
| 斜め参照トレース前 | `head_angles/archive/before_tilted_reference_20260926/` | 既に以前のX/Y調整を含む。完全な中立の基礎モデルとは呼ばない |
| 密メッシュ化前 | `head_angles/single_endpoint/archive/before_mesh_refinement_20260926/` | 既存メッシュで片側終点を調整した版。直接のロールバック候補 |
| 密メッシュ化後・全頭トレース前 | `head_angles/single_endpoint/archive/before_whole_head_outline_20260926/` | 密メッシュ失敗の比較に必要な「後」の固定版 |
| 全頭トレース後 | `head_angles/single_endpoint/Ren_face_endpoint.cmo3` | 輪郭指標が改善しても見た目の受入には至っていない最終候補 |

## 先に見る証拠

- `head_angles/preview/tilted_reference_before_current_comparison.jpg`：傾いた原画への合わせ込みと不自然さの比較。
- `single_endpoint/dense_contour_check/cheek_jaw_comparison_ja.png`：頬・顎のトレース比較。
- `single_endpoint/dense_contour_check/other_pose_remesh_differences_ja.png`：再メッシュが未編集姿勢へ及ぼした差。
- `single_endpoint/dense_contour_check/dense_contour_before_after_measurement.json` と `refined_pose_checks.json`：当時の測定条件と結果。
- `single_endpoint/whole_head_outline_check/whole_head_runtime_guide_4up.png` と `whole_head_runtime_measurement.json`：全頭トレース段階の比較。
- `single_endpoint/whole_head_pose_check/whole_head_pose_checks.json`：当時の正面保持・中間・開口の検証と残る外縁の粗さ。
- 各階層の `test_report.md`、`verification.json`、`outline_retrace_status.json`：検証と未検証の範囲。

`single_endpoint/` で始まる短縮パスは `head_angles/` 配下。画像は実モデル由来の既存資料をそのまま保存し、今回描き直していない。

## 再利用する前の注意

1. 密メッシュ比較スクリプトの一部は「現在のface_runtime」を読み込む。この現在値は全頭トレース後へ進んでいるため、単純再実行は過去の密メッシュ実験の再現にならない。再現するときは上表の固定された前後snapshotを明示してから実行する。
2. 他の比較コードも旧世代のruntimeや `preview/case_01.png`、`case_03.png` を参照する。これらの主要依存は元パスでGit候補に残した。旧検証が合格していたことを、新しいモデルの合格と読み替えない。
3. snapshot内の生成コード・絶対パスを含む履歴JSONは、実行場所・入力版を確認して使用する。archiveから直接作業を再開しない。
4. アトラスが同一ハッシュでも、runtimeの相対参照先に必要なコピーを消さない。Gitは同一内容のblobを共有するため、パスを保ったまま追跡できる。

## 今後の評価へ持ち越すもの

- 数値的な輪郭一致と、キャラクターの自然さ・感情表現は別の評価。
- X/Y/Zを混同せず、小さな範囲の共通動作から組み立てる。
- 人の参照指定・修正とAgentの変形・比較の双方について、良かった点と手戻りを記録する。
- 今回の失敗原因を一つに断定しない。記録にある現象、Bossの評価、推測を分けて残す。
