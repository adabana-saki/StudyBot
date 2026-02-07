# StudyBot - AI搭載学習支援Discord Bot

## プロジェクト概要
Discord上で動作するAI搭載学習支援Bot。ゲーミフィケーション、AIドキュメント解析、スマホ連携通知を統合。

## 技術スタック
- Python 3.12 + discord.py >= 2.3.0
- PostgreSQL + asyncpg
- OpenAI API (GPT-4) + PyPDF2
- matplotlib (チャート生成)
- Docker + docker-compose

## アーキテクチャ
- **Cog Pattern**: 機能ごとにCogに分割、setup_hookで動的ロード
- **Manager Pattern**: ビジネスロジックをManagerクラスに分離
- **Repository Pattern**: DB操作を抽象化、パラメータ化クエリ ($1, $2...)
- **DatabaseManager**: asyncpg接続プール管理、テーブル自動作成

## コマンド
```bash
# 開発
docker-compose up          # ローカル起動
pytest --cov               # テスト実行
ruff check . && ruff format --check .  # コード品質チェック

# Botディレクトリ
cd apps/discord-bot
```

## コミットスタイル
- `feat: ✨ 機能説明` / `fix: 🐛 修正内容` / `docs: 📝 ドキュメント`
- 日本語で記述

## 重要な注意点
- DB操作は必ずRepository層経由
- パラメータ化クエリ ($1, $2...) を使用しSQLインジェクション防止
- asyncio対応: すべてのDB/API操作はasync/await
- discord.pyのinteractionは3秒以内にrespond、長い処理はdefer()
