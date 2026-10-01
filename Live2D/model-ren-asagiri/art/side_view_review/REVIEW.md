# レン横顔原画・切り出し素材レビュー

2026-09-25。対象は `art/head_side_view/` の10 PNG。画面左向きの `person-1.png` は青目、画面右向きの `person-2.png` は茶目で、正面現行素材の「キャラクター左＝画面右が青、キャラクター右＝画面左が茶」と矛盾しない。両方とも同じレンの横顔候補として扱う。10枚は `C:/Users/Setona/Desktop/head_side_view/` の同名ファイルとSHA-256が一致した。元画像は変更していない。

比較に使った現行正面は `art/head/preview/head_sample.png`（1110×1170）と `art_assets/ren-stand-pony-front-4000x6000.png` および `art/head/reference/ren-stand-pony-front-4000x6000.png`。補助参照として `art/full_body_side_view/close-up-face/close-up-face-{1,2,3}.png`、`anime-boy/anime-boy-{1,2}.png`、`short-dark-blue-hair/short-dark-blue-hair-{1,2}.png` を画面表示して見た。横顔と正面の画素単位の位置合わせ・色差計算、Cubismでの変形・重ね順・遷移試験はしていない。

## 判断

現時点の小さな Angle X/Y と頷きには、これらの横顔画像の直接導入は必須ではない。横顔は奥行き、輪郭、髪の流れ、耳と襟の位置を参照する資料として有用。一方、10枚だけでは90度横顔の独立リグは組めない。`person-*` は完成像を丸ごと含み、`dark-blue-hair-*`・目・襟を同時に重ねると描画が二重になる。正面の現行23頭部PNGと自動で置き換えない。

## 修正・整理項目

| 優先度 | ファイルと領域 | 観察 | 次の作業 |
| --- | --- | --- | --- |
| 直接使用前に必須 | `blue-eye/blue-eye-2.png`、`brown-eye/brown-eye-1.png`、`brown-eye/brown-eye-2.png` | `blue-eye-2` は茶色の**眼全体**。`brown-eye-1` も茶色の眼全体で、見た目は近いがハッシュは異なる。`brown-eye-2` は茶色の虹彩だけ。色名と機能が混在し、誤った側への割当や二重描画につながる。 | 原画で採用する茶目を確定し、「左向き青目の眼全体」「右向き茶目の眼全体」「右向き茶目の虹彩」等、向きと機能を示す台帳を作る。不要と判断するまではどれも削除しない。青目側の虹彩だけが必要なら新規分離を検討する。 |
| 直接使用前に必須 | `dark-blue-hair/dark-blue-hair-1.png` の前髪の下・耳穴周辺・襟上の毛先、`dark-blue-hair/dark-blue-hair-2.png` の顔開口・毛先 | 髪単体の透過画像に肌色の細片が残る。髪だけを動かすと、その細片が顔や耳から離れて浮く可能性がある。 | 髪ではない肌色を髪レイヤーから取り除き、必要な肌・耳・首側の下地へ移す。透明背景と明暗背景で拡大確認し、動かすメッシュの外周に肌色が残らないことを確かめる。 |
| 直接使用前に必須 | `dark-blue-hair/dark-blue-hair-{1,2}.png` の頭頂アホ毛の先端・根元、前髪の細い先端 | 独立した髪画像ではアホ毛の弧が途切れた点・細片に見え、根元と頭頂の接続も安定しない。`person-*` の完成像では目立ちにくい。 | 原画を見ながら線と根元を連続させる。揺らすならアホ毛を独立パーツ化し、頭頂との重なり代を描き足す。前髪先端の不要な小片も整理する。 |
| 横顔をリグ化する前に必須 | `person/person-{1,2}.png` の顔・耳・首・髪・シャツ全域 | 一枚の完成像。目・髪・襟の別PNGは存在するが、顔下地、耳、首、後頭部の独立素材はこの10枚にない。髪や耳が回転して露出する隠れ面も確認できない。 | `person-*` を見本にして採用方向ごとに顔下地・耳・首・後頭部・前後髪を分け、髪の下、耳の裏、顎下、首と襟の重なりを描き足す。小角度では必要な露出分だけに範囲を絞り、90度横顔用の全面分離は別工程にする。 |
| 胴体を含む横顔に使う前に必須 | `white-collared-shirt/white-collared-shirt-{1,2}.png` の襟下・肩下の切断面 | 襟と上胸部の切り出しで、下端は画像境界で切れている。`person-*` 内のシャツも胸上部だけ。 | 首・襟の重ね順と隠れ面を定める。全身へ使う場合は `art/full_body_side_view/` の胴体側素材を別途評価し、衣装の接続を制作する。 |
| 参考資料としては可 | `person-{1,2}.png` と現行正面プレビュー | 髪型、左右の瞳色、白シャツは同じ意匠。横顔の目・鼻・顎の描写や髪のハイライトは、現行正面の拡大顔と異なる画面条件・切り出しで、自然な中間角度になるかは静止画だけでは判断できない。 | 小さな Angle X/Y の実モデルを正面基準で確認し、横顔資料は輪郭と奥行きの参考に使う。大きく回す段階で中間角度のサンプルを描き、Bossに意匠のつながりを見てもらう。 |

「必須」は該当PNGを独立した可動パーツとして直接採用する場合の条件。現在の小角度実装を停止させる意味ではない。`person-*` と各パーツの位置関係は座標付きPSDで未照合。`blue-eye-2` と `brown-eye-1` は視覚上似ているが、完全重複とは判定していない。

## 確認対象の寸法とSHA-256

すべてRGBA。寸法は切り出しPNGそのものの幅×高さ。ハッシュは後日の差分確認用。

| `art/head_side_view/` 以下 | 寸法 | SHA-256 |
| --- | --- | --- |
| `blue-eye/blue-eye-1.png` | 82×67 | `4949ced386c1e9f012f1ab9223e85f1ca7d83b09fc70673f1e0f62abd13c2a40` |
| `blue-eye/blue-eye-2.png` | 106×73 | `2f123b575d352a783d41fb4b29433d624478c2b21877202a1addd805a6379528` |
| `brown-eye/brown-eye-1.png` | 99×72 | `8e5a5c7cc00b29402a3f0fa87d671ac450dd7932cf3d5caf8ddc0e5c28b75a18` |
| `brown-eye/brown-eye-2.png` | 29×61 | `f728c17fab72b642ed28676d337152e0c951bd42aa8df1c46a555c2e86b26770` |
| `dark-blue-hair/dark-blue-hair-1.png` | 623×642 | `f64735783dde885939e521d99f974a22859904e0376a877109c5a7211d803cc0` |
| `dark-blue-hair/dark-blue-hair-2.png` | 622×646 | `208f33e86d6738df38b7750618a11fab7da4776c82542c21f86e508ede3f0a06` |
| `person/person-1.png` | 624×904 | `154001ef15cfc59c83bf2c6d099db54b4e0a3e11fe2e8a950679b30d973de47a` |
| `person/person-2.png` | 625×904 | `2f704ce44c96d33e9e0ba16feeb3173be0b3f122e415445d1e82d8ef135aaa8f` |
| `white-collared-shirt/white-collared-shirt-1.png` | 413×236 | `adc09bb06239b36bb464539b5bcb2f662a05e52927ef9b527aad63f41a2111d6` |
| `white-collared-shirt/white-collared-shirt-2.png` | 408×236 | `b7ada48a508bf1e8dbde02f064c151a85d1beeb96097fcebcf4c933fad609865` |

検査は画像の画面表示、Pillowでの寸法・RGBA・SHA-256読取り、Desktop原本とのハッシュ照合。修正画像の生成、PSD統合、Cubism取込み、動画での動作確認は未実施。
