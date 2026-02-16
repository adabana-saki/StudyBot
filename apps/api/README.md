# StudyBot - REST API

FastAPI ベースの REST API。Webダッシュボードとモバイルアプリにデータを提供します。

## セットアップ

### Docker (推奨)

プロジェクトルートで `docker-compose up -d` を実行すると `http://localhost:8000` で起動します。

### ローカル開発

```bash
cd apps/api

# 仮想環境の作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 起動 (PostgreSQL と Redis が起動済みであること)
uvicorn main:app --reload --port 8000
```

### 環境変数

| 変数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `DATABASE_URL` | Yes | - | PostgreSQL 接続URL |
| `API_SECRET_KEY` | Yes | `change-me-in-production` | JWT署名キー |
| `DISCORD_CLIENT_ID` | Yes | - | Discord OAuth2 クライアントID |
| `DISCORD_CLIENT_SECRET` | Yes | - | Discord OAuth2 クライアントシークレット |
| `DISCORD_REDIRECT_URI` | No | `http://localhost:8000/api/auth/callback` | OAuth2 リダイレクトURI |
| `WEB_BASE_URL` | No | `http://localhost:3000` | Web App のURL (CORS許可) |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis接続URL |

## APIドキュメント

起動後、以下のURLで自動生成ドキュメントを確認できます:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 認証フロー

```
1. ユーザー → GET /api/auth/discord
   → Discord OAuth2 認証画面へリダイレクト

2. Discord → GET /api/auth/callback
   → auth_code を生成して Redis に保存
   → Web App にリダイレクト (?code=auth_code)

3. Web App → POST /api/auth/exchange { code: auth_code }
   → JWT access_token + refresh_token を返却

4. 以降のリクエスト
   → Authorization: Bearer <access_token>

5. トークン更新 → POST /api/auth/refresh { refresh_token }
   → 新しい access_token を返却
```

## エンドポイント一覧

### 認証

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/auth/discord` | Discord OAuth2 ログイン | - |
| GET | `/api/auth/callback` | OAuth2 コールバック | - |
| POST | `/api/auth/exchange` | 認証コードをJWTに交換 | - |
| POST | `/api/auth/refresh` | トークン更新 | - |
| GET | `/api/auth/discord/login` | モバイル用ログイン | - |
| GET | `/api/auth/discord/mobile-callback` | モバイル用コールバック | - |

### ユーザー統計

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/stats/me` | プロフィール統計 (XP, レベル, ストリーク, ランク) | Yes |
| GET | `/api/stats/me/study` | 学習統計 (期間別) | Yes |
| GET | `/api/stats/me/daily` | 日別学習時間 | Yes |

### リーダーボード

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/leaderboard/{guild_id}` | サーバーランキング | - |

### 実績

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/achievements/all` | 全実績一覧 | - |
| GET | `/api/achievements/me` | 自分の実績進捗 | Yes |

### フラッシュカード

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/flashcards/decks` | デッキ一覧 | Yes |
| GET | `/api/flashcards/decks/{deck_id}/cards` | カード一覧 | Yes |
| GET | `/api/flashcards/decks/{deck_id}/review` | レビュー対象カード | Yes |
| POST | `/api/flashcards/review` | レビュー結果送信 (SM-2) | Yes |
| GET | `/api/flashcards/decks/{deck_id}/stats` | デッキ統計 | Yes |

### ウェルネス

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/wellness/me` | ウェルネスログ | Yes |
| GET | `/api/wellness/me/averages` | 平均値 | Yes |
| POST | `/api/wellness/me` | ウェルネス記録 | Yes |

### フォーカス (スマホロック)

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/focus/status` | アクティブセッション状態 | Yes |
| POST | `/api/focus/start` | セッション開始 | Yes |
| POST | `/api/focus/end` | セッション終了 | Yes |
| POST | `/api/focus/unlock` | コードで解除 | Yes |
| POST | `/api/focus/penalty-unlock` | ペナルティ解除 (Lv5) | Yes |
| POST | `/api/focus/request-code` | 解除コードリクエスト | Yes |
| GET | `/api/focus/settings` | ロック設定取得 | Yes |
| PUT | `/api/focus/settings` | ロック設定更新 (チャレンジモード・難易度含む) | Yes |
| GET | `/api/focus/history` | セッション履歴 | Yes |
| POST | `/api/focus/challenge/generate` | チャレンジ問題生成 (math/typing) | Yes |
| POST | `/api/focus/challenge/verify` | チャレンジ回答検証 | Yes |

### 通知

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| POST | `/api/notifications/register` | デバイストークン登録 | Yes |
| DELETE | `/api/notifications/unregister` | デバイストークン解除 | Yes |
| GET | `/api/notifications/me` | 通知履歴 | Yes |
| POST | `/api/notifications/read/{id}` | 既読にする | Yes |

### ショップ

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/shop/items` | アイテム一覧 | Yes |
| GET | `/api/shop/inventory` | インベントリ | Yes |
| POST | `/api/shop/purchase` | アイテム購入 | Yes |
| GET | `/api/shop/balance` | コイン残高 | Yes |

### To-Do

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/todos` | タスク一覧 | Yes |
| POST | `/api/todos` | タスク作成 | Yes |
| PATCH | `/api/todos/{todo_id}` | タスク更新 | Yes |
| DELETE | `/api/todos/{todo_id}` | タスク削除 | Yes |
| POST | `/api/todos/{todo_id}/complete` | タスク完了 | Yes |

### 学習プラン

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/plans` | プラン一覧 | Yes |
| GET | `/api/plans/{plan_id}` | プラン詳細 | Yes |

### プロフィール

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/profile/me` | 自分のプロフィール | Yes |
| PUT | `/api/profile/me` | プロフィール更新 | Yes |
| GET | `/api/profile/{user_id}` | 他ユーザーの公開プロフィール | Yes |

### サーバー管理

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/server/{guild_id}/stats` | サーバー統計 | Yes |
| GET | `/api/server/{guild_id}/members` | メンバー一覧 | Yes |
| GET | `/api/server/{guild_id}/vc-stats` | VC統計 | Yes |

### 管理者

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/admin/users` | ユーザー一覧 | Yes |
| POST | `/api/admin/users/{user_id}/grant` | XP/コイン付与 | Yes |
| PUT | `/api/admin/settings/{guild_id}` | サーバー設定更新 | Yes |

### リアルタイム & アクティビティ

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/events/stream` | SSEイベントストリーム | Yes |
| GET | `/api/activity/{guild_id}` | アクティビティフィード | Yes |
| GET | `/api/activity/{guild_id}/studying-now` | 現在学習中のユーザー | Yes |

### スタディバディ

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/buddy/profile` | バディプロフィール | Yes |
| PUT | `/api/buddy/profile` | バディプロフィール更新 | Yes |
| GET | `/api/buddy/matches` | マッチ一覧 | Yes |
| GET | `/api/buddy/available` | 利用可能なバディ | Yes |

### チャレンジ

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/challenges` | チャレンジ一覧 | Yes |
| GET | `/api/challenges/{id}` | チャレンジ詳細 | Yes |
| POST | `/api/challenges/{id}/join` | チャレンジ参加 | Yes |
| POST | `/api/challenges/{id}/checkin` | チェックイン | Yes |
| GET | `/api/challenges/{id}/leaderboard` | ランキング | Yes |

### セッション同期

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/sessions/active` | アクティブセッション | Yes |
| POST | `/api/sessions/start` | セッション開始 (Web) | Yes |
| POST | `/api/sessions/end` | セッション終了 | Yes |

### AIインサイト

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/insights/me` | アクティブなインサイト | Yes |
| GET | `/api/insights/me/reports` | 週次レポート一覧 | Yes |
| GET | `/api/insights/me/reports/{id}` | レポート詳細 | Yes |

### ソーシャルタイムライン

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/timeline/{guild_id}` | タイムライン取得 (リアクション数・コメント数付き) | Yes |
| POST | `/api/timeline/{event_id}/reactions` | リアクション追加 | Yes |
| DELETE | `/api/timeline/{event_id}/reactions/{type}` | リアクション削除 | Yes |
| GET | `/api/timeline/{event_id}/comments` | コメント一覧 | Yes |
| POST | `/api/timeline/{event_id}/comments` | コメント投稿 | Yes |
| DELETE | `/api/timeline/comments/{comment_id}` | コメント削除 (own only) | Yes |

### チームバトル

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/battles/{guild_id}` | アクティブバトル一覧 | Yes |
| GET | `/api/battles/{guild_id}/{battle_id}` | バトル詳細 (貢献度含む) | Yes |

### サーバー分析

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/server/{guild_id}/analytics/engagement` | エンゲージメント推移 | Yes |
| GET | `/api/server/{guild_id}/analytics/at-risk` | 離脱リスクメンバー | Yes |
| GET | `/api/server/{guild_id}/analytics/topics` | トピック分析 | Yes |
| GET | `/api/server/{guild_id}/analytics/optimal-times` | 最適イベント時間 | Yes |
| GET | `/api/server/{guild_id}/analytics/health` | コミュニティ健全性スコア | Yes |
| POST | `/api/server/{guild_id}/actions` | アクション作成 (即時/予約) | Yes |
| GET | `/api/server/{guild_id}/actions` | アクション履歴 | Yes |

### スタディルーム

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/api/rooms/{guild_id}` | キャンパス (全ルーム一覧) | Yes |
| GET | `/api/rooms/{guild_id}/{room_id}` | ルーム詳細 (メンバーリスト含む) | Yes |
| POST | `/api/rooms/{guild_id}/{room_id}/join` | Web参加 | Yes |
| POST | `/api/rooms/{guild_id}/{room_id}/leave` | Web退出 | Yes |
| GET | `/api/rooms/{guild_id}/{room_id}/history` | ルーム利用履歴 | Yes |

### ヘルスチェック

| メソッド | パス | 説明 | 認証 |
|----------|------|------|------|
| GET | `/` | API情報 | - |
| GET | `/health` | ヘルスチェック | - |

## ページネーション

多くのリストエンドポイントはページネーションをサポートします:

```
GET /api/todos?offset=0&limit=50
```

レスポンス形式:

```json
{
  "items": [...],
  "total": 142,
  "offset": 0,
  "limit": 50
}
```

| パラメータ | デフォルト | 範囲 | 説明 |
|-----------|-----------|------|------|
| `offset` | 0 | 0+ | スキップ件数 |
| `limit` | 50 | 1-100 | 取得件数 |

## ミドルウェア

| ミドルウェア | 説明 |
|-------------|------|
| SecurityHeaders | CSP, HSTS, X-Frame-Options ヘッダーを付与 |
| RateLimit | 60リクエスト/分 (IP単位) |
| CORS | Web App のオリジンを許可 |

## テスト

```bash
# 全テスト実行 (159件)
pytest -x -q

# カバレッジ付き
pytest --cov=api --cov-report=term-missing
```
