"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import PageHeader from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface CommandInfo {
  name: string;
  description: string;
  usage: string;
}

interface CategoryInfo {
  label: string;
  emoji: string;
  commands: CommandInfo[];
}

const HELP_DATA: Record<string, CategoryInfo> = {
  study: {
    label: "学習",
    emoji: "📚",
    commands: [
      {
        name: "/study start",
        description: "学習セッションを開始します",
        usage: "/study start [科目]",
      },
      {
        name: "/study stop",
        description: "学習セッションを終了し、記録します",
        usage: "/study stop",
      },
      {
        name: "/study stats",
        description: "学習統計を表示します",
        usage: "/study stats [期間: weekly/monthly/all]",
      },
      {
        name: "/pomodoro",
        description: "ポモドーロタイマーを開始します",
        usage: "/pomodoro [作業分数] [休憩分数]",
      },
      {
        name: "/focus start",
        description: "フォーカスモードを開始します",
        usage: "/focus start [分数]",
      },
      {
        name: "/focus stop",
        description: "フォーカスモードを終了します",
        usage: "/focus stop",
      },
    ],
  },
  gamification: {
    label: "ゲーミフィケーション",
    emoji: "🎮",
    commands: [
      {
        name: "/profile",
        description: "プロフィールを表示します",
        usage: "/profile [@ユーザー]",
      },
      {
        name: "/profile edit",
        description: "プロフィールを編集します",
        usage: "/profile edit",
      },
      {
        name: "/leaderboard",
        description: "ランキングを表示します",
        usage: "/leaderboard [カテゴリ: xp/coins/streak]",
      },
      {
        name: "/achievements",
        description: "実績一覧を表示します",
        usage: "/achievements",
      },
      {
        name: "/raid start",
        description: "スタディレイドを開始します",
        usage: "/raid start [目標分数]",
      },
      {
        name: "/raid join",
        description: "スタディレイドに参加します",
        usage: "/raid join",
      },
    ],
  },
  shop: {
    label: "ショップ",
    emoji: "🛒",
    commands: [
      {
        name: "/shop",
        description: "ショップを表示します",
        usage: "/shop [カテゴリ]",
      },
      {
        name: "/shop buy",
        description: "アイテムを購入します",
        usage: "/shop buy [アイテム名]",
      },
      {
        name: "/shop equip",
        description: "アイテムを装備します",
        usage: "/shop equip [アイテム名]",
      },
      {
        name: "/shop roles",
        description: "取得可能な特別ロールを表示します",
        usage: "/shop roles",
      },
      {
        name: "/inventory",
        description: "インベントリを表示します",
        usage: "/inventory",
      },
      {
        name: "/balance",
        description: "コイン残高を確認します",
        usage: "/balance",
      },
    ],
  },
  ai: {
    label: "AI機能",
    emoji: "🤖",
    commands: [
      {
        name: "/plan create",
        description: "AIが学習プランを生成します",
        usage: "/plan create [科目] [目標]",
      },
      {
        name: "/plan list",
        description: "学習プラン一覧を表示します",
        usage: "/plan list",
      },
      {
        name: "/flashcard create",
        description: "フラッシュカードデッキを作成します",
        usage: "/flashcard create [デッキ名]",
      },
      {
        name: "/flashcard review",
        description: "カードを復習します",
        usage: "/flashcard review [デッキ名]",
      },
    ],
  },
  wellness: {
    label: "ウェルネス",
    emoji: "💚",
    commands: [
      {
        name: "/wellness log",
        description: "気分・エネルギー・ストレスを記録します",
        usage: "/wellness log [気分 1-5] [エネルギー 1-5] [ストレス 1-5]",
      },
      {
        name: "/wellness stats",
        description: "ウェルネス統計を表示します",
        usage: "/wellness stats [日数]",
      },
    ],
  },
  task: {
    label: "タスク管理",
    emoji: "✅",
    commands: [
      {
        name: "/todo add",
        description: "タスクを追加します",
        usage: "/todo add [タイトル] [優先度: 1-3]",
      },
      {
        name: "/todo list",
        description: "タスク一覧を表示します",
        usage: "/todo list [状態: pending/completed]",
      },
      {
        name: "/todo done",
        description: "タスクを完了にします",
        usage: "/todo done [タスクID]",
      },
      {
        name: "/todo delete",
        description: "タスクを削除します",
        usage: "/todo delete [タスクID]",
      },
    ],
  },
};

const FAQ_ITEMS = [
  {
    q: "XPはどうやって獲得できますか？",
    a: "学習セッション、ポモドーロ完了、フォーカスモード完了、レイド参加、タスク完了などでXPを獲得できます。",
  },
  {
    q: "コインは何に使えますか？",
    a: "ショップでアイテム（カスタム称号、特別ロール、XPブースト、テーマなど）を購入できます。",
  },
  {
    q: "VC（ボイスチャンネル）で勉強すると記録されますか？",
    a: "はい。VCに参加して5分以上経過すると自動的に学習時間として記録され、XPとコインが付与されます。",
  },
  {
    q: "ダッシュボードにログインできません",
    a: "Discordアカウントで認証が必要です。トップページの「Discordでログイン」ボタンからログインしてください。",
  },
  {
    q: "レイドとは何ですか？",
    a: "レイドはグループ学習イベントです。参加者全員が目標時間を達成するとボーナスXPとコインが獲得できます。",
  },
];

export default function HelpPage() {
  const [activeCategory, setActiveCategory] = useState("study");
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <PageHeader
        title="ヘルプ"
        description="StudyBotの使い方とコマンド一覧です。"
      />

      {/* Command Categories */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">コマンド一覧</h2>

        {/* Category Tabs */}
        <div className="flex flex-wrap gap-2 mb-6">
          {Object.entries(HELP_DATA).map(([key, cat]) => (
            <button
              key={key}
              onClick={() => setActiveCategory(key)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                activeCategory === key
                  ? "bg-primary text-primary-foreground"
                  : "bg-card text-muted-foreground hover:text-foreground border border-border"
              )}
            >
              {cat.emoji} {cat.label}
            </button>
          ))}
        </div>

        {/* Command List */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              {HELP_DATA[activeCategory].emoji}{" "}
              {HELP_DATA[activeCategory].label}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {HELP_DATA[activeCategory].commands.map((cmd) => (
                <div key={cmd.name} className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <code className="text-primary font-mono text-sm bg-primary/10 px-2 py-0.5 rounded">
                        {cmd.name}
                      </code>
                      <p className="text-sm mt-1.5">
                        {cmd.description}
                      </p>
                    </div>
                  </div>
                  <p className="text-muted-foreground text-xs mt-2 font-mono">
                    使用例: {cmd.usage}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* FAQ */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4">
          よくある質問 (FAQ)
        </h2>
        <div className="space-y-2">
          {FAQ_ITEMS.map((item, i) => (
            <Card key={i}>
              <button
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
                className="w-full text-left p-4 flex items-center justify-between"
              >
                <span className="font-medium">{item.q}</span>
                <ChevronDown
                  className={cn(
                    "h-5 w-5 text-muted-foreground flex-shrink-0 ml-2 transition-transform",
                    openFaq === i && "rotate-180"
                  )}
                />
              </button>
              {openFaq === i && (
                <div className="px-4 pb-4">
                  <p className="text-muted-foreground text-sm">{item.a}</p>
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>

      {/* Getting Started */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">使い方ガイド</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 text-sm">
            <div className="flex items-start space-x-3">
              <span className="text-primary font-bold text-lg">1.</span>
              <div>
                <p className="font-medium">学習を始める</p>
                <p className="text-muted-foreground mt-0.5">
                  <code className="text-primary">/study start</code> で学習セッションを開始。終わったら <code className="text-primary">/study stop</code> で記録されます。
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <span className="text-primary font-bold text-lg">2.</span>
              <div>
                <p className="font-medium">XPとコインを貯める</p>
                <p className="text-muted-foreground mt-0.5">
                  学習するとXPとコインが獲得できます。XPが貯まるとレベルアップ！コインはショップで使えます。
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <span className="text-primary font-bold text-lg">3.</span>
              <div>
                <p className="font-medium">実績を解除する</p>
                <p className="text-muted-foreground mt-0.5">
                  連続学習、セッション数などの条件を達成すると実績が解除されます。<code className="text-primary">/achievements</code> で確認。
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <span className="text-primary font-bold text-lg">4.</span>
              <div>
                <p className="font-medium">仲間と一緒に学習</p>
                <p className="text-muted-foreground mt-0.5">
                  <code className="text-primary">/raid start</code> でスタディレイドを開始。みんなで目標達成を目指しましょう。
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
