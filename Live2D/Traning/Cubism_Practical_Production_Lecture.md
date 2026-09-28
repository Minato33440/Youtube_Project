# Cubism Practical Production Lecture

更新: 2026-09-28

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

# Lesson進捗

- [x] Lesson 01 — PSD Import
- [x] Lesson 02 — ArtMesh確認
- [x] Lesson 03 — Mesh編集
- [x] Lesson 04 — Deformer + Parameterの役割確認
- [x] Lesson 05 — Keyform
- [x] Lesson 06 — Keyform上でのDeformer + ArtMesh補正
- [x] Lesson 07 — 複数Parameterの組み合わせ
- [ ] Lesson 08 — Physics
- [ ] Lesson 09 — Texture Atlas
- [ ] Lesson 10 — Runtime Export

## 次回

Lesson 08では、髪揺れ等を題材に、

- Physicsの入力Parameter
- 出力Parameter
- 振り子設定
- 揺れの収束
- 手動Parameter操作と実Physicsの違い

を確認する。
