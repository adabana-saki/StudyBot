# StudyBot

AI搭載学習支援プラットフォーム。Discord Bot / Web / モバイルアプリから学習を管理・ゲーミフィケーションで継続をサポートします。

## 主な機能

| カテゴリ | 機能 | 説明 |
|----------|------|------|
| 🍅 学習管理 | ポモドーロ / 学習ログ / To-Do / フォーカスモード | タイマー・記録・タスク管理を一元化 |
| ⭐ ゲーミフィケーション | XP・レベル / 実績 / リーダーボード / デイリークエスト | 学習を続けるほど成長を実感できる仕組み |
| 🪙 経済システム | StudyCoin / ショップ / アイテム装備 | 学習報酬でアイテム購入・カスタマイズ |
| 🤖 AI支援 | ドキュメント要約 / クイズ生成 / 学習プラン / 週次インサイト | OpenAI連携で学習を効率化 |
| 👥 ソーシャル | スタディレイド / チーム / バディマッチ / チャレンジ / タイムライン | 仲間と一緒に学習 |
| ⚔️ チームバトル | チーム対抗戦 / 貢献度ランキング / リアルタイムスコア | チーム同士の学習バトルで競争 |
| 🏠 スタディルーム | バーチャル学習空間 / VC連携 / 集合目標 | Discord VCとWebで同じルームに参加 |
| 📊 サーバー分析 | エンゲージメント / 離脱リスク / コミュニティ健全性 | 管理者向け分析ダッシュボード |
| 📱 クロスプラットフォーム | Discord Bot / Webダッシュボード / モバイルアプリ | どこからでも学習管理 |

## アーキテクチャ

```
┌─────────────┐  ┌─────────────┐  ┌──────────────┐
│ Discord Bot │  │   Web App   │  │ Mobile App   │
│  (Python)   │  │  (Next.js)  │  │(React Native)│
└──────┬──────┘  └──────┬──────┘  └──────┬───────┘
       │                │               │
       │         ┌──────┴──────┐        │
       │         │  REST API   │        │
       │         │  (FastAPI)  ├────────┘
       │         └──────┬──────┘
       │                │
  ┌────┴────────────────┴────┐
  │       PostgreSQL 16      │
  └────┬─────────────────────┘
       │
  ┌────┴────┐
  │ Redis 7 │  (キャッシュ・セッション・リアルタイムイベント)
  └─────────┘
```

### Discord Bot の内部構造

```
Cogs (プレゼンテーション層)     ← スラッシュコマンド・UI
  ↓
Managers (ビジネスロジック層)    ← バリデーション・計算・外部API呼び出し
  ↓
Repositories (データアクセス層)  ← SQL クエリ・トランザクション
  ↓
PostgreSQL (永続化層)            ← asyncpg 接続プール
```

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| Discord Bot | Python 3.12, discord.py 2.3+, asyncpg |
| REST API | Python 3.12, FastAPI, asyncpg, JWT認証 |
| Web App | Next.js 14, React 18, TypeScript, Tailwind CSS, shadcn/ui |
| Mobile App | React Native, Expo |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| AI | OpenAI API (gpt-4o-mini / gpt-4o) |
| CI/CD | GitHub Actions, Docker multi-stage builds |
| テスト | pytest, pytest-asyncio (445+ tests) |

## クイックスタート

### 前提条件

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Discord Bot Token](https://discord.com/developers/applications)
- OpenAI API Key (AI機能を使う場合、任意)

### 1. リポジトリをクローン

```bash
git clone https://github.com/your-username/studybot.git
cd studybot
```

### 2. 環境変数を設定

```bash
cp .env.example .env
```

`.env` を開いて以下を最低限設定:

```env
DISCORD_TOKEN=your_bot_token_here
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret
```

### 3. Docker Compose で起動

```bash
docker-compose up -d
```

これで以下が起動します:

| サービス | ポート | 説明 |
|----------|--------|------|
| `bot` | - | Discord Bot (トークンでDiscordに接続) |
| `api` | `8000` | REST API (`http://localhost:8000/docs` でSwagger UI) |
| `web` | `3000` | Webダッシュボード (`http://localhost:3000`) |
| `postgres` | `5432` | PostgreSQL データベース |
| `redis` | `6379` | Redis キャッシュ |

### 4. Discord でコマンドを使う

Bot をサーバーに招待後、`/help` でコマンド一覧を表示できます。

## ローカル開発

各アプリの詳細は個別READMEを参照してください:

- [Discord Bot](apps/discord-bot/README.md) - コマンド一覧・開発ガイド
- [REST API](apps/api/README.md) - エンドポイント一覧・認証フロー
- [Web App](apps/web/README.md) - ページ構成・開発セットアップ

### テスト実行

```bash
# Discord Bot (323 tests)
cd apps/discord-bot
pip install -r requirements.txt
pytest -x -q

# API (122 tests)
cd apps/api
pip install -r requirements.txt
pytest -x -q
```

### コード品質

```bash
ruff check .
ruff format --check .
```

## プロジェクト構成

```
studybot/
├── apps/
│   ├── discord-bot/          # Discord Bot (Python)
│   │   ├── studybot/
│   │   │   ├── cogs/         # スラッシュコマンド (27 Cog)
│   │   │   ├── managers/     # ビジネスロジック (22 Manager)
│   │   │   ├── repositories/ # データアクセス (24 Repository)
│   │   │   ├── services/     # 外部サービス連携 (OpenAI, Redis)
│   │   │   ├── config/       # 設定・定数
│   │   │   ├── database/     # DB接続管理
│   │   │   └── utils/        # ユーティリティ
│   │   └── tests/            # テスト (323件)
│   ├── api/                  # REST API (FastAPI)
│   │   ├── api/
│   │   │   ├── routes/       # エンドポイント (25ファイル)
│   │   │   ├── models/       # Pydanticスキーマ
│   │   │   ├── middleware/   # セキュリティ・レート制限
│   │   │   └── services/     # サービス層
│   │   └── tests/            # テスト (122件)
│   ├── web/                  # Web App (Next.js)
│   │   └── src/
│   │       ├── app/          # ページ (25ルート)
│   │       ├── components/   # UIコンポーネント (49個)
│   │       ├── hooks/        # カスタムフック
│   │       └── lib/          # ユーティリティ
│   └── mobile-app/           # モバイルアプリ (React Native)
├── migrations/               # SQLマイグレーション
├── docker-compose.yml        # Docker構成
├── .github/
│   ├── workflows/ci.yml      # CI/CDパイプライン
│   └── dependabot.yml        # 依存関係自動更新
└── .env.example              # 環境変数テンプレート
```

## 環境変数

| 変数 | 必須 | 説明 |
|------|------|------|
| `DISCORD_TOKEN` | Yes | Discord Bot トークン |
| `DISCORD_CLIENT_ID` | Yes* | Discord OAuth2 クライアントID (*Web/API使用時) |
| `DISCORD_CLIENT_SECRET` | Yes* | Discord OAuth2 クライアントシークレット (*Web/API使用時) |
| `OPENAI_API_KEY` | No | OpenAI API キー (AI機能用) |
| `POSTGRES_PASSWORD` | No | PostgreSQL パスワード (デフォルト: `studybot_dev`) |
| `API_SECRET_KEY` | No | JWT署名キー (デフォルト: `change-me-in-production`) |

全変数の一覧は [.env.example](.env.example) を参照。

## コントリビュート

[CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## ライセンス

[MIT License](LICENSE)
