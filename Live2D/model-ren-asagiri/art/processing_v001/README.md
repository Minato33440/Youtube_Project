# 現行素材について（2026-09-24）

正面頭部の最新は [head/parts](../head/README.md) のみ。ここのfront/partsには首・衣装・四肢を保持。旧顔・髪・耳PNGは [archive](../archive/20260924-old-head-assets/README.md)へ移動し、front/manifestの旧頭部パスは移動先へ更新した。下記の全身PSD・生成コード・検証結果は初期版の記録であり、現行頭部を反映していない。旧生成コードをそのまま再実行しない。背面素材は今回変更していない。

# レン：初期パーツ切り分け・配置 v001

2026-09-21。Bossの完成済み透過原画から、コードでPSD用パーツを作成。細部の修正はBossがエディターで行い、その後にリグへ進むための初期素材です。

## 成果物

| 面 | レイヤーPSD | 編集用モデル |
|---|---|---|
| 正面 | [51レイヤーPSD](front/Ren_front_parts_v001.psd) | [正面cmo3](../../model/parts_v001/Ren_front_parts_v001.cmo3) |
| 背面 | [22レイヤーPSD](back/Ren_back_parts_v001.psd) | [背面cmo3](../../model/parts_v001/Ren_back_parts_v001.cmo3) |

- 両方とも4000×6000、RGB 8bit。各PNGは透明余白をトリミングし、[正面manifest](front/manifest.json)／[背面manifest](back/manifest.json)の`left`・`top`に配置。座標は左上原点の元キャンバスpixelです。
- **R/Lはキャラクター本人の左右**。正面R＝画面左・茶色の瞳、正面L＝画面右・青色の瞳。背面では画面との対応が逆になります。
- 正面39層を表示、候補12層を非表示。背面22層は表示。背景レイヤーはありません。
- 生成物と原画は別フォルダ。11点の入力原画を変更していないことを[source_hashes.json](source_hashes.json)と[validation.json](validation.json)で確認しています。

## 切り分けた内容

正面：アホ毛、前髪中央・左右、横髪左右、後ろ髪、顔表面・額の下地、耳左右、眉左右、原画の白目・虹彩・上まつ毛、閉じ口、首、襟、袖、胴体、ベルト、上下腕・手・ズボン・靴の左右。

背面：アホ毛、後ろ髪中央・左右、頭と首の下地、耳左右、襟、袖、胴体、ベルト、上下腕・手・ズボン・靴の左右。

## 差し替え候補の使い方

`ALT_`は調整用の非表示素材です。見た目が原画と異なるため、通常顔の上に一括表示しないでください。

| 候補 | 表示時の切替 |
|---|---|
| `ALT_whole_eye_R/L` | 対応する`eye_white`、`iris_original`、`eyelash_upper_original`を非表示。別のALT瞳・まつ毛も同時には表示しない |
| `ALT_iris_R/L_*` | 元の虹彩を非表示。`FILL_eye_white_R/L`は目の層より下に配置済み。視線移動には白目の描き足しとCubism側のクリッピング設定が必要 |
| `ALT_eyelash_upper_R/L` | 元の上まつ毛を非表示。原画の目尻に合わせて幅・回転・曲線を微調整 |
| `ALT_mouth_interior`、`ALT_mouth_tongue`、`ALT_mouth_teeth_upper`、`ALT_mouth_open_outline` | `mouth_closed`を非表示にし、4層を表示。口内・舌・上歯・輪郭は独立 |

目6点はキャンバス上の目サイズに合わせた候補コピーとして取り込みました。高解像度の提供素材自体は`../../art_assets/eye_parts/`に保持しています。口は笑顔原画から口周辺だけを採取し、約75%に縮小して配置しています。下歯の独立素材は作っていません。

確認画像：[通常顔](inspection/front_assembled_head.png)／[開口候補](inspection/front_open_mouth.png)／[提供の目候補](inspection/front_eye_candidates.png)／[髪を隠した下地](inspection/front_under_hair.png)。開口・目候補の表示は検査画像の状態であり、保存モデルの通常表示は閉じ口＋原画の目です。

## Bossが仕上げる箇所

- 額・耳の補助原画と元の顔には位置・色・影の差が残ります。髪を隠した画像で見える額の継ぎ目、目尻・耳付け根・頬の残り線を修正してください。
- 髪・袖・腕・襟などの切断面は初期分割です。動かす方向に応じて毛束の根元や関節の隠れた部分を描き足す必要があります。
- 眉・目・閉じ口を除いた顔面は局所補完です。目や口を動かして露出する領域の塗りを整えてください。まつ毛に付随する肌色も調整対象です。
- 指は手のレイヤーにまとまっています。指別の分割、下まつ毛・上下唇の細分化、下歯の追加は今回行っていません。
- 初期ArtMeshの配置までです。変形用のメッシュ、デフォーマ、パラメータのキー、まばたき・口パク・物理演算、テクスチャアトラス、moc3やVTube Studio/nizima LIVEの設定は未作成です。背面への連続回転も未実装です。

## 再生成と検証

`tools/build_all.ps1 -Verify`で、元PNG→切り分け→座標manifest→PSD→検査を再実行できます。v001の生成物を上書きするので、手作業の修正版は別名・別フォルダに保存してください。

使用処理：`tools/prepare_ren.py`、`tools/validate_artifacts.py`、リサで使用した`output/live2d/risa_parts_v1/tools/build_psd.js`と`verify_with_psd_tools.py`。Pillow/NumPy、作業フォルダのOpenCV、既存のag-psd/pngjs/psd-toolsを使用。Cubismへの読み込み・保存はアプリUIで行います。

検査結果は[test_report.md](test_report.md)を参照。PSDの各層RGBA・位置・順序・表示状態を読み戻して確認し、別ライブラリによる描画も検査します。埋め込み合成プレビューと透明部分のRGB差は、実レイヤーの不一致と区別しています。
