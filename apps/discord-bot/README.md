# StudyBot - Discord Bot

AI搭載学習支援Discord Bot。113以上のスラッシュコマンドで学習管理・ゲーミフィケーション・AI支援を提供します。

## セットアップ

### Docker (推奨)

プロジェクトルートで `docker-compose up -d` を実行するだけで起動します。

### ローカル開発

```bash
cd apps/discord-bot

# 仮想環境の作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .env を編集

# 起動 (PostgreSQL と Redis が起動済みであること)
python main.py
```

### 環境変数

| 変数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `DISCORD_TOKEN` | Yes | - | Discord Bot トークン |
| `DATABASE_URL` | Yes | - | PostgreSQL 接続URL |
| `OPENAI_API_KEY` | No | - | OpenAI API キー (AI機能用) |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | デフォルトAIモデル |
| `OPENAI_MODEL_HEAVY` | No | `gpt-4o` | 高精度AIモデル |
| `AI_DAILY_LIMIT` | No | `10` | AI機能の1日あたり利用回数 |
| `BOT_OWNER_ID` | No | - | Bot管理者のDiscord User ID |
| `LOG_LEVEL` | No | `INFO` | ログレベル |
| `DB_POOL_MIN_SIZE` | No | `2` | DB接続プール最小サイズ |
| `DB_POOL_MAX_SIZE` | No | `10` | DB接続プール最大サイズ |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis接続URL |

## コマンド一覧

### 🍅 学習管理

#### ポモドーロタイマー (`/pomodoro`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/pomodoro start` | セッション開始 | `topic?`, `work_min?` (25), `break_min?` (5) |
| `/pomodoro pause` | 一時停止 | - |
| `/pomodoro resume` | 再開 | - |
| `/pomodoro stop` | 停止 | - |
| `/pomodoro status` | 状態確認 | - |

#### 学習ログ (`/study`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/study log` | 学習時間を記録 | `duration`, `topic?` |
| `/study stats` | 統計表示 | `period?` (daily/weekly/monthly/all_time) |
| `/study chart` | チャート生成 | `chart_type?` (line/bar/pie), `days?` (14) |

#### To-Do管理 (`/todo`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/todo add` | タスク追加 (モーダル) | - |
| `/todo quick` | クイック追加 | `title`, `priority?` (1-3), `deadline?` |
| `/todo list` | 一覧表示 | `status?` (pending/completed/all) |
| `/todo complete` | タスク完了 | `task_id` |
| `/todo delete` | タスク削除 | `task_id` |

#### フォーカスモード (`/focus`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/focus start` | フォーカス開始 | `duration?` (60分) |
| `/focus end` | フォーカス終了 | - |
| `/focus whitelist` | チャンネルをホワイトリスト追加 | `channel` |
| `/focus status` | 状態確認 | - |

#### VC勉強追跡 (`/vc`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/vc status` | VCで勉強中のメンバー一覧 | - |
| `/vc stats` | VC勉強時間統計 | `days?` (30) |

### ⭐ ゲーミフィケーション

#### プロフィール & XP
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/profile` | プロフィール表示 | `user?` |
| `/profile_edit` | プロフィール編集 (モーダル) | - |
| `/xp` | XP・レベル表示 | - |
| `/streak` | 連続学習の詳細 | - |
| `/leaderboard` | ランキング表示 | `category?` (study/xp/tasks), `period?` |

#### ショップ (`/shop`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/shop list` | アイテム一覧 | `category?` (title/cosmetic/boost/theme) |
| `/shop buy` | アイテム購入 | `item_id` |
| `/shop inventory` | 所持アイテム表示 | - |
| `/shop equip` | アイテム装備 | `item_id` |
| `/shop roles` | 特別ロール一覧 | - |
| `/coins` | StudyCoin残高表示 | - |

#### 実績 (`/achievements`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/achievements list` | 全実績一覧 | - |
| `/achievements progress` | 自分の進捗 | - |

#### デイリークエスト (`/quest`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/quest daily` | 今日のクエスト表示 | - |
| `/quest claim` | 報酬受け取り | `quest_id` |

### 👥 ソーシャル

#### スタディレイド (`/raid`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/raid create` | レイド作成 | `topic`, `duration`, `max_participants?` (4) |
| `/raid join` | レイド参加 | `raid_id` |
| `/raid leave` | レイド離脱 | `raid_id` |
| `/raid status` | アクティブレイド一覧 | - |

#### スタディチーム (`/team`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/team create` | チーム作成 | `name`, `max_members?` (10) |
| `/team join` | チーム参加 | `team_id` |
| `/team leave` | チーム脱退 | `team_id` |
| `/team list` | チーム一覧 | - |
| `/team stats` | チーム統計 | `team_id` |
| `/team members` | メンバー一覧 | `team_id` |

#### スタディバディ (`/buddy`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/buddy find` | バディを探す | `subject?` |
| `/buddy status` | マッチ状況 | - |
| `/buddy history` | マッチ履歴 | - |
| `/buddy profile` | バディプロフィール設定 | `subjects?`, `times?`, `style?` |

#### チャレンジ (`/challenge`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/challenge create` | チャレンジ作成 | `name`, `duration`, `goal_type?`, `goal_target?` |
| `/challenge join` | チャレンジ参加 | `challenge_id` |
| `/challenge checkin` | チェックイン | `challenge_id`, `progress?` |
| `/challenge list` | チャレンジ一覧 | - |
| `/challenge leaderboard` | チャレンジランキング | `challenge_id` |

### 🤖 AI支援

#### AIドキュメント解析 (`/ai`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/ai summarize` | ファイルをAI要約 | `file`, `detail_level?` (brief/medium/detailed) |
| `/ai keypoints` | キーポイント抽出 | `file` |
| `/ai quiz` | クイズ生成 | `file`, `count?` (5) |
| `/ai ask` | ファイルについて質問 | `file`, `question` |
| `/ai explain` | 概念をAI解説 | `concept` |

#### フラッシュカード (`/flashcard`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/flashcard create` | カード作成 | `topic`, `front`, `back` |
| `/flashcard study` | 学習開始 | `topic` |
| `/flashcard stats` | 統計表示 | - |

#### 学習プラン (`/plan`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/plan create` | AIで学習プラン作成 | `subject`, `goal`, `deadline?` |
| `/plan view` | プラン表示 | - |
| `/plan progress` | 進捗表示 | - |
| `/plan complete` | タスク完了 | `task_id` |

#### ラーニングパス (`/path`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/path list` | パス一覧 | `category?` (math/english/programming) |
| `/path enroll` | パスに登録 | `path_id` |
| `/path progress` | 進捗表示 | `path_id?` |
| `/path complete` | マイルストーン完了 | `path_id` |

#### AIインサイト (`/insights`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/insights preview` | 今週のインサイトをプレビュー | - |

### 💚 ウェルネス & 通知

#### ウェルネス (`/wellness`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/wellness check` | ウェルネス記録 (モーダル) | - |
| `/wellness stats` | 統計表示 | - |

#### スマホ通知 (`/nudge`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/nudge setup` | Webhook URL設定 | `webhook_url` |
| `/nudge toggle` | 通知ON/OFF | `enabled` |
| `/nudge test` | テスト通知 | - |
| `/nudge status` | 設定表示 | - |
| `/nudge lock` | フォーカスロック開始 | `duration`, `coins_bet?`, `unlock_level?` (1-5) |
| `/nudge shield` | フォーカスシールド開始 | `duration` |
| `/nudge break_lock` | ロック解除 | - |
| `/nudge lock_status` | ロックステータス | - |
| `/nudge code` | 解除コード入力 | `code` |
| `/nudge settings` | デフォルト設定変更 | `unlock_level?`, `duration?`, `coin_bet?` |

### ⚔️ チームバトル

#### バトル (`/battle`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/battle challenge` | チームバトル発行 | `team_id`, `days?` (7) |
| `/battle accept` | バトル承認 | `battle_id` |
| `/battle status` | アクティブバトル一覧 | - |
| `/battle detail` | バトル詳細 | `battle_id` |

### 🏠 スタディルーム

#### ルーム (`/room`)
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/room create` | ルーム作成 | `name`, `theme?`, `goal_minutes?` |
| `/room list` | ルーム一覧 | - |
| `/room join` | ルーム参加 | `room_id`, `topic?` |
| `/room leave` | ルーム退出 | - |
| `/room link` | VCチャンネルとルーム紐づけ | `vc_channel` |

### 🔧 管理

#### 管理者コマンド (`/admin`) ※管理者権限必要
| コマンド | 説明 | パラメータ |
|----------|------|-----------|
| `/admin grant_xp` | XP付与 | `user`, `amount` |
| `/admin grant_coins` | コイン付与 | `user`, `amount` |
| `/admin reset_user` | ユーザーリセット | `user` |
| `/admin server_stats` | サーバー統計 | - |
| `/admin set_study_channel` | 勉強チャンネル設定 | `channel` |
| `/admin set_vc_channel` | VC追跡チャンネル設定 | `channel` |

| `/help` | コマンドヘルプ表示 | - |

## XP報酬

| アクション | XP |
|------------|-----|
| ポモドーロ完了 | 10 XP |
| タスク完了 (高優先度) | 30 XP |
| タスク完了 (中優先度) | 20 XP |
| タスク完了 (低優先度) | 10 XP |
| 学習ログ記録 | 5 XP |
| 7日連続学習ボーナス | 50 XP |
| レイド完了 | 15 XP (1.5倍ボーナス) |

## テスト

```bash
# 全テスト実行 (323件)
pytest -x -q

# カバレッジ付き
pytest --cov=studybot --cov-report=term-missing

# 特定ファイルのみ
pytest tests/test_pomodoro.py -v
```

## アーキテクチャ

```
studybot/
├── cogs/              # 27 Cog (プレゼンテーション層)
│   ├── pomodoro.py    # ポモドーロタイマー
│   ├── study_log.py   # 学習ログ
│   ├── todo.py        # To-Do管理
│   ├── gamification.py # XP・レベル・ストリーク
│   ├── shop.py        # ショップ・通貨
│   ├── raid.py        # スタディレイド
│   ├── focus.py       # フォーカスモード
│   ├── ai_doc.py      # AIドキュメント解析
│   └── ...            # その他
├── managers/          # ビジネスロジック層
├── repositories/      # データアクセス層 (パラメータ化クエリ)
├── services/          # 外部サービス (OpenAI, Redis)
├── config/            # 設定・定数
├── database/          # DB接続プール管理
└── utils/             # Embed生成ヘルパーなど
```
