# Ren 眉の動き実装と検証

2026-10-01。Bossが目と閉眼まつ毛を修正した `Ren_base4.cmo3` を入力とし、Cubism Editor 5.3.04 FREEのGUIで眉を実装した。成果物は [Ren_base5.cmo3](../Ren_base5.cmo3)。髪の表示とパラメータを既定値へ戻して保存し、タブを閉じて再読込できることを確認済み。

## 保存版

| 対象 | 容量 | SHA256 |
|---|---:|---|
| 入力 base4 | 7,373,000 bytes | `666c7f3e1e579faf9703f4dde525f06217f75b83296c5337d440c7fcb59bd8e8` |
| 出力 base5 | 7,385,026 bytes | `6e2a8e9c856c0617f4dd100e3b6c2a6f7a29582760a9ef1bbc4f4aed9768d647` |

base4は更新2026-10-01 19:41:25 JST、base5の最終保存は20:17:18 JST。入力を [Ren_base4_before_brows.cmo3](Ren_base4_before_brows.cmo3) として保護し、作業後も入力・バックアップのバイト一致を確認した。CMO3の編集はすべてCubism上で行い、内部形式への直接書込みはしていない。

## 実装

既存の眉8パラメータへ各3点 `-1 / 0 / +1` を接続。Parameter ID・範囲・既定値は変更していない。左右の眉は独立して操作できる。以下の左右はモデル側の名称であり、Lは青い目側、Rは茶色の目側。

| 動き | Parameter ID | -1 | +1 |
|---|---|---|---|
| 上下 | `ParamBrowLY` / `ParamBrowRY` | 下げる | 上げる |
| 左右 | `ParamBrowLX` / `ParamBrowRX` | 鼻側へ寄せる | 外側へ開く |
| 角度 | `ParamBrowLAngle` / `ParamBrowRAngle` | 眉頭を下げる方向 | 眉頭を上げる方向 |
| 変形 | `ParamBrowLForm` / `ParamBrowRForm` | 中央の山を抑える | 中央の山を上げる |

各側の階層は `Face_Warp → Brow_L/R_Angle → Brow_L/R_X → Brow_L/R_Y → Brow_L/R_Form → brow_L/R`。回転2個・ワープ6個を追加し、デフォーマは14→22個。眉ArtMeshの親変更に伴いローカル座標はCubismが変換した。元のメッシュ分割や使用画像は維持している。

角度はLが `-12 / 0 / +12` 度、Rが `+12 / 0 / -12` 度。上下・左右は画面で移動し、上げ約31px／下げ約23px、左右約11.5px相当を目安にした。これらの移動量は表示倍率からの概算であり、保存データ上のワープ座標系の直接測定値ではない。変形は中央列のベジェ制御点を上下して曲率を調整した。

## 確認結果

[verification.json](verification.json) の静的検査16項目はすべてPASS。

- 48 ArtMeshの使用画像RGBA・配置、編集用メッシュ座標・接続・三角形インデックスがbase4と一致。
- 全28パラメータの定義を維持。眉以外の既存キーフォーム・階層・表示状態に差分なし。
- 追加8デフォーマが正しい既存IDに接続され、各3キーの形状が異なることを確認。
- 全70オブジェクトの509キー登録に欠落・重複・未解決のフォーム参照なし。
- 既存デフォーマ、Physicsの入力・出力等の検査対象設定、アトラス数を維持。作業中に隠した髪5メッシュと親デフォーマの表示はすべて復帰。

`face_underfill` と `eyelash_closed_L` の編集用メッシュの生XMLハッシュは保存時の参照番号変更で異なる。`xs.ref` を解決し、シリアライザの `xs.id / xs.ref / xs.idx` を除外した内容比較では一致した。単純な生XMLハッシュ差を形状変更とは扱っていない。

GUIでは各動きの端点、両眉の困り・怒り方向の組合せ、目Smile .5/1、開眼・片閉眼・両閉眼・半開きを代表条件で確認。低い眉でも、確認した条件では目との大きな交差や破綻は見えなかった。上下・角度・変形の中間値と左右非対称の組合せも確認した。最後に全パラメータを既定値（眉0、開眼1、EyeSmile0）へ戻し、髪を表示して保存・再読込した。

| 証拠 | 内容 |
|---|---|
| [01](01_neutral_hair_hidden.jpg) | 髪を隠した中立眉 |
| [02](02_form_plus.jpg) / [03](03_form_minus.jpg) | 変形パラメータの両端 |
| [04](04_low_concern_combo.jpg) / [05](05_concern_smile.jpg) | 低い困り眉、笑顔との組合せ |
| [06](06_low_anger_combo.jpg) | 全眉パラメータ-1の組合せ、開眼・Smile1 |
| [07](07_closed_eyes.jpg) | 同じ眉条件で両閉眼・Smile1 |
| [08](08_intermediate_asymmetric.jpg) | L眉Y/Angle=-.5、Form=.5と左右の異なる開閉量 |
| [09](09_saved_hair_restored.jpg) | 髪を戻した保存状態 |
| [10](10_reopened_default.jpg) | base5を閉じて再読込した既定状態 |

## 未検証と次工程

正面の代表条件までの確認であり、全パラメータの直積・厳密な連続掃引・runtime書出し・VTube Studio・自然さのBoss最終受入は未実施。Bossの目7点修正の全条件を再受入したわけでもない。

現行base5でも `ParamEyeBallX/Y` と `ParamAngleX/Y` はキーフォーム未接続。今回の眉実装で視線や頭部XYが完成したとは扱わない。次は眉の動き幅の見た目確認と視線実装、正面の目・眉・口の組合せ点検を経て、予定のY→X→中間→XY四隅→Z複合へ進む。Zは既存接続を保持した。旧head_angles実験へ戻らない。

## 作業記録

Repositoryは `C:/Python/REX_AI/Youtube_Project`、main、HEAD `f81916152b638cf03a90fef8becbfc046fb9c888`。20:20 JSTのstatusはA 486、AM 2、AD 2、未ステージM 13、D 6、未追跡集約8。既存の資産整理・ユーザー編集が混在する。base_motionは未追跡。今回add/commit/pushなし、既存ステージや原画・教材を変更していない。

担当はCodex、子Agent 0、forkなし。実効モデル名・推論強度・利用量は未取得。GUI工程は保護記録19:43:55から最終保存20:17:18まで約33分（事前調査と後続検証・記録を含まない）。左眉Yの初回ドラッグで境界を掴んだ操作をUndoして中央移動に修正した。途中のウィンドウ取得失敗は再観測後に作業を継続。最終データ検査と再読込で保存結果を確認した。

再検査：`python -X utf8 Live2D/model-ren-asagiri/model/base_motion/brow_implementation_20261001/verify_brows.py`。これはCMO3を読み取る内部形式の検査であり、Cubism SDKによるruntime検証ではない。
