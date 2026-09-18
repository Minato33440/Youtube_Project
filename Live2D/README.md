# Live2D — 仮の制作・再利用拠点

更新: 2026-09-16。Bossとの合意を残す入口。現在は `Youtube_Project` 内の仮運用であり、独立リポジトリ化・素材移管は未実施。

## 方針と決定済みのこと

「構造を決めてから動くのではなく、動きながら必要に応じて構造化する」。まず初回キャラクターのリサを完成させ、その実績を Repository-centered Knowledge Production の最初の Reference Implementation にする。

- 当面は本書から既存のモデル・入力設定・再生成手順・検証記録を参照する。実データの正本は各リンク先に置き、同じ資産の正本を増やさない。
- 既存の Filmora・Cubism の参照を保つため、素材の移動や改名は資産化の実装時に依存関係と復元方法を確認してから行う。
- 初回完成後に、実際に再利用できるデータとキャラクター固有の調整を分ける。現時点で分類用の空フォルダーや共通基盤を先行して作らない。
- 保存対象は成功した出力だけでなく、再生成に必要な入力・処理・設定、失敗の再現条件、検証結果、Bossの評価と採用理由。会話を短く要約した文章だけで置き換えない。

## 現在地と既存データへの入口

以下は所在を確認した参照先。今回の文書作成で再生成や再検査を実行したものではない。

| 対象 | 入口・位置付け |
| --- | --- |
| 日本語音素の時刻データ | [音素整列](../output/live2d/voice_sync_v2/alignment/phonemes.json) — 今回の音声に対応する入力 |
| 口の開閉・横幅・丸め | [v3の検証と再生成手順](../output/live2d/voice_sync_v3/test_report.md) |
| まばたき・呼吸・首との連動 | [v4の検証と再生成手順](../output/live2d/voice_sync_v4/test_report.md)、[manifest](../output/live2d/voice_sync_v4/manifest.json) |
| 演技の設定・時系列 | [入力設定](../output/live2d/voice_sync_v4/performance_profile.json)、[CSV](../output/live2d/voice_sync_v4/performance_curve.csv)、[motion3](../output/live2d/voice_sync_v4/performance.motion3.json) |
| 編集用モデル | [Risa_coordinated.cmo3](../output/live2d/voice_sync_v4/Risa_coordinated.cmo3) — リグを保持。上記の演技時系列は別ファイル |
| 全編用のナレーション別出力 | [full_sample_v1](../output/live2d/full_sample_v1/) — N01〜N05 の設定・モーション・描画記録 |
| コードによる元動画への合成 | [検証記録](../Politics_Economics/2026-09-09_fiscal_policy/code_edit/sample_v1_risa/test_report.md) |
| Filmora修正版試作 | [WFP](../Politics_Economics/2026-09-09_fiscal_policy/filmora/Risa_Layered_Trial_20260915_MotionFixed.wfp)、[MP4](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Layered_Trial_20260915_MotionFixed.mp4) |
| Filmoraの静止不具合と修正 | [原因・修正・検査記録](../Politics_Economics/2026-09-09_fiscal_policy/code_edit/sample_v1_risa/filmora_motion_fix_report.md)、[動きの検査コード](../work/verify_filmora_motion.py) |
| N01のサイズ・動作調整（2026-09-16） | [約16秒のMP4](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Narration_N01_SizeMotion_Adjusted_v1.mp4)、[調整内容・検証・再生成](../output/live2d/narration_adjustment_v1/test_report.md) — 表示1.5倍、開口1.2倍、首2倍、すぼめ55％。Bossが配置・顔から首の動きを「概ね良くなった」と評価 |
| 胸部呼吸v1（2026-09-16） | [モデル単独・音声付き約16秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v1.mp4)、[呼吸のみ約8秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v1.mp4)、[リグ変更・検証・再生成](../output/live2d/chest_breath_v1/test_report.md) — Bossは「胸部の動きも肩の動きもほとんど分からない」と評価。動作検出の合格だけでは視認性を保証しなかった例として保持 |
| 胸部・肩の呼吸を強めたv2（2026-09-16） | [モデル単独・音声付き約16秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v2.mp4)、[呼吸のみ約8秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v2.mp4)、[編集用cmo3](../output/live2d/chest_breath_v2/Risa_chest_breath.cmo3)、[リグ変更・検証・再生成](../output/live2d/chest_breath_v2/test_report.md) — Bossは体幹上部全体と頸部の上下動が不自然と評価。強度を上げるだけでは局所性を満たさない失敗例として保持 |
| 首元を固定した局所呼吸v3（2026-09-16） | [モデル単独・音声付き約16秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v3.mp4)、[呼吸のみ約8秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v3.mp4)、[編集用cmo3](../output/live2d/chest_breath_v3/Risa_chest_breath.cmo3)、[リグ変更・検証・再生成](../output/live2d/chest_breath_v3/test_report.md) — 全体伸縮を停止し、衣服メッシュと8×9の局所変形を再構成。襟中央の移動0px、最大域で肩各16px・胸幅269→282px。Bossは上腹部の連動を確認し、下腹部と上部ニットの皺の連動追加を依頼 |
| 上下ニットの皺を追加した呼吸v4（2026-09-16） | [呼吸のみ約8秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v4.mp4)、[モデル単独・音声付き約16秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v4.mp4)、[編集用cmo3](../output/live2d/chest_breath_v4/Risa_chest_breath.cmo3)、[変更・検証・再生成](../output/live2d/chest_breath_v4/test_report.md) — 現在の原画のまま、Body_Clothesの6頂点を呼吸に連動。最大域で上部の皺が約4px、ベルト上の皺が約3px変化。襟上端・顔・ベルトを維持。技術検査合格、Bossの自然さの視聴評価待ち |
| ニットの上下方向反転v5・比較候補（2026-09-16） | [v4/v5の左右同時比較・約8秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Breath_Direction_Compare_v4_v5.mp4)、[反転版単独・呼吸のみ](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v5.mp4)、[音声付き約16秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v5.mp4)、[編集用cmo3](../output/live2d/chest_breath_v5/Risa_chest_breath.cmo3)、[変更・検証・再生成](../output/live2d/chest_breath_v5/test_report.md) — Bossの提案により6頂点の追加上下変位のみ反転。吸気時は首元上・腹部下。胸・肩・左右方向・呼吸曲線は維持。技術検査合格、自然さの比較評価待ち |
| 喉の内部の皺を中央へ寄せるv6（2026-09-16） | [喉〜胸部の拡大比較v5/v6・約8秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Throat_Folds_Compare_v5_v6.mp4)、[呼吸のみ単独](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v6.mp4)、[音声付き約16秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v6.mp4)、[編集用cmo3](../output/live2d/chest_breath_v6/Risa_chest_breath.cmo3)、[変更・検証・再生成](../output/live2d/chest_breath_v6/test_report.md) — Bossが良好と評価したv5の腹部を維持。喉元の上下移動を解除し、外形を保ちながら内部の皺を左右から中央へ寄せる。技術検査合格、喉と胸のつながりの視聴評価待ち |
| 喉の内部の皺を強めたv7（2026-09-16） | [v6/v7の拡大比較・約8秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Throat_Folds_Compare_v6_v7.mp4)、[呼吸のみ単独](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v7.mp4)、[音声付き約16秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v7.mp4)、[編集用cmo3](../output/live2d/chest_breath_v7/Risa_chest_breath.cmo3)、[変更・検証・再生成](../output/live2d/chest_breath_v7/test_report.md) — v6はBossが動き不足と評価。内部2頂点の中央寄せのキー変位を約3倍に拡張。外形・襟上端・腹部・胸肩・演技曲線を維持。技術検査合格、v7の視認性・自然さは視聴評価待ち |
| タートルネック上部の皺を追加したv8（2026-09-16） | [v7/v8拡大比較・約8秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Throat_Folds_Compare_v7_v8.mp4)、[呼吸のみ単独](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_BreathOnly_v8.mp4)、[音声付き約16秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_ChestBreath_v8.mp4)、[編集用cmo3](../output/live2d/chest_breath_v8/Risa_chest_breath.cmo3)、[変更・検証・再生成](../output/live2d/chest_breath_v8/test_report.md) — v7で動きが出たとの評価を受け、上部内部1頂点の横方向変形を追加。襟上端・輪郭と胸肩腹部を維持。技術検査合格、v8の視聴評価待ち |

### Bossの評価と確認範囲

2026-09-17、Bossが PunctuationPause v1 を通し試聴し「発語の間と呼吸が大分自然になった」と評価。今回の間・呼吸設定を日本語音声合成モデル共通の制作側暫定プリセットとして記録し、リサの口・目・首・呼吸を人間型モデルの調整開始値として保存した。[暫定プリセットの入口](presets/README.md)。共通タイミング、人間型の初期値、リサ固有の形状・可動域・配置と由来を分離。別音声・別キャラクターの試験は未実施。既存ビルダーへの自動読込は未実装で、今回の作業は記録と採用状態の更新。

2026-09-17追加：[句読点別の間・モデル単独約15.3秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_PunctuationPause_v1.mp4)、[設定・再生成・検証](../output/live2d/punctuation_pause_v1/test_report.md)。読点と文中の追加休止を0.12秒、通常文末0.50秒、問いかけ後0.70秒へ編集。発語のPCMとモデル形状を保持し、口・首・まばたきを時刻変換、呼吸は文末に再配置。技術検査合格、Bossの通し試聴評価待ち。暫定基準であり別音声・別モデルでの汎用検証は未実施。

2026-09-17追加：[発語に合わせた呼吸v1・音声付き約16秒](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_ModelOnly_SpeechBreath_v1.mp4)、[v8との同時比較](../Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_SpeechBreath_Compare_v8_v1.mp4)、[設計・検証・再生成](../output/live2d/speech_breath_v1/test_report.md)。Bossの実装依頼に基づき、v8の形状を固定してParamBreathだけ変更。8か所の実音声休止内で速めに吸気し、発語を含む間の区間はゆっくり呼気。短い吸気は浅め、冒頭は吸った状態、終端は落ち着いた状態。技術検査合格、初回の自然さ評価待ち。

- 2026-09-17、Bossはv8について「呼吸時の全体の動きは取りあえずこの位でいい」と評価。呼吸の変形量を暫定採用。次の相談は音声付きサンプルの時間配分で、休止中に比較的速く吸気し、発語中にゆっくり呼気する案。変形量の受入とタイミング案の実装は区別し、この記録時点では呼吸曲線の変更は未実施。
- 本対話で、口の自然さは「凡そ良し」、その後の連動は「控えめだけど自然な動き」と評価済み。
- 2026-09-16、Bossは胸部呼吸v5の腹部を「良い感じ」と評価。喉元は上下移動から中央へ皺を寄せる案へ進め、v6で比較。腹部の評価を喉元やモデル全体の完成判定へ拡張しない。
- 2026-09-16、Bossはv6の喉の皺を「ほとんど動いていない感じ」と評価。動きを検出できても視認性の合格を意味しない例として残し、v7で局所変形を強めた。v7の受入は未判定。
- 2026-09-16、Bossはv7を「大分動きは出てきてる」と評価。タートルネック上部の皺だけをさらに足す依頼を受け、v8を作成。v7の評価は視認性改善についてのもので、モデル全体の完成判定には拡張しない。
- 2026-09-15、本対話で Filmora 修正版試作について「今度は問題なさそうだね」と評価。試作の確認結果として記録し、全編の Filmora 化や初回キャラ全体の完成宣言には拡張しない。
- リンク先の当時の報告に残る「Bossの判定未実施」は報告作成時点の状態。上記はその後の受入記録であり、再検査の実施を意味しない。
- v4時点の呼吸は簡易的な微小伸縮。2026-09-16の胸部呼吸候補では衣服に専用の変形を追加した。首は軽い左右の傾き。別モデルでの再利用、ライブの顔トラッキング、任意の外部アプリでの再生は今回の受入範囲に含まれない。細部と検証限界は各報告を参照する。

## 初回完成後に実装すること

最初の到達点は、長い会話履歴を渡さなくても、入力音声・モデル版・設定・処理手順から同じ演技を再生成し、既知の検査と見比べられる状態。必要なツールの版、外部素材、ハッシュと復元手順を実行確認とともにそろえる。大きな原画・音声・動画の保管方式はその際に選び、参照リンクだけをバックアップとは扱わない。

Bossの例示した Japanese Speech Motion / Universal Motion / Archetype Presets / Character Overrides / Rigging Data / Evaluation / Failure Boundaries / Decisions は、現段階では整理の観点として扱う。

- 日本語音声ごとの音素・休止の時刻と、共通化候補の変換ルールを区別する。
- Universal Motion → Archetype Preset → Character Override の考え方で、一般的な動きと体型・表現、個別リグの補正値を分ける。ただしリサ1体で確認できたものは共通化候補であり、別キャラで確認するまで汎用性が実証済みとはしない。
- まばたきの選択や強調時の首振りは演出判断であり、音声から直接観測した生理データと混同しない。
- 失敗は症状・入力版・再現条件・修正・検出方法を結び付ける。今回の Filmora の静止問題は、音声とデコードが正常でも映像の動きは別途検査が必要だった実例として保持する。

## 将来の全体アーキテクチャ検討

参照: [LLM Orchestrator Repository-centered Migration Design v1](<C:/Python/REX_AI/REX_Brain_Vault/raw/system_build/LLM Orchestrator Repository-centered Migration Design v1.md>)。設計提案であり、現行運用を一括で変更する指示ではない。

検討の軸は User ↔ Astraなどの担当Agent ↔ Project Repository。制作資産の正本は各プロジェクトに置き、Obsidianは横断索引やメモ、NotebookLMは資料の調査・比較に使う。Hermesは必要なProvider・専用機能への接続に使い、search → coordination → broker の固定経路をすべての作業の前提にしない。

既存構造を変える判断は、実作業で支障が確認された箇所ごとに行う。権限、処理の停止・復元、責任範囲、評価の根拠は移行先でも保持する。UCAR/REXの個人的な記憶と制作資産の移管は別の判断として扱う。本書では Vault、Hermes、既存AGENTS.md の改修・停止を行っていない。

次の制作作業では本書を入口に現在の成果物を確認し、初回キャラを完成させる。資産化は完成時に必要な内容から実装する。
