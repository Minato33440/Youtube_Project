# レン：斜め頷きの調整


2026-09-26最新：全頭輪郭下絵で顔下地を再調整・保存・runtime再書出し済み。新ガイドによる結果と残る縁の粗さは [single_endpoint/README.md](single_endpoint/README.md) 冒頭へ。以下の191点計測は前工程の履歴。

## 現在地：顔下地のメッシュを追加して頬〜顎を再調整（2026-09-26）

Bossは前回の斜め顔と片側静止Sampleの頬の角張りを指摘。下記の旧実装は未採用。現在は顔下地だけに絞り、X=-30/Y=-30の左右頬〜顎の境界と内側へ頂点を追加し、傾きを保持した原画へ再調整した。輪郭が整うまで目・髪などへ進まない。

- [今回の説明と静止Sample](single_endpoint/README.md)
- [片側終点の輪郭比較](single_endpoint/whole_head_outline_check/whole_head_runtime_guide_4up.png)
- [中間姿勢](single_endpoint/whole_head_pose_check/face_intermediate_poses_ja.png)／[正面の頷き・口開閉](single_endpoint/whole_head_pose_check/front_mouth_preservation_ja.png)
- [現在の作業候補cmo3](single_endpoint/Ren_face_endpoint.cmo3)
- [保持検査・制約](single_endpoint/test_report.md)

基準は`archive/before_tilted_reference_20260926`、今回開始前は`single_endpoint/archive/before_mesh_refinement_20260926`。可視輪郭191点の距離は中央値7.75→2.83px、最大36.52→6.91px（4000×6000換算）。顔下地32静止条件と正面頷き・口開閉を再確認した。再分割により以前の18条件の厳密表示一致は成立しないが、正面輪郭差は2000×3000で最大1px。終点の薄い半透明の縁は残る。詳細は検査記録へ。目・口・耳・髪の終点合わせと新しい動画は保留。旧`Ren_front.cmo3`や旧動画を今回の成果物として扱わない。

## 以下は前回の未採用実装記録

2026-09-26。Looking_down (2).pngの傾きを残した参照PSDをCubismに重ね、左右の斜め頷きの頭部傾斜、頬〜顎の輪郭、鼻・口の配置を再調整した。原画の角度を水平へ戻す以前の比較方法は採用しない。最新の動作の自然さはBoss確認待ち。

- [編集モデル](Ren_front.cmo3)
- [12秒MP4](preview/Ren_head_angles.mp4)／[GIF](preview/Ren_head_angles.gif)
- [修正前・今回・傾きを残した原画との比較](preview/tilted_reference_before_current_comparison.jpg)
- [左右終点での瞬き・開口](preview/oblique_endpoint_expression_contact_sheet.jpg)
- [16状態](preview/head_angles_review.jpg)
- [参照PSD](reference_overlay/oblique_nod_reference_overlay.psd)／[位置・原画ハッシュ](reference_overlay/reference_overlay_manifest.json)
- [実装操作記録](reference_overlay/IMPLEMENTATION_NOTES.md)／[検査記録](test_report.md)／[機械検査](verification.json)
- [必要な部位だけを補完する次工程の候補](reference_overlay/NEXT_PARTS_PREPARATION.md)

## 今回の変更

参照原画は均一拡縮と平行移動だけで配置。Cubism内では2枚の下絵レイヤーを45%で重ねて比較し、原画の目の傾き・顔の中心線・顎先を目印にした。右向き用ガイドは形状比較のために反転したもの。モデル自身の茶／青の目と髪の非対称は反転していない。参照下絵は非表示・書き出し対象外にして保存した。

Head_TiltとHead_XYの間へHead_Oblique_Roll_XYを追加。AngleX/Y各3キーのうちX=-30/Y=-30で-6度、X=+30/Y=-30で+6度の傾斜を与え、左右の斜め下だけ位置を補正した。他の7キーは無変形。

Face_Contour_XYの既存5×5変換／4×4ベジェを再調整し、左右斜め下の2キーで顔下部と顎を短縮、頬の近側・遠側を別々に補正した。顔を平面のまま回転するだけではなく、耳下から顎へ向かう輪郭を変えている。Mouth_Align_XにYキーを追加し、閉口と口内の6ArtMeshを斜め下で上方へ追従させた。

目・耳・髪は既存の奥行き変形と新しい頭部傾斜に追従。今回はこれらの描画やメッシュ密度を新規に作り直していない。首の陰影も既存Neck_Shadow_Xを維持し、新しい顎裏の肌面は追加していない。肩・襟・胴体、完成PNG、既存PSD、髪物理設定は保持。

## 残っている原画との差

顎の縦長さと顔・口の傾きは修正前より目標へ近づいた。一方、原画の頬の丸み、耳内部の形、頬に掛かる横髪、顎下の陰影は完全には一致しない。原画の目の開き方や鼻の描画も正面採用絵と異なるため、顔全体を置き換えて一致させたとは扱わない。

次に必要なら、顔下地の頬〜顎、近側の耳、横髪・もみあげだけを抽出・補完する。判断箇所と条件は上記の次工程資料に整理した。今回のSampleで改善量を確認してから対象を絞る。

## 保存・検査

開始時のcmo3・runtime・preview・記録はarchive/before_tilted_reference_20260926に保持。Cubism Editor 5.3.04 FREEで保存→閉じる→再読込→SDK5.0書き出しを実施し、書き出し設定も再保存した。runtimeは48 ArtMesh／27パラメータ、編集側は14変形器と参照2レイヤー。アトラスは既存とハッシュ一致する2048×2048一枚。

正面の維持は、X=0/Y21位置×通常・閉眼・会話口の63条件を今回直前のruntimeと比較。透明な輪郭端でstraight RGBAの差が増幅したため、元の失敗記録を残し、白・灰背景合成で別途診断した。62条件は最大2/255以内、X0/Y-6/閉眼のみまつ毛端1画素で最大3/255。この限定例外を明記した表示比較と納品検査は合格。元PNG128枚と頭部・参照41枚、原画(2)、開始時バックアップのハッシュ保持、参照PSDの読戻し、runtimeと動画の整合も確認済み。完全なバイト一致や全頂点の一致を主張しない。詳細はverification.jsonおよびtest_report.md。

動画は実moc3から描画。0〜3秒が正面頷き、3〜6秒が左、6〜9秒が右、9〜12秒が複合動作。左右もY=-30の修正終点まで動かし、区間の境界は中立へ戻る。別途左右終点で瞬き・会話口・最大会話口を確認する。

髪物理は前工程のAngleZ入力を継続。休止からの緩やかな入力では髪出力0になる既存制限があり、別の強い診断入力で旧版と比較する。XY物理の追加、完全横顔、VTube Studio／nizima LIVE、販売品質の受入は今回の範囲外。

## 履歴

以前の詳細と比較はarchive内に保持。特にbefore_tilted_reference_20260926は今回直前、before_contour_direction_20260925等はさらに前の工程。古い回転正規化比較や「顎先を中央へ戻す」操作を現在の目標として再適用しない。正面頷きの受入と、最新斜め姿勢の確認待ちは区別する。
