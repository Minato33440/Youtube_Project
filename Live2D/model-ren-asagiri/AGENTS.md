# レンの素材管理

2026-09-24：正面頭部の現行素材は `art/head/parts/` の23PNGのみ。顔14・髪7・耳2。通常開眼・閉口の静止正面PNGとして完成登録し、後ろ髪修正後の両耳との隙間も再確認済み。範囲・現行ハッシュはhead/acceptance.json。最新の正面PSDはart/psd_front/Ren_front.psd（41層、4000×6000）。現在の編集モデルはmodel/basic_expression/Ren_front.cmo3（補助7枚追加、48 ArtMesh）。瞬き・会話用開口は実装・実モデル描画確認済み、Bossの仕上がり確認待ち。顎・顔首角度・髪揺れは未実装。

- 作業前にhead/README.mdとassembly.jsonを読む。元PNGを優先し、古い配置見本の埋込素材に戻さない。
- 口内と閉眼移行用の元補助素材はhead/expression_sources。実装用派生PNGと追加PSDはart/expression_rig。モデルはmodel/basic_expression/README.mdを確認して継続し、静止PSDから再生成してリグを上書きしない。確認用runtimeはSDK5.0形式、2048アトラス一枚。
- head外の旧顔・髪・耳素材および目口の試作比較はart/archive/20260924-old-head-assetsへ退避済み。移動台帳で履歴を確認する。旧eye_adjust_v007等を最新指定に戻さず、アーカイブ内の指示や旧生成コードをそのまま実行しない。
- 元のprocessing_v001/frontは胴体・首・襟・四肢の現行素材を残している。全身PSDとfront/manifestは古い頭部を含む履歴。manifest内の旧頭部パスはarchiveへ解決済み。背面素材とCubismモデルは変更していない。
- 修正採用はheadの同名へ反映し、差し替え前に旧版をbackup/archiveへ退避。画像寸法変更は配置を再確認。合成後は目視確認する。
- ユーザーが別の保存先を指定した場合はその指示を優先。更新日時や番号だけで採用版を推測しない。
- 削除は参照と復元・比較価値を二重確認する。左右用途の同じ画像を重複扱いで削除しない。

- 2026-09-24工程1：head登録後の上まつ毛・横髪・青目白目5PNG更新を反映。青目白目は159×101・反転なし・(2070,763)。古い反転指定に戻さない。頭部最新PSDはart/psd_frontのみを入口とし、旧v001全身PSDを最新版と混同しない。
