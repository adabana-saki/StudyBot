# コントリビューションガイド

StudyBot への貢献を歓迎します！このガイドでは、コントリビュートの手順を説明します。

## 開発環境のセットアップ

1. リポジトリをフォーク & クローン
2. 環境変数を設定 (`.env.example` → `.env`)
3. `docker-compose up -d` で依存サービスを起動
4. 各アプリのREADMEに従って開発サーバーを起動

## ブランチ戦略

```
main                ← プロダクション (直接pushしない)
  └── feature/xxx   ← 機能追加
  └── fix/xxx       ← バグ修正
  └── docs/xxx      ← ドキュメント
```

## コミットスタイル

日本語で、接頭辞 + 絵文字を使用:

```
feat: ✨ 新機能の説明
fix: 🐛 バグ修正の説明
docs: 📝 ドキュメント変更
refactor: ♻️ リファクタリング
test: ✅ テスト追加・修正
perf: ⚡ パフォーマンス改善
ci: 🔧 CI/CD変更
```

例:
```
feat: ✨ スタディチーム機能を追加
fix: 🐛 ポモドーロタイマーの一時停止バグを修正
docs: 📝 API README にエンドポイント一覧を追加
```

## Pull Request の手順

1. `main` から新しいブランチを作成
2. 変更を実装
3. テストを追加・修正
4. 全テストがパスすることを確認
5. PR を作成し、変更内容を説明

### PR チェックリスト

- [ ] テストが全てパスする (`pytest -x -q`)
- [ ] Linter にエラーがない (`ruff check .`)
- [ ] フォーマットが整っている (`ruff format --check .`)
- [ ] 必要に応じてドキュメントを更新

## コーディング規約

### Python (Discord Bot / API)

- **フォーマッター**: ruff format
- **リンター**: ruff check
- **型ヒント**: 関数の引数・戻り値に型アノテーションを付ける
- **docstring**: 全てのクラス・公開メソッドにdocstringを付ける (日本語OK)
- **非同期**: DB/API操作は `async/await` を使用
- **SQLインジェクション防止**: パラメータ化クエリ (`$1, $2...`) を必ず使用
- **エラーハンドリング**: bare `except` は使わず、具体的な例外クラスを指定

### TypeScript (Web App)

- **リンター**: ESLint (`npm run lint`)
- **コンポーネント**: 関数コンポーネント + フック
- **スタイリング**: Tailwind CSS ユーティリティクラス

### アーキテクチャ原則

```
Cog (プレゼンテーション)  → Manager (ビジネスロジック) → Repository (データアクセス)
```

- **Cog**: Discord UIの構築・インタラクション処理のみ
- **Manager**: バリデーション・ビジネスロジック・外部API呼び出し
- **Repository**: SQLクエリの実行・トランザクション管理
- DB操作は必ずRepository層経由
- discord.py の interaction は 3秒以内に respond、長い処理は `defer()` を使用

## テスト

### テストの書き方

- `apps/discord-bot/tests/` と `apps/api/tests/` にテストを配置
- `conftest.py` の共通フィクスチャを活用 (`mock_db_pool`, `mock_bot` 等)
- Manager のテストでは DB をモックし、ロジックのみテスト
- API のテストでは `TestClient` を使用

### テスト実行

```bash
# Discord Bot (256 tests)
cd apps/discord-bot && pytest -x -q

# API (85 tests)
cd apps/api && pytest -x -q

# 全テスト
cd apps/discord-bot && pytest -x -q && cd ../api && pytest -x -q
```

## Issue & バグ報告

Issue を作成する際は以下の情報を含めてください:

- 発生している問題の説明
- 再現手順
- 期待される動作
- 実際の動作
- 環境情報 (OS, Python/Node.jsバージョン)

## ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照。
