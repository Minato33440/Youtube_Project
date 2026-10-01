# Cubism Practical Production Lecture

更新: 2026-09-30

## 目的

朝霧レンの既存素材を教材に、Cubism Editorでの制作工程をMinato自身が一度最初から最後まで通して理解する。

最終目的は職人作業の全てを手動化することではなく、**Agent/Astraへ正確に指示し、結果を監督・受入できる判断力を持つこと**。

本書は実習側の正本とし、Lessonごとの操作、失敗、修正、気づきを残す。別キャラへ再利用する製造原則は ../CHARACTER_PRODUCTION_WORKFLOW.md へ蒸留する。

## 現行カリキュラム

1. **Lesson 01 — PSD Import**
2. **Lesson 02 — ArtMesh確認**
3. **Lesson 03 — Mesh編集**
4. **Lesson 04 — Deformer + Parameterの役割確認**
5. **Lesson 05 — Keyform**
6. **Lesson 06 — Keyform上でのDeformer + ArtMesh補正**
7. **Lesson 07 — 複数Parameterの組み合わせ**
8. Lesson 08 — Physics
9. Lesson 09 — Texture Atlas
10. Lesson 10 — moc3 / model3.json書き出し
11. Lesson 11 — 髪揺れのキーフォームを手動／自動生成で作る

## 学習方針

各Lessonは次の流れで進める。

1. 教材コピーを別名保存する
2. 目的を1つに絞る
3. Cubism上で一つずつ操作する
4. スクリーンショットで途中状態を確認する
5. 「何が起きたか」を言葉で整理する
6. 失敗・誤解・修正方法も残す
7. Lessonの学びをWorkflowへ蒸留する

本番の Live2D/model-ren-asagiri/ は直接編集せず、教材は Live2D/Traning/ 配下のコピーを使う。

---

# Lesson 01 — PSD Import

## 目的

PSDの各レイヤーがCubismへ取り込まれた時に、どのようにモデル要素へ変わるかを確認する。

## 教材

最初に、完成原画保存用PSDを誤って読み込んだ。このPSDはパーツ分離版ではなく、Cubism上では数レイヤーしか現れなかった。

この失敗から、教材には**Live2D用に可動パーツごとに分離されたPSD**が必要だと確認した。

最終的に使用した教材：

- Ren_front_training_L01.psd
- 元データ：4000×6000、41独立レイヤー
- Cubismでは1/2解像度（2000×3000）で読み込み

## 操作

1. Cubism EditorでPSDを新規モデルとして開く
2. 読み込み直後はMesh、Deformer、Parameterを変更しない
3. Parts / ArtMeshの対応を確認する
4. face_underfill、前髪、虹彩、衣服など複数部位をクリックし、PSDレイヤー名とCubism上の選択対象が一致することを確認
5. 読み込み直後の状態を基準CMO3として保存する

## 確認できたこと

- PSDの各可動パーツレイヤーが、Cubism上で独立したArtMeshとして扱われる
- Parameter一覧が表示されていても、Keyformがなければ動作は未実装
- 完成原画PSDとCubism Import用PSDは用途が違う

## 失敗・気づき

**失敗**：完成原画保存用PSDを教材として読み込んだ。

**学び**：Cubism Import PSDでは、全パーツを1枚に統合するのではなく、**1可動パーツ = 1独立レイヤー**を維持する。

---

# Lesson 02 — ArtMesh確認

## 目的

ArtMeshと、その内部のMeshが別の概念であることを実物で確認する。

## 操作

face_underfill、ALT_iris_L_blue、hair_front_C をそれぞれ手動メッシュ編集モードで確認した。

## 結果

3パーツとも、PSD Import直後は概ね**四隅4頂点 + 対角線の2三角形**という最低限のMeshだった。

## 理解した構造

~~~text
PSD Layer
  ↓
ArtMesh
  ↓
Mesh（Vertex / Edge / Triangle）
~~~

- **ArtMesh**：画像を変形対象として扱う単位
- **Mesh**：ArtMesh内部で実際に変形を伝える網

ArtMeshが存在していても、実用的な変形用Meshが完成しているとは限らない。

## 気づき

同じArtMeshでも必要なMesh密度は用途で違う。

- 顔下地：輪郭・頬・顎など局所変形が多い
- 虹彩：主に移動なら粗くてもよい
- 前髪：根元〜毛先方向の変形が重要

---

# Lesson 03 — Mesh編集

## 目的

自動Mesh生成と手動補正の役割を理解し、実際に画像変形へつながるMeshを作る。

## 1. 自動生成

face_underfill に対して自動Mesh生成を実施。最初はプリセット「標準」を使用した。

確認項目：

- 顔輪郭に沿って外周頂点が配置されるか
- 顎先に頂点があるか
- 頬〜顎の三角形が自然につながるか
- 内部に極端な細長い三角形がないか

## 2. メッシュ編集モードと通常編集の違い

最初、メッシュ編集モードで頂点を動かしても画像が変形しなかった。

これは正常で、メッシュ編集モードは**トポロジーの配置を編集するモード**だった。

- メッシュ編集モード：頂点・辺・三角形を配置する
- 通常モデリング：確定Meshの頂点を動かし、画像そのものを変形する

通常編集へ戻って顎や頬の複数頂点を動かすと、囲われた領域全体が滑らかに変形することを確認した。

## 3. 「標準」と「変形度合い（大）」比較

同じ顔下地で比較したところ、「変形度合い（大）」は輪郭・内部とも頂点密度が高く、頬〜顎の変形がより滑らかだった。

ただし、**高密度 = 常に高品質**ではない。

良いMeshの判断基準：

1. 特徴点に頂点がある
2. 変形方向に頂点が連続している
3. 三角形が極端に細長くない
4. 必要以上に高密度ではない
5. Deformerの仕事までMeshへ背負わせない

## 4. 手動補正

顎先、左右顎角、頬〜耳下の流れを手動調整した。

調整後に、顎先周辺、頬〜顎角、左右輪郭の領域変形をテストし、輪郭が滑らかなことを確認した。

## Lesson 03の結論

**Meshは静止状態だけで完成判定せず、実際の変形と往復しながら仕上げる。**

---

# Lesson 04 — Deformer + Parameterの役割確認

## 目的

ArtMeshを直接動かす方法から一段上がり、複数ArtMeshをDeformer階層でまとめる考え方を理解する。

## 1. Face_Warp作成

顔面パーツ群をまとめるWarp Deformerを作成。

重要な気づき：

**Warpの枠の中に画像が入っていることと、そのArtMeshがWarpの子であることは別。**

Deformerパレットで各ArtMeshを Face_Warp 配下へドラッグし、インスペクタでも親Deformerを確認した。

Warpの格子を動かすと、配下のArtMesh群がまとめて柔らかく変形することを確認した。

## 2. Rotation Deformer追加

Face_Warp の親に Face_Rotation_Practice を作成。

~~~text
Face_Rotation_Practice
└─ Face_Warp
   └─ face / eyes / brows / mouth / ears ...
~~~

比較：

- Warp：形を歪ませる
- Rotation：形を比較的保ったまま回転させる

Angle Zのような頭部傾斜はRotation主体が扱いやすいことを体感した。

## 3. Rotation支点

最初は顔中央付近に支点があり、回転すると不自然だった。

支点を首中央まで下げると、今度は頭全体が大きな円弧で動きすぎた。

最終的に、**顎下〜上位頸部付近**へ調整すると首の上で頭が傾く感覚に近づいた。

子を追従変形させずRotation Deformer自身の基準位置だけを調整する操作も確認した。

## 4. Parameterの役割確認

既存の Angle Z Parameterを動かしても、Keyform未登録では何も動かないことを確認。

- Parameter = 数値軸
- Deformer = 実際の変形構造

という違いを確認した。

---

# Lesson 05 — Keyform

## 目的

Deformerの形をParameter上の特定値へ登録し、スライダー操作で再現可能にする。

## 操作

Angle Z に3点Keyformを追加：

- -30
- 0
- +30

Face_Rotation_Practice は、

- Angle Z = -30 → Rotation -15°
- Angle Z = 0 → 0°
- Angle Z = +30 → Rotation +15°

として登録した。

Parameter値とRotation実角度は同一である必要はない。

## 中間補間確認

Angle Z = +15でRotationが概ね+7.5°となり、中間姿勢が自動補間されることを確認した。

## Lesson 05の結論

~~~text
Parameter = 状態の数値軸
Keyform   = 特定値での形
Deformer  = 実際の大きな変形
~~~

---

# Lesson 06 — Keyform上でのDeformer + ArtMesh補正

## 目的

同じParameter上で、Rotation、Warp、ArtMeshがそれぞれ独立したKeyformを持ち、同時補間されることを確認する。

## 操作例

~~~text
Angle Z = +30
├─ Face_Rotation_Practice：+15°
├─ Face_Warp：+30側の全体補正
└─ mouth_closed：+30側の局所補正
~~~

その後、Angle Zを +30 → +15 → 0 と動かした。

## 結果

- Rotationの傾き
- Face_Warpの補正
- mouth_closed ArtMeshの局所補正

が同一Angle Z上で同時に補間されることを確認した。

## Lesson 06の原則

1. Rotationだけで自然なら追加補正しない
2. 全体の形状差が残る場合だけWarp
3. 局所差だけ残る場合にArtMesh
4. 中間値まで動かして補間結果を確認する

**Rotation → Warp → ArtMesh** の順で降りる。

---

# Lesson 07 — 複数Parameterの組み合わせ

## 目的

単一Parameterごとの変形から進み、複数Parameterが同時に作用した時の自然さと干渉を確認する。

主な対象：

- Angle Z
- Eye Blink（左右）
- Eye Smile（左右）
- Mouth Open
- Mouth Form

## 1. Eye Blink

左右それぞれに専用Deformerを作り、開閉を5点で設定。

- 0.0 = 閉眼
- 0.25
- 0.5
- 0.75
- 1.0 = 開眼

Deformerで大枠を作り、上まぶた・下まぶた・白目・虹彩・まつ毛等のArtMeshで各中間を微調整した。

確認：

- 左右独立で瞬きできる
- Face Rotationと共存できる
- 中間値で急な潰れや跳ねがない

## 2. Eye Smile

Blinkとは別に、左右の笑顔Parameterを設定。

- Blink = まぶたの開閉
- Smile = 感情として目を細める

似た形でも目的を分離すると、ウインク・閉眼・笑顔目を独立制御できる。

## 3. Mouth Open / Mouth Form

口では次を分離した。

- Mouth Open = 発声・開口量
- Mouth Form = 感情方向

Mouth Form：

- -1 = 不満・不機嫌寄り
- 0 = 中立
- +1 = 笑い寄り

Mouth FormとMouth Openを重ねることで、閉口表情だけでなく会話中の感情差を確認した。

## 4. 不満口の複合補正

初期状態では、Mouth Form = -1 と大きな開口を重ねると、開口側の明るい形へ引っ張られて「不満口」が曖昧になった。

そこでMouth Form = -1を固定した状態で、Mouth Openの複数中間値（例：0 / 0.3 / 0.5 / 0.8 / 1.0）ごとに口ArtMeshを調整した。

これにより、

- 閉じた不満口
- 不満げに話す口
- 大きく開いても笑って見えない口

という連続性が改善した。

## 5. 複合表情確認

確認した代表状態：

- 片目閉じ + 開口
- Angle Z + Blink
- Angle Z + Smile
- Eye Smile + Mouth Form
- Eye Smile + Mouth Form + Mouth Open
- 中立 → 中間 → 終点

## Lesson 07で得た感覚

- 単独で正しい形が、複合でも正しいとは限らない
- まずDeformerで方向を作り、ArtMeshで中間・局所を詰める
- 非線形な変化では中間Keyformが重要
- Parameterごとの責務分離が、複雑な表情を扱いやすくする
- 全組み合わせを作り込まず、実運用で多用する帯域から優先する

---

---

# Lesson 08 — Physics

## 目的

手動で作った揺れParameterを、別Parameterの変化から時間差付きで自動駆動するPhysicsの仕組みを理解する。

## 1. 前髪の出力Parameterを準備

階層を整理した。

~~~text
Face_Rotation_Practice
└─ Hair_Base_Warp
   └─ HairFrontC_Warp
      └─ hair_front_C
~~~

HairSwing_Front_Practice を -1 / 0 / +1 で作成し、根元をなるべく固定、毛先ほど大きく動く左右揺れを作った。

この時点ではPhysicsを使わず、手動スライダーで滑らかに往復できることを確認した。

## 2. Physicsグループ作成

Physics_HairFrontC_Practice を作成。

~~~text
入力：Angle Z
種別：角度
影響度：100%
    ↓
Physics
    ↓
出力：HairSwing_Front_Practice
振り子：No.1
倍率：1.0
~~~

前髪では「髪（短い）」プリセットを起点にした。

Angle Zをゆっくり動かすと揺れは小さく、速く動かすと前髪が遅れて揺れ、行き過ぎてから収束することを確認した。

## 3. 振り子パラメータの感触

数値を変えて比較した。

- 長さを伸ばす → ゆったり大きい揺れ
- 反応速度を下げる → 入力に遅れて追従
- 収束を遅くする → 余韻が長く残る

ここから、Physicsは「揺らす/揺らさない」ではなく、遅れ・慣性・収束で部位の質感を設計する機能と理解した。

## 4. アホ毛を別Physicsへ分離

アホ毛専用に、

~~~text
Hair_Base_Warp
└─ Hair_ahoge_Warp
   └─ hair_ahoge
~~~

を作り、前髪とは別Parameter・別Physicsグループへ分離した。

同じAngle Z入力でも、

- 前髪：短く比較的安定
- アホ毛：軽く大きめに揺れ、余韻を残す

という別の物理特性を作れることを確認した。

## 5. Parameterレンジ変更で起きた失敗

アホ毛Parameterを最初 -30 / 0 / +30 で作成したため、Physics出力が可動範囲に対して小さく、見た目の揺れが分かりにくかった。

Keyform形状を維持したまま -1 / 0 / +1 へ変更し、Parameter本体の最小・最大も -1 / +1 へ修正した。

その際、親Deformer側のParameterを変更した後、hair_ahoge ArtMesh側のKeyform紐づけが消え、途中で画像が表示されなくなる症状が出た。

ArtMesh側にも -1 / 0 / +1 のKeyformを作り直すと復旧した。

## Lesson 08の結論

- Physicsの前に出力Parameterの手動変形を完成させる
- 同じ入力でも部位ごとに別Physicsを持たせられる
- Parameterレンジ変更時はDeformerとArtMeshの両方を確認する
- Physicsは形状設計ではなく時間応答設計である

---

# Lesson 09 — Texture Atlas

## 目的

Runtime用Texture Atlasが、モデル画像をどのように再配置・縮小し、最終画質へ影響するかを確認する。

## 1. Atlas作成

FREE版環境で 2048 × 2048 / 1枚 を作成。

自動レイアウト後、全ArtMeshは概ね 57.82% の倍率で配置された。

hand_L など一部はAtlas内の空間効率のため90°回転して配置されたが、これはAtlas上の格納方向でありモデル上の表示方向とは別。

## 2. 配置検証

- 重なりを検出
- 枠からのはみ出しを検出

を実施し、該当ArtMeshが選択されなかったため自動配置に問題なしと判断した。

## 3. 画質確認

Atlas確定後にモデリング画面へ戻り、虹彩などを拡大確認。

元画像100%に対して約57.82%へ縮小されたことで、特に虹彩の細線や高周波ディテールに解像感低下が目視できた。

## Lesson 09の結論

Texture Atlasは単なる画像の詰め合わせではなく、限られた解像度をどのパーツへ配分するかという画質設計である。

本番では顔・目・口・前髪を高優先とし、2048一枚で不足する場合は4096等の大きいAtlasや複数Atlasを検討する。

---

# Lesson 10 — Runtime Export / VTube Studio

## 目的

Cubism Editorの編集モデルをRuntime用一式へ書き出し、外部アプリで実際にロードできることを確認する。

## 1. 書き出し設定

既存レン環境との互換性を優先し、SDK 5.0形式で書き出した。

有効化した主な項目：

- physics3.json
- physics3.jsonへ計算FPS
- cdi3.json
- テクスチャ色漏れ防止
- 書き出しターゲット：1/1（2048px）

## 2. 出力結果

~~~text
Ren_training_L10_deformer01.moc3
Ren_training_L10_deformer01.model3.json
Ren_training_L10_deformer01.physics3.json
Ren_training_L10_deformer01.cdi3.json
Ren_training_L10_deformer01.2048/
└─ texture_00.png
~~~

## 3. model3.json確認

model3.json がRuntime一式の入口になっていることを確認。

~~~text
Moc      → .moc3
Textures → .2048/texture_00.png
Physics  → .physics3.json
DisplayInfo → .cdi3.json
~~~

EyeBlink / LipSync Groupsは空配列だったため、本番では標準Groupやアプリ側Parameter mappingを別途確認する。

## 4. VTube Studioで実機確認

model3.json をVTube Studioへ読み込み、モデル表示に成功。

Live2D Itemとしても読み込み、

- Angle Z
- Keyformを持つ表情・目・口
- 前髪Physics
- アホ毛Physics

がRuntime側で反映されることを確認した。

VTube Studioでは、通常モデルの設定とLive2D Item化後の設定は別系統として扱われることも確認した。

## Lesson 10の結論

書き出し成功だけでは完成ではない。model3.jsonの参照確認と、実Runtimeアプリでのロード・Parameter・Physics確認までをRuntime exportの受入条件とする。

---

# Lesson 11 — 髪揺れのキーフォームを手動／自動生成で作る

## 目的と実例

Lesson 08でBossが行った「3点パラメータの終点を手で変形し、Physicsで揺らす」方法と、2026-09-30にAstraがレンの制作モデルで使ったCubismの［揺れの動きを自動生成］を比較する。**両者の違いは主に、揺れパラメータの各キーフォームの形をどう作るか**にある。時間差の揺れを与えるPhysicsは、どちらの方法でも別に設定する。

今回の制作モデルは [`model/base_motion/Ren_base.cmo3`](../model-ren-asagiri/model/base_motion/Ren_base.cmo3)。教材コピー `Ren_deformer1.cmo3` から作成した制作側の作業モデルであり、Lesson 01〜10の教材原本を更新したものではない。Bossの報告では、Astraは今回の髪揺れ作成時に［揺れの動きを自動生成］を使用した。保存モデルの構造と検証範囲は [base_motion/README](../model-ren-asagiri/model/base_motion/README.md) と [test_report](../model-ren-asagiri/model/base_motion/test_report.md) を参照する。自動生成ダイアログで使った推定値・支点・横縦の振幅・柔らかさの正確な値は、現行の作業記録からは確定できない。

## 二つの作り方

| 工程 | BossのLesson 08：手動3点キー | Astraの今回の制作：自動生成を利用 |
| --- | --- | --- |
| 形状作成 | 前髪の出力Parameterを-1 / 0 / +1にし、根元を保ちながら両端のWarp Deformerを手で変形 | 対象のWarp Deformerと出力Parameterを［揺れの動きを自動生成］へ登録し、推定した揺れ形状をキーフォームへ反映。必要なら生成後に形を調整 |
| 時間変化 | Angle Zを入力、前髪Parameterを出力とするPhysicsを別に設定 | 生成したキーだけでは時間差の揺れは生じない。Angle Z入力から横髪・後ろ髪のParameterを駆動するPhysicsを別に設定 |
| 調整の中心 | 左右終点の輪郭、毛先の可動量、根元・隣の髪との接続を直接作る | 推定タイプ・支点・横縦の揺れ量・柔らかさ等で初期形を作り、同じ箇所を目視して補正する |
| 向く場面 | 非対称な毛束、原画に合わせた局所的な調整、少数パーツの精密な仕上げ | 対象が多いときの初期形作成や、一般的な髪揺れのたたき台 |

Lesson 08の前髪は `HairFrontC_Warp` を `HairSwing_Front_Practice` の3点で手動変形してから、`Angle Z → Physics_HairFrontC_Practice → HairSwing_Front_Practice` と接続した。今回の制作モデルでは、`Hair_Side_L_Sway` / `Hair_Side_R_Sway` が `ParamHairSide` の-1 / 0 / +1、`Hair_Back_Sway` が `ParamHairBack` の-1 / 0 / +1に接続されている。Physicsは既存の中央前髪・アホ毛2グループを保持し、横髪・後ろ髪を足した4グループが保存されている。横髪左右は同じ出力Parameterを共有しているので、別々の物理出力としては扱わない。

## Cubismの自動生成を使う手順と注意点

1. 元モデルを別名で保存し、動かすArtMeshを含むWarp Deformerと、その揺れ専用の出力Parameterを決める。回転Deformerはこの機能の対象外。
2. ［モデリング］→［パラメータ］→［揺れの動きを自動生成］を開き、Warp Deformerを登録してParameterを選ぶ。推定タイプの［髪揺れ］を起点に、支点と横・縦の揺れ量、柔らかさ、必要なら左右非対称を調整する。
3. ［キーフォームを更新］で形を反映し、-1 / 0 / +1と中間値を手動スライダーで往復させる。対象Parameterのキーが0点または3点以外の場合、確認でOKすると既存キーを削除して3点を作り直すため、保持したい形があれば先に複製する。
4. 根元、耳・頬・襟との重なりを確認し、生成形が合わない部分はWarp Deformerを手で直す。自動生成は初期形の補助であり、キャラ固有の自然さの判定は代行しない。
5. 形が成立した後に物理演算設定で入力・出力・振り子を設定し、ゆっくりした動きと速い動きの両方で遅れ・行き過ぎ・収束を確認する。モデルを保存・再読込してから、必要な段階でRuntimeも検証する。

今回の `Ren_base.cmo3` は、Editor内で横髪・後ろ髪の端点と4物理グループの保存を確認した段階。本番アトラスを保留したためRuntimeは書き出しておらず、物理演算を含む連続動作、配信アプリでの再現、Bossの最終受入は未確認。アホ毛の形・キー・既存PhysicsはBossの作り直し対象として保持した。

Bossが後で実習する場合は、制作モデルを複製した練習用ファイルで横髪の3点キーを手動で一度確認し、自動生成後の同じキーと中間値を比較する。根元の安定、毛先の軌道、顔との重なりを見て、必要な箇所だけ手で直す。最後にPhysicsのプレビューで遅れと収束を比べる。制作モデルのキーを直接上書きしない。

## Lesson 11の結論

「揺れの動きを自動生成」は**揺れの形をキーフォームへ作る工程**を助ける。Bossの手動3点キー方式と競合せず、生成した形を手で直してから同じPhysics工程へ進める。形の自然さ、入力への反応、Runtimeでの再現はそれぞれ別に確認する。

参照：[Live2D公式・揺れの動きの自動生成](https://docs.live2d.com/cubism-editor-manual/auto-generation-of-sway-motion/)、[Live2D公式・物理演算について](https://docs.live2d.com/cubism-editor-manual/physics-operation/)。

---

# 全体総括 — PSDからRuntimeまで一周して得たこと

今回の講義では、朝霧レンの教材コピーを使い、以下を実際に一周した。

~~~text
PNG原画
↓
分離PSD / Cubism Import PSD
↓
ArtMesh / Mesh
↓
Deformer階層
↓
Parameter / Keyform
↓
Deformer + ArtMesh多層補正
↓
複数Parameter / 表情
↓
Physics
↓
Texture Atlas
↓
moc3 / model3.json / physics3.json
↓
VTube Studio
~~~

最も大きな学びは、Live2D制作を「終点画像へ形を合わせる作業」ではなく、階層と責務を設計し、連続変形・複合状態・Runtimeまで含めて成立させる工程として理解できたこと。

## 技術的に整理できた責務

- Mesh：局所変形の網
- Rotation Deformer：大きな回転・傾き
- Warp Deformer：面全体の柔らかい補正
- 局所Deformer：目・口・髪など部位単位
- Parameter：状態軸
- Keyform：その軸上の形
- ArtMesh：最後の局所補正
- Physics：別Parameterの変化から時間差付きで出力を駆動
- Texture Atlas：Runtime画質の配分
- model3.json：Runtime一式の入口

## 制作判断として得たこと

1. 静止原画への完全一致より、0→中間→終点の自然さを優先する
2. 参照原画は正解輪郭ではなく演技方向のガイド
3. 大きな変形から小さな補正へ降りる
4. 中間が自然ならKeyformを増やさない
5. 非線形部分だけ中間Keyformを追加する
6. 単独Parameterだけでなく、実用上多い複合状態を確認する
7. Physicsは部位ごとに分け、質感を設計する
8. Editor内の成立とRuntimeの成立を別に検証する

---

# Astraとの協働ガイド

今回の目的はBossが全工程を手作業することではなく、Astraへ正しい単位で仕事を渡し、結果を監督できる状態になることだった。

## Astraに任せやすい

- コードによる初期パーツ分離
- PSD組立・座標・manifest
- Mesh自動生成
- Deformer階層作成
- Parameter / Keyformの定型登録
- 指定値での端点作成
- Physics入出力グループ作成
- Texture Atlas自動配置・検証
- Runtime export
- JSON参照検査
- スクリーンショット・比較画像・テストログ作成

## Bossが主導する

- 原画らしさ
- 輪郭・髪・耳・目・口の最終品質
- Deformer支点
- どこまで動かすか
- 中間姿勢の自然さ
- 感情表現
- 複合Parameterの採否
- Physicsの質感
- Atlas画質配分
- 商品としての最終受入

## Astraへの指示テンプレート

~~~text
Goal:
  対象動作を実装する

対象:
  Deformer / ArtMesh / Parameter

階層:
  親 → 子

Parameter:
  名前 / min / default / max

変更可:
  明示する

変更禁止:
  PSD差替え / Mesh再生成 / 他Parameter等

参照:
  原画 / 既存Keyform / comparison

確認:
  端点 / 中間 / 複合Parameter / Runtime

合格条件:
  自然さ / 隙間なし / 跳ねなし / 指定Runtimeで再現
~~~

## Computer Useの使い分け

Computer Useへ細かな輪郭トレースや大量の頂点選定を丸投げしない。

向く作業：

- Deformer作成
- 親子階層
- Parameter / Keyform
- 物理演算設定
- Atlas
- export
- 定型確認

人間レビューを残す作業：

- 数px単位の頂点
- 輪郭
- 表情
- 原画の印象
- 演技の自然さ

---

# 今回の失敗から残すチェックポイント

- 完成原画PSDとパーツ分離PSDを混同しない
- Mesh編集モードと通常頂点変形を混同しない
- Deformer枠内にあることと親子関係を混同しない
- Parameter値と実際のDeformer角度を同一視しない
- Keyform値とParameter本体のmin/maxは別設定
- Parameterレンジ変更後は子ArtMeshのKeyformも確認する
- Physicsは出力Parameterの手動動作を先に完成させる
- Atlas倍率を見ずに画質合格にしない
- export成功だけでRuntime合格にしない

---

# Lesson進捗

- [x] Lesson 01 — PSD Import
- [x] Lesson 02 — ArtMesh確認
- [x] Lesson 03 — Mesh編集
- [x] Lesson 04 — Deformer + Parameterの役割確認
- [x] Lesson 05 — Keyform
- [x] Lesson 06 — Keyform上でのDeformer + ArtMesh補正
- [x] Lesson 07 — 複数Parameterの組み合わせ
- [x] Lesson 08 — Physics
- [x] Lesson 09 — Texture Atlas
- [x] Lesson 10 — Runtime Export / VTube Studio
- [ ] Lesson 11 — 髪揺れの手動3点キーと自動生成の比較（教材を追加。Boss自身の自動生成実習とRuntime・最終受入は未了）

## 修了時点

Boss自身でPSD ImportからVTube Studio実機確認までを一周し、Astraへ任せる作業と人間が判断すべき作業の境界を具体的に説明・監督できる状態まで到達した。
