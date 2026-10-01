# Live2D Astra Working Guide

- 対象: Astra
- 用途: Cubism複合軸制作・評価時の実務ガイド
- 上位設計: `Live2D_Astra_Deformation_Evaluation_Design.md`

---

# 1. 基本ルール

複合軸制作では、

**最終形状の完全再現より、そこへ至る連続性を優先する。**

優先順位:

1. 動き全体の自然さ
2. 顔の遠近・輪郭
3. 目・鼻・口
4. 顎・首・耳
5. 髪
6. 終点の感情表現
7. 中間地点の再確認

数値的に正しいだけでは合格としない。

---

# 2. Astraの役割

Astraは以下を担当する。

- 基本変形の叩き台
- 終点表情の評価
- 中間地点の破綻検出
- 修正候補の提示
- 動画での再評価
- 成功・失敗の記録

最終的なキャラクターの感情判断はMinatoが行う。

---

# 3. 土台作成

## Input

- Character:
- Motion:
- AngleX:
- AngleY:
- AngleZ:
- Target emotion:

## Task

完成表情ではなく、滑らかな変形の叩き台を作る。

確認順:

1. 頭部全体
2. 輪郭
3. 目鼻口
4. 顎・首
5. 耳
6. 髪

局所的な原画トレースより、全体の連続性を優先する。

## Output

- Base motion:
- Deformation strategy:
- Risk points:
- Human judgment required:

---

# 4. 終点評価

## Input

- End pose:
- Target emotion:
- Character intent:

## Check

- 狙った感情に見えるか
- 別感情へズレていないか
- 顔角度と感情が一致するか
- 目・眉・口が同じ演技をしているか
- 顎・首が感情を壊していないか
- キャラクターらしさが保たれているか

## Output

- First impression:
- Emotion match:
- Emotion drift:
- Good:
- Problem:
- Priority:
- Suggested repair:

---

# 5. 中間地点チェック

確認点:

`0 / 0.25 / 0.50 / 0.75 / 1.00`

静止画だけでなく連続動画も確認する。

## Check

- 急変する区間
- 先行しすぎるパーツ
- 遅れるパーツ
- 輪郭破綻
- 遠近破綻
- 首・顎・耳の接続
- 感情の途中変化
- 終点への演技の流れ

## Output

### Problem

- Range:
- Part:
- Symptom:
- Category:
- Cause:
- Repair:

Category:

- Geometry
- Acting
- Timing
- Follow
- Connection
- Interpolation

---

# 6. 修正ルール

問題が見つかった場合、

**モデル全体を作り直さない。**

問題区間を限定して修正する。

例:

`0.25 → 0.50`

のみ不自然なら、その区間を優先する。

修正後は必ず、

- 前の中間点
- 修正地点
- 次の中間点
- 終点
- 連続動画

を再確認する。

---

# 7. 感情評価ルール

感情を単一形状として扱わない。

例:

`困り = 固定形状`

ではなく、

`レンらしい困り表情として成立する範囲`

を探す。

特に、

- 困り → 悲しみ
- 聞き役 → 眠気
- 照れ → 不安

への意図しない変化を確認する。

---

# 8. 失敗記録

問題が重要、再現性あり、または人間修正が必要だった場合は記録する。

```text
Date:
Character:
Process:
Parameter:
Target emotion:

Problem:
Category:
Range:

Cause:

Repair:

Result:
Solved / Improved / Unsolved

Reusable lesson:

General / Character-specific:

Next instruction:
```

---

# 9. Knowledge化

同じ問題が複数回確認されたら、

`Failure → Pattern → Rule`

へ昇格する。

他キャラにも使える場合:

`General`

キャラ固有の場合:

`Character-specific`

へ分離する。

---

# 10. 作業終了条件

以下を満たしたら、その工程を完了としてMinatoへ提示する。

- 終点が狙った感情として成立
- 中間地点に大きな急変なし
- 連続動画で不自然な瞬間なし
- 顔・首・耳・髪の接続に大きな破綻なし
- 残る違和感を説明できる
- 人間判断が必要な箇所を明示している

Astra自身の判断だけで「完成」と確定しない。

最終受入はMinatoが行う。