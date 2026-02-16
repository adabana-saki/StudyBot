# StudyBot - Web Dashboard

Next.js ベースのWebダッシュボード。Discord OAuth2 認証で、学習データの閲覧・管理を提供します。

## セットアップ

### Docker (推奨)

プロジェクトルートで `docker-compose up -d` を実行すると `http://localhost:3000` で起動します。

### ローカル開発

```bash
cd apps/web

# 依存関係のインストール
npm install

# 環境変数の設定
cp .env.example .env.local
# .env.local を編集

# 開発サーバー起動 (API が http://localhost:8000 で起動済みであること)
npm run dev
```

`http://localhost:3000` でアクセスできます。

### 環境変数

| 変数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | REST API のURL |
| `NEXT_PUBLIC_DISCORD_CLIENT_ID` | Yes | - | Discord OAuth2 クライアントID |

## 技術スタック

| 項目 | 技術 |
|------|------|
| フレームワーク | Next.js 14 (App Router) |
| 言語 | TypeScript 5.3 |
| スタイリング | Tailwind CSS 3.4 |
| UIコンポーネント | shadcn/ui (Radix UI) |
| チャート | Recharts |
| アイコン | Lucide React |

## ページ構成

| パス | 説明 |
|------|------|
| `/` | ランディングページ |
| `/auth/callback` | Discord OAuth2 コールバック |
| `/dashboard` | ダッシュボード (学習統計・チャート) |
| `/achievements` | 実績一覧 |
| `/activity` | アクティビティフィード |
| `/buddy` | スタディバディ |
| `/challenges` | チャレンジ一覧 |
| `/challenges/[id]` | チャレンジ詳細 |
| `/flashcards` | フラッシュカード |
| `/focus` | フォーカスセッション (スマホロック) |
| `/help` | ヘルプ |
| `/insights` | AIインサイト |
| `/leaderboard` | リーダーボード |
| `/plans` | 学習プラン |
| `/profile` | プロフィール |
| `/timeline` | ソーシャルタイムライン (リアクション・コメント) |
| `/battles` | チームバトル一覧 |
| `/battles/[id]` | バトルアリーナ (リアルタイムスコア) |
| `/rooms` | スタディキャンパス (ルーム一覧) |
| `/rooms/[id]` | ルーム詳細 (メンバー・タイマー) |
| `/server` | サーバー管理 |
| `/server/analytics` | 分析ダッシュボード (エンゲージメント・離脱リスク) |
| `/shop` | ショップ |
| `/todos` | To-Do管理 |
| `/wellness` | ウェルネス |

## コンポーネント

### レイアウト
- `Sidebar` - サイドバーナビゲーション
- `PageHeader` - ページヘッダー
- `Modal` - モーダルダイアログ
- `ErrorBanner` - エラー表示
- `LoadingSpinner` - ローディング

### 機能コンポーネント
- `StatsCard` - 統計カード
- `StudyChart` - 学習チャート
- `StudyHeatmap` - 学習ヒートマップ
- `LeaderboardTable` - リーダーボード
- `AchievementCard` - 実績カード
- `FlashcardDeck` - フラッシュカードデッキ
- `ActiveSessionCard` - アクティブセッション
- `ActivityFeed` - アクティビティフィード
- `StudyingNowPanel` - 現在学習中パネル
- `BuddyCard` - バディカード
- `ChallengeCard` - チャレンジカード
- `InsightCard` - インサイトカード
- `CorrelationChart` - 相関チャート
- `WellnessChart` - ウェルネスチャート
- `TimelineCard` - タイムラインイベントカード
- `ReactionBar` - リアクションバー (👏🔥❤️📚)
- `CommentThread` - コメントスレッド
- `BattleArena` - バトルアリーナ (VS表示・スコアバー)
- `ContributionChart` - 貢献度横棒グラフ
- `CommunityHealth` - コミュニティ健全性スコア
- `EngagementChart` - エンゲージメント推移チャート
- `AtRiskPanel` - 離脱リスクメンバーパネル
- `ActivityHeatmap` - 学習時間帯ヒートマップ
- `RoomCard` - ルームカード (テーマ・人数・目標)
- `RoomMemberGrid` - ルームメンバーグリッド
- `RoomTimer` - ルーム内フォーカスタイマー
- `BlockOverlay` - フォーカスロック中の全画面オーバーレイ (カウントダウン・モチベーションメッセージ)
- `ChallengeModal` - チャレンジ解除モーダル (計算/タイピング)

### UIコンポーネント (shadcn/ui)
`src/components/ui/` に Button, Card, Dialog, Table, Tabs, Toast 等の基本UIを配置。

## カスタムフック

| フック | 説明 |
|--------|------|
| `useAuthGuard` | 認証ガード (未ログインでリダイレクト) |
| `useEventStream` | SSEイベントストリーム接続 |
| `useSessionSync` | クロスプラットフォームセッション同期 |

## スクリプト

```bash
npm run dev      # 開発サーバー (http://localhost:3000)
npm run build    # プロダクションビルド
npm run start    # プロダクション起動
npm run lint     # ESLint
```

## ディレクトリ構成

```
src/
├── app/              # Next.js App Router ページ (25ルート)
│   ├── layout.tsx    # ルートレイアウト
│   ├── page.tsx      # ランディングページ
│   ├── globals.css   # グローバルスタイル
│   ├── dashboard/    # ダッシュボード
│   ├── auth/         # OAuth2 コールバック
│   ├── timeline/     # ソーシャルタイムライン
│   ├── battles/      # チームバトル
│   ├── rooms/        # スタディルーム
│   ├── server/analytics/ # 分析ダッシュボード
│   └── ...           # その他ページ
├── components/       # コンポーネント (51個)
│   ├── ui/           # shadcn/ui 基本コンポーネント
│   └── *.tsx         # 機能コンポーネント
├── hooks/            # カスタムフック (3個)
└── lib/
    ├── api.ts        # API クライアント
    ├── events.ts     # SSEイベント定義
    └── utils.ts      # ユーティリティ
```
