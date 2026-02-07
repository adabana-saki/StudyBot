# StudyBot - AI搭載学習支援Discord Bot

ゲーミフィケーション、AIドキュメント解析、スマホ連携通知を統合した学習支援Discord Bot。

## 機能一覧

### 🍅 ポモドーロタイマー
- `/pomodoro start [topic] [work_min] [break_min]` - セッション開始
- `/pomodoro pause` / `resume` / `stop` / `status`
- ボタンUI、進捗バー表示

### 📝 学習ログ & 統計
- `/study log [duration] [topic]` - 学習時間を記録
- `/study stats [period]` - 統計表示（日次/週次/月次/全期間）
- `/study chart [type] [days]` - チャート生成（折れ線/棒/円グラフ）

### ✅ To-Do管理
- `/todo add` - モーダルでタスク追加
- `/todo quick [title] [priority] [deadline]` - クイック追加
- `/todo list [status]` - 一覧表示
- `/todo complete [task_id]` - タスク完了（+XP）

### ⭐ XP & レベルシステム
- `/profile` - プロフィール表示
- `/xp` - XP確認
- ポモドーロ完了: 10XP、タスク完了: 10-30XP、連続7日: 50XPボーナス

### 🏆 リーダーボード
- `/leaderboard [category] [period]` - ランキング表示
- カテゴリ: 学習時間 / XP / タスク完了数

### 🤖 AIドキュメント解析
- `/ai summarize [file] [detail_level]` - ファイル要約
- `/ai keypoints [file]` - キーポイント抽出
- SHA-256キャッシュ、1日10回制限

### 📱 スマホ通知
- `/nudge setup [webhook_url]` - Webhook設定
- `/nudge toggle [enabled]` - ON/OFF切り替え
- `/nudge test` - テスト通知

## セットアップ

### 前提条件
- Docker & Docker Compose
- Discord Bot Token（[開発者ポータル](https://discord.com/developers/applications)で取得）
- OpenAI API Key（AI機能用、任意）

### 起動手順

1. 環境変数を設定:
```bash
cd apps/discord-bot
cp .env.example .env
# .env を編集してDISCORD_TOKENなどを設定
```

2. Docker Composeで起動:
```bash
docker-compose up -d
```

### ローカル開発

```bash
cd apps/discord-bot
pip install -r requirements-dev.txt

# テスト実行
pytest --cov -v

# コード品質チェック
ruff check .
ruff format --check .
```

## 技術スタック

| 項目 | 技術 |
|------|------|
| Bot | Python 3.12 + discord.py |
| DB | PostgreSQL + asyncpg |
| AI | OpenAI API (GPT-4) + PyPDF2 |
| チャート | matplotlib |
| テスト | pytest + pytest-asyncio |
| CI/CD | GitHub Actions |
| デプロイ | Docker + docker-compose |

## アーキテクチャ

```
Cogs (プレゼンテーション層)
  ↓
Managers (ビジネスロジック層)
  ↓
Repositories (データアクセス層)
  ↓
PostgreSQL (永続化層)
```

## ライセンス

MIT
