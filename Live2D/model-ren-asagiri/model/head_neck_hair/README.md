# レン — 顎・首・髪の連動

2026-09-24。Boss了承済みの瞬き・会話用開口へ、顎連動、首の左右傾斜、髪の揺れを追加した初回実装。モデル保存・再読込・SDK書き出し・実モデル描画検査済み。動きの仕上がりはBossの確認待ち。

## 開くファイル

- **現在の編集モデル：[Ren_front.cmo3](Ren_front.cmo3)**
- [12秒MP4](preview/Ren_head_neck_hair.mp4)／[GIF](preview/Ren_head_neck_hair.gif)
- [動作14状態の比較](preview/head_neck_hair_review.jpg)／[顎と首の拡大](preview/jaw_neck_detail.jpg)
- [前回との正面比較](preview/neutral_comparison.jpg)
- [検査記録](test_report.md)／[機械検査結果](verification.json)

`../basic_expression/Ren_front.cmo3`は了承済みの基準として保持。このモデルを静止PSDから作り直さない。最新PNGの入口は引き続き`../../art/head/parts/`。

## 実装した動き

| 操作 | 内容 |
| --- | --- |
| ParamEyeLOpen / ParamEyeROpen | 既存の左右独立まばたきを継承 |
| ParamMouthOpenY 0〜1 | 了承済みの通常会話口に、顔下地の顎を控えめに下げる動きを追加 |
| ParamAngleZ -30 / 0 / 30 | 頭部を実角度約-6 / 0 / +6度に傾ける。目・口・耳・髪が追従し、首上部を変形。首下部と襟は固定 |
| ParamHairFront -1〜1 | 中央前髪とアホ毛。アホ毛は別の変形器で根元を保ち、同じパラメータを共有 |
| ParamHairSide -1〜1 | 左右の横髪をそれぞれの変形器で揺らす |
| ParamHairBack -1〜1 | 後ろ髪を控えめに揺らす |

物理演算はAngleZを入力する3グループをCubismへ読み込み・保存した。前髪＋アホ毛、横髪、後ろ髪へ出力し、60fps設定で書き出し済み。動画は傾斜・瞬き・口だけを入力し、**髪は書き出した物理演算が動かしている**。物理確認はCubismの「物理演算・シーンブレンド設定」で行う。通常編集画面では髪のパラメータを手動確認できる。

## 変形器の構成

Head_Tilt（Rotation）下に全頭部メッシュと以下の変形器を配置。閉眼用まつ毛と口内も同じ頭部に追従する。

- Jaw_Open（Warp）：face_underfillのみ。5×5／ベジェ2×2。開口1時に下中央制御点を作業画面36.9%で12px下げ、顎輪郭は約8画面px下がる。口メッシュそのものは今回変更していない。
- Hair_Front_Sway（Warp3）：中央前髪。上を支点、横3.3／縦2.8／柔らかさ3。
- Hair_Side_L_Sway（Warp4）、Hair_Side_R_Sway（Warp5）：上を支点、横2.8／縦1.5／柔らかさ3。
- Hair_Back_Sway（Warp6）：上を支点、横1.9／縦1.0／柔らかさ3。
- Ahoge_Sway（Warp7）：右の根元を支点、横4.4／縦2.9／柔らかさ3。

Neck_Follow（Warp2）はRoot下。neck-clavicleを保持し、AngleZの両端で上段制御点を左右10画面px・傾き±8画面px調整。中下段を固定。前髪L/Rの頭頂側は頭部へ追従する静的な土台として保持。

## 検査範囲と残る工程

48 ArtMesh、8変形器、書き出しパラメータID27個。2048×2048アトラス1枚。Cubism Editor 5.3.04 FREEで制作し、ローカル再生環境に合わせSDK5.0形式で書き出した。PRO体験版は開始していない。

正面中立の前回との差は最大1/255、8超の差のある画素0。元48PNGと基準cmo3のハッシュは保持。14状態と12秒動画の代表フレームで顎・耳・首・襟・髪根元を目視し、今回の小さな傾斜範囲では目立つ背景抜けや追従漏れは見られなかった。一般の全組み合わせや大角度まで保証する検査ではない。

未実装：AngleXの横向き、AngleYのうなずき、独立したアホ毛制御、大笑い用の追加開口、体・呼吸・追加表情。VTube Studio／nizima LIVEでの追跡・自動瞬き・リップシンク調整も未検証。現段階を販売完成とは扱わない。

## 次の作業

1. BossにMP4/GIFで顎の量・首の傾き・髪の柔らかさを確認してもらい、必要ならこのcmo3で調整。
2. 採用後、顔の左右向きと上下向きの実装範囲を決め、耳・首・髪の重なりを角度ごとに確認。
3. 大笑い追加開口や配信アプリ調整は別工程。

render_preview.pyは実moc3を描画し、比較と動画を再生成する。verify_delivery.pyは素材保持・出力参照・動画仕様を再検査する。どちらも元PNGとcmo3を変更しない。prepare_physics.pyは読み込み用物理JSONの生成のみで、実モデル更新にはCubismでの読み込み・保存・再書き出しが必要。

開始HEADはmainのfebf8ad（Blinking/Open_mouth 1st）。親Agentのみ、stage/commit/pushなし。途中のGUI干渉はBossの続行許可後に解消し、本工程を完了した。

