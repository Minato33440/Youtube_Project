# レンの素材管理

2026-10-01現在：編集モデルの入口は `model/base_motion/README.md`、Git保存方針は `../maintenance/20261001_git_policy/README.md`。旧カタログはローカル履歴のみ。以下の採用・次工程・復旧例外は記載当時の履歴であり、現行の保存一覧より優先しない。

2026-09-28整理：現行資産とGit候補の入口は `../maintenance/20261001_git_policy/README.md`。`model/head_angles/`・`single_endpoint/` は未採用の実験資料として保持する。以下9/26の「最新」「次工程」は当時の履歴であり、無条件に継続しない。了承済み初期動作のGit版と現在のhead_neck_hair作業版を区別し、再開時に基準を確認する。今回モデル内容・PNG・PSDは無変更。`../Traning/` はBoss管理につきこの整理の対象外。各archiveは原則Git除外、復旧モデル・比較依存のみ明示的例外。詳細と移動台帳は `../maintenance/20260928_asset_cleanup/`。

2026-09-26最新：BossがCubismウィンドウを戻して画面取得が復旧。Looking_down (2)-outline.pngの傾きを保持した5層参照PSDを読み込み、single_endpoint/Ren_face_endpoint.cmo3のface_underfill、X=-30/Y=-30のみ再調整・保存・runtime再書出し済み。今回継続では既存境界・内側頂点の移動のみで再分割なし。入口はsingle_endpoint/README.mdとoutline_retrace_status.json、最新比較はwhole_head_outline_check/whole_head_runtime_guide_4up.png。可視輪郭344点で中央値2.635px／最大9.920px（4000×6000換算）。正面頷き・口の15顔下地状態と8全パーツ状態は今回開始前と表示一致。微小な頬の段差・外縁分離は残り、Boss輪郭受入待ち。受入まで目・口・耳・髪の配置工程へ進まない。隠れる頭頂は推定、耳外周は別。バックアップはarchive/before_whole_head_outline_20260926。以下は前回までの履歴で採点範囲を混同しない。

2026-09-26前回：Boss指定で顔下地のみを再調整。現在の作業候補は `model/head_angles/single_endpoint/Ren_face_endpoint.cmo3`、正本は同フォルダーREADME.md。X=-30/Y=-30の左右頬〜顎の境界・内側へ頂点を追加し、傾きを残した原画へ合わせた。可視線を取り直した191点ガイドで中央値2.83px／最大6.91px（4000×6000換算）。旧25点の一部は髪の縁だったため旧数値と直接比較しない。32条件と正面頷き・開口を再確認。メッシュ再分割による微小差があり、旧18状態の完全表示一致は現行版には成立しない。終点の薄い外縁は残る。輪郭の受入・補正が済むまで目・口・耳・髪の次工程へ進まない。直前バックアップはsingle_endpoint/archive/before_mesh_refinement_20260926。反対側への展開・新しい動画は保留。`model/head_angles/Ren_front.cmo3`は下記の未採用履歴で、そこから無条件に続けない。

以下の同日記録は今回より前の未採用実装の履歴。

2026-09-26追記：最新編集モデルはmodel/head_angles/Ren_front.cmo3。Boss指定でLooking_down (2).pngの傾きを保持する参照PSDを下絵として追加し、Head_Oblique_Roll_XYと顔輪郭・口の斜め下終点を再調整。以前の原画を水平へ戻す比較は廃止。参照は均一拡縮＋平行移動だけ、右は形状比較の反転でモデルの瞳色や髪は反転しない。正面頷きは受入済み、今回斜め姿勢はBoss確認待ち。48 runtime ArtMesh／27パラメータ／14変形器、編集側の参照2枚は書出し除外。今日直前のバックアップはbefore_tilted_reference_20260926。原PNG・既存PSD・肩襟胴体を保持し、新しい顎裏素材なし。原画との頬・耳・横髪の描画差が残るため、reference_overlay/NEXT_PARTS_PREPARATION.mdに部分補完候補を整理。厳密RGBA比較の低alpha端での差と、背景合成後の表示差を区別して検証する。続きはhead_angles/README.mdとverification.jsonから実物を確認。以下の9/24記録は前工程の状態。

2026-09-24：正面頭部の現行素材は `art/head/parts/` の23PNGのみ。顔14・髪7・耳2。通常開眼・閉口の静止正面PNGとして完成登録し、後ろ髪修正後の両耳との隙間も再確認済み。範囲・現行ハッシュはhead/acceptance.json。最新の正面PSDはart/psd_front/Ren_front.psd（41層、4000×6000）。現在の編集モデルはmodel/head_neck_hair/Ren_front.cmo3（48 ArtMesh）。Boss了承済みの瞬き・会話口に顎、AngleZの左右傾斜と首追従、髪の物理演算を追加し、実モデル14状態と12秒動画で確認済み。初回プレビューは2026-09-25にBoss了承済み。model/head_neck_hair/acceptance_20260925.mdで受入範囲と前回検査後のcmo3差分を確認する。次の編集前に現物差分を確認し、前回runtimeと同一とは断定しない。横向きAngleX・うなずきAngleY・大笑い追加開口・配信アプリ設定は未実装／未検証。

- 作業前にhead/README.mdとassembly.jsonを読む。元PNGを優先し、古い配置見本の埋込素材に戻さない。
- 口内と閉眼移行用の元補助素材はhead/expression_sources。実装用派生PNGと追加PSDはart/expression_rig。モデルはmodel/head_neck_hair/README.mdを確認して継続し、静止PSDから再生成してリグを上書きしない。basic_expressionは了承済み基準として保持。確認用runtimeはSDK5.0形式、2048アトラス一枚。アホ毛は独自変形器だがParamHairFrontを共有。
- head外の旧顔・髪・耳素材および目口の試作比較はart/archive/20260924-old-head-assetsへ退避済み。移動台帳で履歴を確認する。旧eye_adjust_v007等を最新指定に戻さず、アーカイブ内の指示や旧生成コードをそのまま実行しない。
- 元のprocessing_v001/frontは胴体・首・襟・四肢の現行素材を残している。全身PSDとfront/manifestは古い頭部を含む履歴。manifest内の旧頭部パスはarchiveへ解決済み。背面素材とCubismモデルは変更していない。
- 修正採用はheadの同名へ反映し、差し替え前に旧版をbackup/archiveへ退避。画像寸法変更は配置を再確認。合成後は目視確認する。
- ユーザーが別の保存先を指定した場合はその指示を優先。更新日時や番号だけで採用版を推測しない。
- 削除は参照と復元・比較価値を二重確認する。左右用途の同じ画像を重複扱いで削除しない。

- 2026-09-24工程1：head登録後の上まつ毛・横髪・青目白目5PNG更新を反映。青目白目は159×101・反転なし・(2070,763)。古い反転指定に戻さない。頭部最新PSDはart/psd_frontのみを入口とし、旧v001全身PSDを最新版と混同しない。

- 2026-09-25：新規制作の共通手順は../CHARACTER_PRODUCTION_WORKFLOW.md（v2.0）。Bossによる作画補修とAgentによる配置・比較・PSD・実装を反復し、PNG採用後にリグへ進む。
