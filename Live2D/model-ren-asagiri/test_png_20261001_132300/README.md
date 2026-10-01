# レン：比較テストPNGの索引

2026-10-01整理。条件・制作記録を確認できた**53枚、14,532,257 bytes（約13.86 MiB）**を [selected](selected/) に元バイトのままコピーした。ファイル名は内容・条件・テスト日。mtimeによる最終判定はしていない。

「同じテスト段階の最終出力」「了承済みの形状見本」「未採用実験の最終実施版」「異なる計測基準」を分けた。ここにある画像を現行Ren_base3の検証済み証拠とは扱わない。

| フォルダ | 枚数 | 内容・日付・位置づけ |
|---|---:|---|
| [01_static_assembly](selected/01_static_assembly/) | 5 | 9/21首襟、9/24頭部最終、PSD統合前の髪・耳接続の了承段階も別保存 |
| [02_psd_validation](selected/02_psd_validation/) | 4 | 9/24正面41層PSDの目・頭首・首襟・独立読戻し。静止検査 |
| [03_accepted_shape_references](selected/03_accepted_shape_references/) | 7 | 9/22瞬き3段階・通常会話口v002の4段階。過去に了承された形状見本 |
| [04_face_comparison](selected/04_face_comparison/) | 1 | 9/22顔v010比較の「今回」サンプル。現行原画とは別 |
| [05_accepted_initial_motion](selected/05_accepted_initial_motion/) | 14 | 9/24顎・首・髪・閉眼・会話の各条件。初回動画は9/25了承。現在のCMO3と同一とは断定しない |
| [06_unaccepted_contour_experiment](selected/06_unaccepted_contour_experiment/) | 6 | 9/26全頭輪郭344点の比較・補間・顎・正面保持・他姿勢。191点の旧計測は異なる基準として1枚別保存。未採用 |
| [07_unaccepted_XY_experiment](selected/07_unaccepted_XY_experiment/) | 16 | 9/26全頭XY試行の最終16条件。顔単体へ移る前の未採用段階 |

日時と位置づけの根拠、元パス、コピー先、SHA256、サイズ、Git状態、パラメータ値は [selection.json](selection.json)。case番号と条件の対応は既存verification.jsonとrender_preview.pyの列挙・保存処理を照合した。元記録の `Tilt + speech` は実値がZ=-30なので、名前はラベルから推測せずパラメータ値を採った。

## archive移動は0件

比較出力候補344枚を棚卸しし、完全同一バイト33群を確認した。ただし**全344枚が9/28のbaseline.jsonに登録され、現行verify_cleanup.pyが元パスで内容を検査する**。依存を壊さないという今回の条件に従い、移動・削除はしていない。原パスの維持が必要なcase画像、Before画像、共有latest_previewもそのまま。

特に同じ髪・耳接続テストの再出力2枚（合計1,319,193 bytes、約1.26 MiB）は削除候補として特定できたが、次の理由で移動保留。

- `art/head/work/hair_check_20260924/final_preview/head_sample.png`
- `art/head/work/hair_check_20260924/final_preview/head_sample_gray.png`

それぞれ同じテスト内の `registered_position.png` / `registered_position_gray.png` とバイト一致。採用段階を表すその2枚は元位置と今回の集約先に保持。しかし上記の保存検査が旧再出力パスも読むため、archiveへは移していない。[move_plan.json](move_plan.json) に元／予定archive／SHA256／理由／代替画像／依存を記録。[movement_manifest.json](movement_manifest.json) は空配列で、実移動なしを表す。

archive整理を続けるなら、先にこの保存検査を新しい移動台帳に対応させる必要がある。今回は既存検査コード・過去の台帳・文書を変更していない。ファイル数や重複率を理由に異条件の画像を捨てない。

## 棚卸しと確認範囲

- [review_candidates.json](review_candidates.json)：344候補の保存位置・ハッシュ・Git状態・依存、33重複群。選定外291枚は現状保持。原画・parts・source_snapshot・runtime・参考原画・前回集約は候補から除外した。
- [reference_audit.json](reference_audit.json)：Repositoryのテキスト・コードの参照検索と判断。動的生成パスの完全な静的解析ではないため、不明なものは移動しない。
- [verification.json](verification.json)：53コピーのバイト一致、元ファイル・モデル・runtime・前回48枚集約と報告の不変。Git indexのバイト不変は下記のとおり未確認。
- [preservation_before.json](preservation_before.json)：依存ライブラリ・キャッシュを除く元Projectファイルの開始時ハッシュ。
- [organize.py](organize.py)：コピーと検証の再利用コード。既存出力への再実行は停止する。移動保留の計画は実行できない。

53枚は確認シート [1](qa_selection_1.jpg)・[2](qa_selection_2.jpg)・[3](qa_selection_3.jpg)・[4](qa_selection_4.jpg)・[5](qa_selection_5.jpg) で実際に閲覧。これはファイル内容・条件の確認であり、表情・モデル品質の再受入ではない。集約はPNGのみで、JPG/GIF/動画の比較記録は元位置を保持する。

既存ファイルの上書き、元原画・CMO3・runtime変更、削除、archive移動、.gitignore変更、stage/commit/pushなし。コピーによる増分であり、ディスク容量は削減していない。

## Git indexの別途観測

開始時index SHA256は `59690fce0efbf40ce9f4e38029e0f4bf704aaeeafb591d99b49115139b6e9166`、終了確認時は `dc27048fedbfe430119554cdae71dc98e70c195ae7947d862420f1489faeb07f`。index更新日時は2026-10-01 13:26:24 JST。こちらからGit書込みは行わず、Git照会には `--no-optional-locks` を指定したが、変更したプロセスと理由は確定できない。indexの復元・上書きは行わない。

ステージは490件のまま。開始時に記録した比較候補344パスのindex登録（96追跡パスを含む）はすべて一致した。全indexの開始時内容を保存していないため、全登録の不変までは証明しない。`art/expression_rig/parts/eyelash_closed_L.png` と `eyelash_closed_R.png` は終了時AD表示だが、前回棚卸し時点でも同フォルダのPNGは口5枚のみで、今回の開始時ファイル記録にもこの2枚は含まれない。今回削除したものではない。採用元 `art/head/parts/eyelash_closed_L/R.png` は不変。詳細は [index_observation.json](index_observation.json)。

実行記録：Codex、追加子Agent 0、実効モデル名・推論強度・使用量は未取得。記録照合、バイト重複、参照追跡、目視、コピー保全検査を実施。移動候補2枚は依存発見により実行前に保留へ変更した。


2026-10-01参照更新：前回の原画集約は[latest_png_collection](../art/latest_png_collection/README.md)へ移転。preservation_before.json・reference_audit.jsonは当時の原記録のまま保持し、検証時のみrelocation.jsonで旧パスと今回の参照修正を解決する。既存verify_cleanup.pyは変更していない。
