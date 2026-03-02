"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { isAuthenticated, logout } from "@/lib/auth";
import {
  Activity,
  LayoutDashboard,
  Trophy,
  Award,
  BookOpen,
  Heart,
  ShoppingBag,
  CheckSquare,
  Map,
  Server,
  User,
  HelpCircle,
  Focus,
  Brain,
  Flag,
  Users,
  Menu,
  LogOut,
  MessageCircle,
  Swords,
  DoorOpen,
  Signal,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

interface NavCategory {
  label: string;
  items: NavItem[];
}

const navCategories: NavCategory[] = [
  {
    label: "学習",
    items: [
      { href: "/dashboard", label: "ダッシュボード", icon: LayoutDashboard },
      { href: "/activity", label: "アクティビティ", icon: Activity },
      { href: "/focus", label: "フォーカス", icon: Focus },
      { href: "/todos", label: "タスク", icon: CheckSquare },
      { href: "/plans", label: "プラン", icon: Map },
    ],
  },
  {
    label: "ゲーム",
    items: [
      { href: "/leaderboard", label: "リーダーボード", icon: Trophy },
      { href: "/achievements", label: "実績", icon: Award },
      { href: "/shop", label: "ショップ", icon: ShoppingBag },
      { href: "/challenges", label: "チャレンジ", icon: Flag },
      { href: "/battles", label: "バトル", icon: Swords },
    ],
  },
  {
    label: "AI・カード",
    items: [
      { href: "/flashcards", label: "フラッシュカード", icon: BookOpen },
      { href: "/insights", label: "インサイト", icon: Brain },
    ],
  },
  {
    label: "ソーシャル",
    items: [
      { href: "/buddy", label: "バディ", icon: Users },
      { href: "/timeline", label: "タイムライン", icon: MessageCircle },
      { href: "/rooms", label: "ルーム", icon: DoorOpen },
    ],
  },
  {
    label: "ウェルネス",
    items: [{ href: "/wellness", label: "ウェルネス", icon: Heart }],
  },
  {
    label: "設定",
    items: [
      { href: "/server", label: "サーバー", icon: Server },
      { href: "/profile", label: "プロフィール", icon: User },
      { href: "/status", label: "システム状態", icon: Signal },
      { href: "/help", label: "ヘルプ", icon: HelpCircle },
    ],
  },
];

function NavContent({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
      {navCategories.map((category) => (
        <div key={category.label}>
          <p className="px-3 mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {category.label}
          </p>
          <div className="space-y-0.5">
            {category.items.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

export default function Sidebar() {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setAuthenticated(isAuthenticated());
  }, [pathname]);

  if (!authenticated) return null;

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 lg:shrink-0 border-r bg-card h-screen sticky top-0">
        {/* Logo */}
        <div className="flex items-center gap-2 px-6 h-16 shrink-0 border-b">
          <BookOpen className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold">StudyBot</span>
        </div>

        <NavContent pathname={pathname} />

        {/* Logout */}
        <div className="shrink-0 border-t p-3">
          <Button
            variant="ghost"
            className="w-full justify-start gap-3"
            onClick={logout}
          >
            <LogOut className="h-4 w-4" />
            ログアウト
          </Button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="lg:hidden sticky top-0 z-40 flex items-center justify-between h-14 border-b bg-card px-4">
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 p-0">
            <SheetHeader className="px-6 pt-6 pb-2">
              <SheetTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                StudyBot
              </SheetTitle>
            </SheetHeader>
            <Separator />
            <NavContent
              pathname={pathname}
              onNavigate={() => setSheetOpen(false)}
            />
            <Separator />
            <div className="p-3">
              <Button
                variant="ghost"
                className="w-full justify-start gap-3"
                onClick={logout}
              >
                <LogOut className="h-4 w-4" />
                ログアウト
              </Button>
            </div>
          </SheetContent>
        </Sheet>

        <Link href="/dashboard" className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          <span className="font-bold">StudyBot</span>
        </Link>

        {/* Spacer for centering */}
        <div className="w-10" />
      </div>
    </>
  );
}
