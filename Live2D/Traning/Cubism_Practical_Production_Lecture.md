# Cubism Practical Production Lecture

更新開始: 2026-09-26

## 目的

朝霧レンの既存素材を教材に、Cubism Editorでの制作工程をMinato自身が一度最初から最後まで通して理解する。
最終目的は職人作業の全てを手動化することではなく、Agent/Astraへ正確に指示し、結果を監督・受入できる判断力を持つこと。

## カリキュラム

1. **PSD Import**
2. ArtMesh確認
3. Mesh編集
4. Deformer作成・親子関係
5. Parameter作成
6. Keyform追加
7. 頂点／Deformer変形
8. 複数Parameterの組合せ確認
9. Physics
10. Texture Atlas
11. moc3 / model3.json書き出し

## 学習方針

各Lessonは次の流れで進める。

1. 目的を確認する
2. 教材コピーを開く
3. Cubism上で一つずつ操作する
4. 途中状態をスクリーンショットで確認する
5. 「何が起きたか」を言葉で整理する
6. 保存して次工程へ進む
7. 失敗・勘違いも記録する

## 重要な判断軸

この講義では操作手順だけでなく、次の判断を重視する。

- ArtMeshを直接変形すべきか、Deformerで変形すべきか
- Parameterは何を表す軸なのか
- Keyformはどの状態を固定しているのか
- 単独動作と複合動作で何が変わるのか
- Physicsの入力と出力をどう分けるか
- Editor内で成立することと、runtimeで成立することの違い

## 参照モデル

教材の基準キャラクターは朝霧レン。
本番モデルは直接編集せず、`Live2D/Traning/` 配下に作業コピーを置く。

現在の完成側比較用CMO3は
`Lesson01_PSD_Import/reference/Ren_front_completed_reference.cmo3`
として置くが、Lesson 01では編集しない。

## Lesson進捗

- [ ] Lesson 01 — PSD Import
- [ ] Lesson 02 — ArtMesh確認
- [ ] Lesson 03 — Mesh編集
- [ ] Lesson 04 — Deformer
- [ ] Lesson 05 — Parameter
- [ ] Lesson 06 — Keyform
- [ ] Lesson 07 — 頂点／Deformer変形
- [ ] Lesson 08 — 複数Parameter
- [ ] Lesson 09 — Physics
- [ ] Lesson 10 — Texture Atlas
- [ ] Lesson 11 — Runtime Export
