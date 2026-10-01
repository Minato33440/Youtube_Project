# Live2D 資産整理 — 2026-09-28

2026-10-01追記：以下の件数・ステージ状態は9/28当時の履歴。旧カタログと旧一括登録リストはローカル資料として保持し、現在の登録対象には使わない。今回の選別は[Git保存方針](../20261001_git_policy/README.md)と保存一覧を正本とする。

対象: `C:/Python/REX_AI/Youtube_Project/Live2D`。`Traning/` はBoss管理のため変更していない。制作・復旧の入口は [現在のGit保存方針](../20261001_git_policy/README.md)。

## 結果

| 分類 | 件数 | 容量 | 選び方 |
| --- | ---: | ---: | --- |
| 新しくGitへ保存する制作資産 | 221 | 約164.6 MiB | [git_asset.txt](git_asset.txt) |
| 未採用実験・失敗例・復旧点 | 249 | 約169.6 MiB | [git_experiment.txt](git_experiment.txt) |
| 既存の未追跡文書・設定・音声プロジェクト | 5 | 約0.04 MiB | [git_document_or_project.txt](git_document_or_project.txt) |
| 既にGit追跡済み | 243 | 約51.7 MiB | 今回の整理前からの追跡対象 |
| 今回archiveへ移動したフレーム・ログ | 16 | 約2.04 MiB | [移動台帳](movement_manifest.json)で復元可能 |
| 既存ローカルarchive | 778 | 約142.7 MiB | 原則ignore、ディスク上に保持 |
| ローカル依存・キャッシュ | 70 | 約112.2 MiB | インポート先を壊さないよう位置保持 |
| その他の既存生成物・旧版 | 83 | 約56.2 MiB | 従来のignoreを維持、位置保持 |

件数は整理開始時の1,665ファイルの分類。新しく作ったこの索引・台帳・検証コード等は別。削除は0件。選別済みの新規候補475件と整理用文書をステージした。以前から変更されていたファイルはステージせず保持。コミット・pushは未実施。

もとの未追跡表示は167件だったが、PNG・PSDが一律ignoreされていたため、制作に必要な原本や手修正素材も隠れていた。23件をローカル保管扱いにし、従来隠れていた331件を資産・証拠として候補に加えた。新規候補475件を上の3リストで選別済み。画像をすべて無条件に追跡する設定にはしていない。

## 旧コミット案（廃止・実行しない）

選別済みの新規ファイルはステージ済み。分類を分けてステージし直す場合、リポジトリのルートで以下のリストを利用できる。リストには `Traning/`、キャッシュ、選外のarchiveを含めていない。

```powershell
git add --pathspec-from-file=Live2D/maintenance/20260928_asset_cleanup/git_asset.txt
git add --pathspec-from-file=Live2D/maintenance/20260928_asset_cleanup/git_experiment.txt
git add --pathspec-from-file=Live2D/maintenance/20260928_asset_cleanup/git_document_or_project.txt
git add -- Live2D/.gitignore Live2D/ASSET_CATALOG.md Live2D/maintenance/20260928_asset_cleanup
```

制作資産と実験資料は別々のコミットにできる。`git add Live2D` や `git add .` ではBoss管理の `Traning` や既存変更まで含むため、この一覧を使う。

[review_existing_changes.txt](review_existing_changes.txt) は作業開始前から変更されていたLive2D内の9ファイル。現在のCMO3やREADME変更も含むため、新規候補リストとは分けた。今回追記した入口3文書にも以前の変更がある。既存差分ごと確認して選ぶ。ルート `.gitignore` と `output/live2d/risa_parts_v1/README.md` の既存差分は変更していない。

最大の新規候補は旧正面PSDの25,279,393 bytes。今回はGit LFS設定や履歴の書換えを行っていない。同一アトラスの複数パスはruntimeの相対参照に必要で、Git上の同一内容blobは共有される。

## archiveと復元

移動先は `Live2D/archive/20260928-generated-previews/`。`inventory.csv` に全対象の元パス・分類・サイズ・SHA256、`movement_manifest.json` に今回移動した16件の元先対応を保存した。

```powershell
# 復元対象の確認だけ
python -X utf8 Live2D/maintenance/20260928_asset_cleanup/restore_previews.py
# 必要な場合のみ復元。既にある元ファイルは上書きしない
python -X utf8 Live2D/maintenance/20260928_asset_cleanup/restore_previews.py --apply
```

最初の候補44件から、現行検証コードが直接またはglobで読み込む28枚を元位置へ戻した。最終退避はbasic_expressionの個別フレーム12枚、head_neck_hairの動画キャプチャ2枚、head_anglesの描画ログ2件。検証入力であるhead_neck_hair/head_anglesのcase画像一式は維持した。

archiveはGitに入らない。ディスク障害へのバックアップは別途必要。今回保管した旧資料を、新しい制作指示や現行の採用版として扱わない。

## 検証と限界

[validation.json](validation.json) に、元1,665ファイルの内容保全、`Traning` 17ファイルの内容・ファイル集合・Git状態不変、現行素材manifest93参照、runtime55参照、検証コードのcase画像30枚、Git候補の非ignoreと分類漏れなしを記録。

3つの入口文書に整理案内だけ追記し、追記前の全文をローカルarchiveに保存した。PNG・PSD・CMO3・runtimeのバイト列は変更していない。旧アーカイブを使う全工程の再実行やCubismでの見た目の再確認は行っていない。

テキストには既存のWindows CRLFがあるため、差分書式検査では `cr-at-eol` を指定した。旧 `head_angles/test_report.md` の末尾空行1件は元資料を保つためそのまま。今回新規の整理文書・コードの書式検査は合格。

`organize.py` は今回の実行記録。保存済み台帳があれば再実行を止める。整理を常時自動適用するツールではない。検査だけ再実行する場合は `verify_cleanup.py` を使う。

## 作業記録

- 親担当: Astra。実効モデル・推論強度のランタイム観測値、契約枠消費は未取得。
- 独立監査: 子Agent 1、GPT-5.6 Sol / Highを指定、fork履歴なし。モデル履歴・比較コードの依存関係と整理後の対象を読み取り専用で確認。
- 手戻り: 再生成可能でも検証入力だった28フレームを退避対象から除外。変更前ハッシュに一致することを確認して元位置へ復元。
- 人の既存修正や未受入モデルを、整理の都合で採用・再生成・上書きしない。
