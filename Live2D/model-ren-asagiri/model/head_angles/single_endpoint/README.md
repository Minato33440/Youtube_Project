# レン：顔下地の頬〜顎を原画へ合わせる

## 2026-09-26最新：全頭輪郭の下絵で顔下地を再調整

BossがCubismウィンドウを画面内へ戻した後、画面取得が復旧。`Looking_down (2)-outline.png`から作った5層の参照PSDを読み込み、X=-30／Y=-30のface_underfillの既存境界・内側頂点を調整した。今回の継続では再分割していない。耳根元から頬・顎へつなぎ、過大だった頭頂部を下絵へ合わせた。原画の傾きは保持。隠れる頭頂は推定、耳外周は別パーツとして扱う。

`Ren_face_endpoint.cmo3`を保存し、顔下地単体と全パーツのSDK5.0 runtimeを再書出し。実runtimeから比較を生成した。同一ガイドの可視顔輪郭344点では、4000×6000換算の中央値4.457→2.635px、90パーセンタイル14.333→7.279px、最大23.622→9.920px。髪に隠れる補完線275点の最大差は98.555→16.856px。前回の191点ガイドとは範囲が異なるため数値を混同しない。

- [最新版：下絵・調整前・調整後・重ね合わせ](whole_head_outline_check/whole_head_runtime_guide_4up.png)
- [中間姿勢](whole_head_pose_check/face_intermediate_poses_ja.png)／[顎の開口追従](whole_head_pose_check/face_jaw_opening_ja.png)
- [正面の頷き・口開閉の前後比較](whole_head_pose_check/front_mouth_preservation_ja.png)
- [編集可能モデル](Ren_face_endpoint.cmo3)／[今回の状態・ハッシュ](outline_retrace_status.json)
- [輪郭計測](whole_head_outline_check/whole_head_runtime_measurement.json)／[姿勢検証](whole_head_pose_check/whole_head_pose_checks.json)

正面5角度×口3段階の顔下地、全パーツでの正面2角度×口4段階は、今回のバックアップとの表示差0。ほか3姿勢の境界差も0。顔下地32条件を確認した。ただし頬の小さな段差と半透明の縁は残る。alpha>=16で終点は最大7行に外縁分離（2000×3000描画で1〜3px幅の隙間）、alpha>=64でX=-15/Y=-30は口4状態それぞれ1行に分離がある。完全な輪郭・三角形反転なしを保証する検査ではない。動画・物理の新検証は未実施。

今回開始前は `archive/before_whole_head_outline_20260926/` に保持。Cubismは正面中立・実パーツ表示・参照非表示で保存済み。保存後の閉じて再読込は今回未実施。まず顔下地の輪郭と残る縁をBossに確認してもらい、受入・追加修正が済むまで目・耳・髪・口の次工程や反対側への展開へ進まない。

## 前回：頬〜顎の頂点追加（以下は履歴）

2026-09-26更新。Boss指定で、片側の斜め頷き終点（X=-30／Y=-30）の顔下地だけを再調整。左右の頬〜顎と内側へ頂点を追加し、輪郭の角張りを抑えた。目・髪などの配置工程へは進んでいない。今回の輪郭SampleはBoss確認待ち。

- [原画・調整前・調整後の比較](dense_contour_check/cheek_jaw_comparison_ja.png)
- [顔下地だけの中間姿勢](dense_contour_check/face_intermediate_poses_ja.png)
- [口開閉に伴う顎の追従](dense_contour_check/face_jaw_opening_ja.png)
- [正面の頷き・口開閉の前後比較](dense_contour_check/front_mouth_preservation_ja.png)
- [編集可能な候補モデル](Ren_face_endpoint.cmo3)
- [検証と制約](test_report.md)／[機械検査・ハッシュ](verification.json)

## 今回の変更

前回候補をarchive/before_mesh_refinement_20260926へ保存してから、Cubism内のface_underfill ArtMeshを編集。頬の曲がる箇所に境界頂点、その内側に支えとなる頂点を追加して再接続した。X=-30／Y=-30で境界・内側・透明余白側の頂点を連動して調整し、肌面の局所的な伸びを抑えながら顎へつないだ。他のキーと親変形器を直接編集していないが、メッシュ再分割による描画差はある。

基準原画はart/Looking_down/Looking_down (2).png。傾きを保持し、4000×6000キャンバスへ均一倍率1.2904500571、原点(1404.8264,161.1169)で固定配置。モデルへ都合よく回転・拡縮していない。前回ガイドの画面右上側に髪の縁を含む区間があったため、今回は実際に見える肌の輪郭へ取り直し、髪に隠れる推定部分を数値評価から除外した。[新しい4層の参照PSD](dense_contour_check/dense_contour_reference_4000x6000.psd)をCubismへ読み込み、保存時・書き出し時は非表示にした。

原PNG・既存PSDは加工せず、比較画像の候補も実際の書き出しモデルから描画している。原画の顔を候補へ貼り替えたり、描画後に輪郭を変形したりしていない。

## 比較結果と残り

同じ新ガイドの可視輪郭191点で調整前後を測定。4000×6000座標換算の最短距離は、中央値7.75→2.83px、90パーセンタイル27.46→5.44px、最大36.52→6.91px。両頬の角張りと張り出しが改善した。古い25点ガイドの数値とは直接比較しない。

正面頷き・口開閉と中間姿勢を再確認した。顔下地32静止条件で大きな面の割れは見られず、正面5角度×口3段階の輪郭差は2000×3000描画で最大1px（元キャンバス換算2px）。全パーツでの正面頷きと口4段階も前後比較した。

ただし以前の18条件の厳密な表示一致検査は不一致。メッシュ再分割後は輪郭近辺に微小な描画差が出るため、「正面などが完全に同じ」とは報告しない。斜め終点の画面左頬と顎先には薄い半透明の縁が少し残る。alpha>=16では最大3行で微小な外縁の分離があり、alpha>=64では32条件すべて一続き。これは残存する縁の粗さで、消去済みとは扱わない。三角形の反転・重複の数値検査はSDK公開API不足で未実施。

今回の確認は顔下地の静止形状と補間位置。髪で隠れる上側輪郭、各パーツの終点位置、反対側の新しい輪郭、物理を含む連続動画は完成判定していない。全パーツ終点のpreview/candidate_endpoint_assembly_unadjusted.pngは未配置状態の内部資料で、今回の完成Sampleではない。

## 続き

まず顔下地の比較で頬〜顎の形と残る縁を確認する。輪郭の受入・必要な修正が済むまで目・口・耳・髪の次工程へ進まない。正式モデルへの昇格も保留。Cubismには保存した候補を正面中立・実パーツ表示・参照非表示で残した。

前回の比較と検査はarchive/before_mesh_refinement_20260926に保存。contour_checkと旧preview/single_endpoint_contour_review.pngは前回ガイドによる履歴で、最新版の入口はこのREADMEとdense_contour_check。
