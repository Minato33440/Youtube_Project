# Ren 虹彩XYの実装と検証

2026-10-02。Bossの依頼「虹彩XYZ」は直後の訂正によりXYのみを対象とした。Cubism 5.3.04 FREEのGUIで手動実装し、編集可能な [Ren_base6.cmo3](../Ren_base6.cmo3) に保存・再読込した。Zと頭部XYは今回変更していない。自動生成・Physicsによる動きの追加は行っていない。

## 保存版と入力

| 対象 | bytes | SHA256 |
| --- | ---: | --- |
| 入力 Ren_base5.cmo3 | 7,393,532 | `375c7c2e85d871c2c36648e9f884f3f5ebd73e775f78e239e6dee43c055d148c` |
| 出力 Ren_base6.cmo3 | 7,401,473 | `3b1a458f976d22c9d4829d89af2fb7222ca478372d19af3fa9980968fa0e6f5b` |

入力の元ファイルと [保護コピー](Ren_base5_before_iris_xy.cmo3) はバイト一致。開始時の [baseline.json](baseline.json) とも照合済み。入力は前日の眉検証時のbase5（hash `6e2a8e9c...`）から更新されているため、今回の保存版に対して改めて検査した。

## 実装

両目共通の既存 `ParamEyeBallX`／`ParamEyeBallY` を使用し、各ワープへ-1／0／+1の3点を登録。+Xは画面右、+Yは画面上。Yを虹彩の親、Xをその外側の親とした。X作成時は「子要素のキーフォームを考慮」を有効にした。

| 目 | 親から子への階層 | 接続 |
| --- | --- | --- |
| 左 | Left_Eye → Iris_L_X (Warp21) → Iris_L_Y (Warp20) → ALT_iris_L_blue | X／Y |
| 右 | Right_Eye → Iris_R_X (Warp23) → Iris_R_Y (Warp22) → ALT_iris_R_brown | X／Y |

105.6%表示時にXを左右各24画面px、Yを上下各16画面px移動して端点を作成。モデル換算の目安は約22.7px／15.2pxだが、最終表示の移動量は既存の目の開閉・Smile親変形にも依存する。元の虹彩ArtMeshは開閉キー、不透明度、クリッピングを維持。髪は作業中も表示した。

## Editorの目視確認

頭部XYZは0。以下は保存前の代表条件の確認であり、全条件の連続掃引ではない。L/Rの指定がない行では左右同値。虹彩の移動を確認し、確認条件内で白目の外へのはみ出しや閉眼時の残留は見られなかった。

| 条件 | 確認した視線・値 | 画面証拠 |
| --- | --- | --- |
| Open 1、Smile .5 | 中立、左右上下の端点、XY四隅 | [01](01_neutral.png)、[02](02_left.png)、[03](03_left_up.png)、[04](04_right_up.png)、[05](05_right_down.png)、[06](06_left_down.png) |
| Open 1、Smile .5 | X +.5、Y -.5の中間 | [07](07_mid_xy.png) |
| Open .5、Smile .5 | 中間とXY四隅 | [08](08_half_open_mid.png)、[09](09_half_right_up.png)、[10](10_half_left_up.png)、[11](11_half_left_down.png)、[12](12_half_right_down.png) |
| Open .25、Smile .5 | X +1、Y -1。UI数値は丸め表示で.3 | [13](13_quarter_open_right_down.png) |
| Open 0、Smile .5／1 | X +1、Y -1 | [14](14_closed_extreme.png)、[15](15_closed_smile.png) |
| L Open 1、R Open 0、Smile 1 | X +1、Y -1のウインク | [16](16_wink_smile_gaze.png) |
| Open 1、Smile 1／0 | X +1、Y -1 | [17](17_open_smile_gaze.png)、[18](18_no_smile_gaze.png) |

保存後にタブを閉じ、base6を再読込できることを確認（[19](19_reopened.png)）。その後、視線XY0・頭部XYZ0・両Open1・両Smile .5・眉0へ戻した。髪表示、未保存表示なし、base6を開いたまま終了（[20](20_final_center.png)）。再読込後は中立を確認し、全代表条件の再掃引はしていない。

## 保存データの静的検査

[verify_iris_xy.py](verify_iris_xy.py) を `python -X utf8` で実行、終了コード0、[verification.json](verification.json) の16項目すべてPASS。CMO3は読み取りのみ。既存の監査パーサーで入力・出力を展開し、参照番号の差を解決して意味上の一致を比較した。[before_inventory.json](before_inventory.json)／[after_inventory.json](after_inventory.json)。

- 入力base5、保護コピー、開始時hashが一致し、検査中のファイル変更なし。
- 48メッシュと頂点・三角形、48使用画像のRGBA・配置、既存可視性を保持。
- 28パラメータ定義、既存22デフォーマ、Physicsとアトラス数を保持。追加は予定したワープ4個のみ。
- 既存オブジェクトの差分は虹彩2枚の親と親変更に伴うローカル形状座標に限定。顔下地・眉などの既存形状は不変。
- 虹彩の開閉バインド・キー列・不透明度・クリッピングを保持。追加ワープの3点、方向、親参照と異なる端点形状を確認。
- 全74オブジェクトの536キー登録に欠落・重複・未解決参照なし。

## 未確認と次工程

全Open×Smile×視線XYの連続動作、頭部角度や髪との全複合条件、runtime書出し・実機動作、Bossによる自然さの最終受入は未実施。今回は虹彩XYの初回実装と代表条件の確認を完了した。次はBossの見た目確認を経て、予定の頭部Y→X→中間→XY四隅→Z複合へ進む。

## 作業記録

正本Repositoryは `C:/Python/REX_AI/Youtube_Project`、main / HEAD `9e45ffe068c7df5ec4527dbc10d803a596285c9b`。base5を保護してbase6へ別名保存。既存のLesson01削除6件、head_neck_hair/Ren_front.cmo3の変更、未追跡の過去成果物は整理せず保持。add/commit/pushなし。

担当はCodex、子Agent 0、forkなし。実効モデル名・推論強度・利用量は取得していない。保護コピー作成15:04 JSTから静的検査完了15:28 JSTまで約24分、その後に記録を整理。GUIの誤選択による顔下地移動を取り消し、保存版の比較で不変を確認した。検査スクリプトの初回JSON出力ではNumPy boolの直列化エラーを修正して再実行し、16項目PASSを得た。両件ともモデルの未解決欠陥としては残っていない。
