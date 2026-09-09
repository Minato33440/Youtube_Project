# Youtube_Project

YouTube 動画制作専用のリポジトリ。テーマ設計・素材選定・原稿・字幕・編集手順といった
**制作の設計・記録**を管理する。動画や音声などの大容量素材は Git 管理外に置く。

## 目的

複数の元動画から必要な発言を選び、前後にオリジナルのナレーション・画像・字幕を加えた
動画を制作する。制作の各工程（テーマ決定 → 素材選定 → 切り抜き → 原稿 → 音声 → 画像 →
字幕・統合編集 → 書き出し）を、後から再現・修正できる形で残すことを目的とする。

編集ソフトは Wondershare Filmora を使用する。ローカルでの編集と、外部サービスを利用する
画像・音声生成は区別して記録する。

## ディレクトリ構成

```text
Youtube_Project/
├── .venv/                       # Python 仮想環境（Git 管理外）
├── .gitignore
├── README.md
├── filmore_output/              # Filmora 書き出し先へのジャンクション（Git 管理外）
└── Politics_Economics/          # 分野ごとの作業場所
    ├── VIDEO_PRODUCTION_WORKFLOW.md   # 制作ワークフロー（工程・評価・整理案）
    └── YYYY-MM-DD_テーマ名/            # 動画 1 本ごとの作業フォルダー
        ├── brief.md             # セッションで決めたテーマ・方針
        ├── sources.md           # 元動画・公開日・利用条件・資料
        ├── cuts.csv             # 元動画の開始終了・配置順・採用理由
        ├── narration.md         # ナレーション原稿
        ├── media/               # 元動画・音声・画像（Git 管理外）
        ├── subtitles/           # 仮文字起こし・最終字幕
        ├── filmora/             # 編集プロジェクト（Git 管理外）
        ├── exports/             # 試作・完成動画（Git 管理外）
        └── test_report.md       # 操作成否・時間・修正・検証範囲
```

分野を増やす場合は、`Politics_Economics/` と同じ階層にフォルダーを追加する。

## Git で追跡するもの / しないもの

| 追跡する | 追跡しない（`.gitignore`） |
| --- | --- |
| ワークフロー・制作メモ（`*.md`） | 動画・音声ファイル（`*.mp4`, `*.wav` など） |
| カット表（`*.csv`） | 画像素材（`*.png`, `*.jpg` など） |
| 字幕ファイル（`*.srt`, `*.vtt`） | `media/` `exports/` `filmora/` |
| スクリプト（`*.py`） | Filmora プロジェクト（`*.wfp`） |
| 設定の雛形（`.env.example`） | `.venv/`、API キー・認証情報（`.env` ほか） |
| | `filmore_output/`（Filmora 書き出し先へのジャンクション） |

ドキュメント用の図版を追跡したい場合は `docs/images/` に置く。

## セットアップ

Python 3.13 で仮想環境を作成済み（`.venv/`。Git 管理外なので clone 後は各自で作成する）。

```powershell
# 作成（clone 直後の初回のみ）
python -m venv .venv

# 有効化（PowerShell）
.\.venv\Scripts\Activate.ps1

# 有効化（Git Bash）
source .venv/Scripts/activate
```

依存パッケージを追加したら、`pip freeze > requirements.txt` で固定してコミットする。

### 補助ツール

- **FFmpeg / FFprobe** — 素材の尺・コーデック確認、切り出し、音声抽出に使用（ローカルに存在を確認済み）。
- **Filmora 15** — 本編の編集・字幕・音声合成・書き出し。

### filmore_output/（Filmora 書き出し先のミラー）

`filmore_output/` は Filmora の既定の書き出し先へのディレクトリジャンクション。
実体は `%APPDATA%\Wondershare\Wondershare Filmora\Output\` で、双方どちらから
読み書きしても同じファイルを指す（コピーではない）。書き出した動画をエクスプローラーで
探しに行かず、プロジェクト内から直接扱うためのもの。

clone 直後は存在しないため、必要なら次のコマンドで再作成する（管理者権限は不要）。

```powershell
New-Item -ItemType Junction `
  -Path   "C:\Python\REX_AI\Youtube_Project\filmore_output" `
  -Target "$env:APPDATA\Wondershare\Wondershare Filmora\Output"
```

削除するときは `Remove-Item .\filmore_output -Force`（リンクだけが消え、実体は残る）。
`-Recurse` は付けないこと。

## 運用ルール

- 元動画の利用条件と、YouTube の再利用コンテンツに関する収益化基準は、制作とは別に確認する。
- 発信者の主張・確認できた事実・こちら側の考察を、原稿および記録の中で混同しない。
- 生成画像は背景や概念の説明に使い、実際の出来事の記録映像・写真と誤認させる表現を避ける。
- 認証情報・API キーはコミットしない。共有が必要な設定は `.env.example` に項目名だけ書く。
- YouTube へのアップロード・公開は、本リポジトリのワークフローの対象外（別途指示に基づいて行う）。

## 参照

- [Politics_Economics/VIDEO_PRODUCTION_WORKFLOW.md](Politics_Economics/VIDEO_PRODUCTION_WORKFLOW.md) — 制作ワークフローの詳細
