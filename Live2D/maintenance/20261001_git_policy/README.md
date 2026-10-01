# RenのGit追跡方針整理（2026-10-01）

## 2026-10-01 選択保存の現行方針

ユーザー承認により、今後このリポジトリでは資産価値と容量を確認して個別にcommit/pushする。一括add、定期自動push、履歴書換えは行わない。現行編集元、再利用コード、必要設定、判断・検証記録を優先し、旧世代binary、依存ライブラリ、再生成物は別保管する。権利や公開範囲が不明な新規資料は保留する。画像は原則ローカル／別ストレージで管理し、明示承認済みlatest_png_collectionの5形式・再帰・大小文字例外のみ維持する。保存先未指定のため物理移動・削除・外部ストレージへのアップロードはしない。

今回の開始HEADは `5f2fbac87c050338e5bb19cd33a39c0230e3f508`。開始時index差分は0件で、GitHub mainと一致。教材8件とlatest_previewの6画像の追跡解除は既にpush済み。以下の旧「stage6件」「335候補」等は実施当時の記録であり現在の状態ではない。

旧 `Live2D/ASSET_CATALOG.md` は未追跡だったため、実物を残したままignoreし追加しない。現行CMO3はRen_base5のみ新規保存し、base〜base4はローカルに保持する。採用PNGフォルダ59件は旧base3スナップショットとして保存。旧モデル・証拠画像・中間JSONへのリンクはローカル資料への参照であり、cloneだけで過去検証を完全再現できるとは扱わない。

保存対象とSHA256は [selected_assets.json](selected_assets.json)。旧一括登録リストや未採用実験の中間JSONは新規追加しない。既存追跡済み依存の整理は別作業。教材追加binary、head_neck_hairの変更CMO3、pylibと旧Lesson01の削除表示は今回の対象外。

今回の検証は秘密情報パターン検査、JSON/Python構文、ignore規則、保存前後hashとindex・remote照合。モデルの内部・GUI・映像・音声・runtime動作は再検証していない。旧検証結果を現在のモデルに転用しない。

実行記録：Codex、子Agent0、forkなし。モデル／推論の実効値・使用量は未取得。再作業は旧記録と現行説明の区別、旧モデル除外に伴う規則検査更新。以下は以前の整理の履歴。

---


ユーザー承認により、Renの原画・比較画像・テスト生成物・重複コピーはローカル保管とし、Git用原画コピー `art/latest_png_collection` を例外にした。規則の正本はRepository直下の [.gitignore](../../../.gitignore)。全Repository共通のGit設定は変更していない。

## 残すもの／ローカル保管

- `latest_png_collection`：PNG/JPG/JPEG/PSD/GIFを大小文字・深い階層を含めて許可。README・台帳・検証コードも保持。Cubism作業側のPNGから移動・置換していない。
- 手順・判断記録・manifest・検証コード：作業／テスト／archive内でも種類別に追跡可能。機密JSONの既存除外は再有効化しない。
- `model/base_motion`直下のCMO3：現行base5を含めて許可。番号だけで旧版を不要と判断せず、base〜base4も残した。教材・既存本体／runtimeのmoc3/JSON・他プロジェクトの規則は維持。
- `art`、`art_assets`、`latest_preview`、`test_png_*`、モデルのpreview/review/implementation、未採用head_angles、archive/backup/buckup：用途フォルダ単位で生成物を除外し、記録とコードだけを再許可。画像はRen範囲で種類別にも除外するので、新しいテストフォルダにも適用される。
- `Live2D/.gitignore`の626行の個別例外は、rootへの案内3行に集約。局所的な依存ライブラリ／解析中間物用の既存.gitignoreは保持。

**文書の画像・旧モデルへのリンクはローカル保管先への参照となる。Git cloneだけでは、その画像表示や画像入力を必要とする過去検査を再現できない。** 旧runtimeのtexture画像も原則ローカルであり、cloneだけの配布用runtime一式とは扱わない。元ファイルは全て元位置に残したため、この整理で既存ローカルruntimeの参照は変更していない。105枚の証拠画像を新規stageする以前の案は撤回した。

## indexの変更

開始時のステージ差分は空。HEADは `f81916152b638cf03a90fef8becbfc046fb9c888`。

既存追跡の `model-ren-asagiri/latest_preview/` 内の次の6画像だけを `git rm --cached` で登録解除した。物理ファイルは残っており、開始時hashと一致する。

- Ren_head_neck_hair.gif
- comparison_original.jpg
- eyes.png
- head_neck_hair_review.jpg
- head_sample.png
- python_composite.png

stageはこの6件の削除のみ。ignore・文書・他資産はstageしていない。indexのその他の登録内容、HEAD、教材の登録内容は開始時と同一。commit/push・履歴書換・ファイル移動／削除なし。

## 検証と残る注意

[check_policy.py](check_policy.py) は185条件の読み取り検査。5形式×大小文字×深い階層、作業／テスト画像の除外、archive内の文書・コード、現行CMO3、moc3/JSON、秘密JSON、対象外の教材／runtime／docs等を確認。実行例：

```powershell
C:/Python313/python.exe -B Live2D/maintenance/20261001_git_policy/check_policy.py
```

検査スクリプトはGitを変更せず、verification.jsonのみ更新する。今回の[検証結果](verification.json)は全条件合格。Ren内の読取り可能な既存1,813ファイルは欠落0・内容変更0・追加0。原画・CMO3・runtimeを含む。`art/processing_v001/tools/pylib` 内のcv2とdist-infoの2ディレクトリは最初からアクセス拒否で検査対象外。別手段で読んでいない。

別件の `output/live2d/risa_parts_v1/tools/pylib` は1,141件の未stage削除表示が残る。numpyディレクトリは存在するが列挙・ファイル参照にWinError5（アクセス拒否）となった。少なくとも実削除だけでは説明できず、全件の実体は未確定。この整理へ混ぜず、登録内容も変更していない。

許可候補の最終集計では未追跡＋追跡変更335件、作業ファイルのパス合計約197.4 MiB。教材が約132.8 MiBを占める。これはstage済み量やpush転送量ではない。[候補集計・6件のindex差分](candidate_summary.json)。現行base5とその原画を除外していない。旧base番号の正式な保管選定は未実施。

次のstageは `.gitignore`、`Live2D/.gitignore`、この整理記録を確認したうえで個別指定し、その他は必要な資産のみ選ぶ。pylibのアクセス問題があるため、`git add -A`、全index削除／再登録は行わない。stage済み6削除とignore変更を一緒にレビューすると、リモートにも今回の追跡方針が伝わる。

実行記録：Codex、実効モデル／推論強度／使用量は未取得、子Agent0。フォルダー規則・種類別例外へ整理し、185条件の回帰検査、index差分、読取り可能な全Renファイルのハッシュを確認。GUI／モデル再検証はこのGit整理の対象外。
