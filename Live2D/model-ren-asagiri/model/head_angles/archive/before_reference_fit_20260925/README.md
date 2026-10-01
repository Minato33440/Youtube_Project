# レン：小さな左右向き・正面うなずき

2026-09-25。初回実装・技術検査済み。動きの自然さと強さはBoss確認待ち。

- 編集モデル：[Ren_front.cmo3](Ren_front.cmo3)
- 確認動画：[12秒MP4](preview/Ren_head_angles.mp4)／[GIF](preview/Ren_head_angles.gif)
- [16状態の比較](preview/head_angles_review.jpg)／[動画の抜粋](preview/animation_review.jpg)
- [検査結果](verification.json)／[横顔素材の修正一覧](../../art/side_view_review/REVIEW.md)

既存の瞬き、会話口、顎、AngleZの首かしげ・首追従、髪揺れを保持した別モデル。前工程のhead_neck_hairは変更していない。正面姿勢は前回runtimeに対し最大1/255の画像差で、目立つ変化はない。

## 今回の実装

Head_Tiltの内側にHead_XY（Warp8）を追加。元の直接の子をまとめ、口内・閉眼まつ毛・顔・耳・既存の髪と顎の変形器を含めて追従させた。変換分割5×5、ベジェ2×2。AngleX/Yはそれぞれ-30/0/30、組合せ9状態。

3D回転表現の平面キーを下地に、X+30で中心制御点へ約88原画pxの横移動を加えて奥行きを作成し、左右対称の奥行き推定で他のキーへ反映。設定上の回転範囲はX±18度、Y±12度、カメラと回転中心(2000,720)、Zオフセット0、平行投影。これらは操作設定であり、画像から計測した解剖学的な頭部角度ではない。

会話中の控えめな首振り・うなずき用。90度横顔や強い3/4向きではない。横顔PNGは輪郭と奥行きの参照に使用し、新しいパーツとしては取り込んでいない。首の独立したXYキー、横向き用の耳・鼻・口の別形状、XY入力から髪へ追加する物理は今後の調整候補。今回の髪物理は既存のAngleZ入力を保持している。

## 検査と保存

Cubism Editor 5.3.04 FREEで保存し、閉じて再読込後にHead_XYの階層とX/Yキーを確認。SDK5.0互換runtimeを別フォルダーへ出力。元PNG128枚と前工程cmo3の開始時ハッシュは不変。48 ArtMesh／27パラメータを実runtimeから確認。

16状態にはX/Y四隅、左右上下、横向き＋閉眼、うなずき＋会話、AngleZと髪を含む複合姿勢を含む。下部シャツの描画は全状態で不変（最大差1以下）。顎下・首・耳下を静止比較と動画抜粋で確認し、今回の範囲では目立つ背景抜けを認めなかった。12秒360フレームのMP4と180フレームGIFを作成。動画の髪はruntime物理の出力で、直接髪パラメータを駆動していない。

VTube Studio・nizima LIVEは未検証。大笑いの追加開口、完全な横顔は未実装。Bossの見た目の了承はまだ記録していない。

## 続き

まず動画でうなずき量・左右の向きの見え方を確認する。必要なら顔面と後頭部の奥行きを分け、鼻・口・遠い側の目の形を個別調整する。角度を拡大する際は[横顔修正一覧](../../art/side_view_review/REVIEW.md)を参照し、BossのPNG補修とAgentの配置・リグ調整を分業する。

参考：[Live2D公式・3D回転表現](https://docs.live2d.com/cubism-editor-manual/apply-3d-rotation-expression/)／[ワープデフォーマ](https://docs.live2d.com/cubism-editor-manual/making-and-placement-of-warp-deformer/)。中央制御点と全体移動の中心が重なる場合は、赤いバウンディングボックスを隠してから制御点を操作する。
