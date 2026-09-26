# Lesson 01 — PSD Import

## このLessonの目的

PSDをCubismへ読み込んだ瞬間に何が作られるのかを理解する。

このLessonでは、まだMesh編集・Deformer・Parameter・Keyformを作らない。
**「PSDのレイヤーがCubismのモデル構造へどう入るか」だけを確認する。**

## 教材に使うPSD

朝霧レンの現行正面PSDを使用する。

元資料上の仕様:

- ファイル名: `Ren_front.psd`
- 4000 × 6000 px
- RGB 8bit
- 透明背景
- 41独立レイヤー
- 通常開眼・閉口の静止配置版

Git上にはPSD本体が現在コミットされていないため、元のローカル保存版を**コピー**して使用する。

### 作業コピー名

`Ren_front_training_L01.psd`

推奨配置:

`Live2D/Traning/Lesson01_PSD_Import/work/Ren_front_training_L01.psd`

元の `Ren_front.psd` は変更しない。

## reference フォルダ

- `manifest.json` — 元PSDに使用したPNG、配置、重ね順の記録
- `psd_verification.json` — PSD読戻し検査
- `Ren_front_completed_reference.cmo3` — 後工程まで実装済みモデルの比較用。Lesson 01では編集禁止

## 実習 1 — 新規PSDを開く

1. Cubism Editorを起動する。
2. 本番CMO3は開かない。
3. `Ren_front_training_L01.psd` を新規モデルとして読み込む。
4. 読み込み直後は、変形・メッシュ編集・デフォーマ作成を行わない。
5. キャンバス全体を表示し、レンが正面中立姿勢で表示されることを確認する。

### ここで見るもの

- 全身の位置が中央から大きくずれていない
- 背景が透明
- 顔・髪・耳・首・襟・シャツ・四肢が欠けていない
- レイヤーの重なり順が元の静止合成と一致している
- 左右が反転していない

## 実習 2 — Parts / ArtMeshの対応を見る

PSDを読み込むと、PSDのレイヤーはCubism側のDrawable/ArtMeshとして扱うための素材になる。

この時点では「動くモデル」ではない。
**静止した各パーツに、Cubism側で変形を与えられる入口ができた状態**と考える。

確認すること:

1. Partsパレットで頭部・髪・目・口・首・衣服などの項目を見る。
2. キャンバス上で一つの部位を選択し、どの項目が選ばれるか確認する。
3. 選択した部位以外が勝手に一緒に選択されないことを見る。
4. まず3〜5部位だけ確認する。全41層を一度に整理し直さない。

推奨確認部位:

- 顔下地
- 前髪
- 片目
- 首
- シャツ胴体

## 実習 3 — 保存する

読み込み直後の状態を別名で保存する。

推奨名:

`Ren_training_L01_imported.cmo3`

これは今後のLessonの**基準点**になる。

### この保存で変更してよいもの

- CubismがPSDを読み込むために生成したモデル構造
- 保存ファイル名

### まだ変更しないもの

- Mesh形状
- Deformer
- Parameter
- Keyform
- Physics
- Texture Atlas
- 表情
- 角度変形

## Lesson 01 合格条件

以下を全て満たしたら完了。

- [ ] 教材PSDを本番PSDとは別名で使用した
- [ ] 4000×6000の正面モデルとして読み込めた
- [ ] 主要部位の重なりに大きな破綻がない
- [ ] Parts/ArtMeshの対応を最低3部位確認した
- [ ] Mesh/Deformer/Parameterをまだ編集していない
- [ ] `Ren_training_L01_imported.cmo3` として保存した
- [ ] 読み込み直後の全体スクリーンショットを残した

## Boss → UCAR に見せてほしいもの

Lesson 01の操作後、次の2枚があればレビューできる。

1. **全体表示** — レン全身とCubism UIが見える状態
2. **顔下地を1つ選択した状態** — Parts/ArtMeshとの対応が見える状態

その2枚を確認してからLesson 02「ArtMesh確認」へ進む。

## このLessonで理解したい一文

> PSD Importはリグではない。  
> 原画レイヤーを、Cubismで変形可能なモデル要素として受け入れる入口である。
