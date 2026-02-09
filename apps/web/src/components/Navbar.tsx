"use client";

import { useState } from "react";
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
  X,
  LogOut,
  MessageCircle,
  Swords,
  DoorOpen,
  BarChart3,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

const navLinks = [
  { href: "/dashboard", label: "ダッシュボード", icon: LayoutDashboard },
  { href: "/activity", label: "アクティビティ", icon: Activity },
  { href: "/leaderboard", label: "リーダーボード", icon: Trophy },
  { href: "/achievements", label: "実績", icon: Award },
  { href: "/flashcards", label: "フラッシュカード", icon: BookOpen },
  { href: "/wellness", label: "ウェルネス", icon: Heart },
  { href: "/focus", label: "フォーカス", icon: Focus },
  { href: "/buddy", label: "バディ", icon: Users },
  { href: "/insights", label: "インサイト", icon: Brain },
  { href: "/challenges", label: "チャレンジ", icon: Flag },
  { href: "/timeline", label: "タイムライン", icon: MessageCircle },
  { href: "/battles", label: "バトル", icon: Swords },
  { href: "/rooms", label: "ルーム", icon: DoorOpen },
  { href: "/market", label: "投資市場", icon: TrendingUp },
  { href: "/shop", label: "ショップ", icon: ShoppingBag },
  { href: "/todos", label: "タスク", icon: CheckSquare },
  { href: "/plans", label: "プラン", icon: Map },
  { href: "/server", label: "サーバー", icon: Server },
  { href: "/profile", label: "プロフィール", icon: User },
  { href: "/help", label: "ヘルプ", icon: HelpCircle },
];

export default function Navbar() {
  const [sheetOpen, setSheetOpen] = useState(false);
  const pathname = usePathname();
  const authenticated = isAuthenticated();

  if (!authenticated) return null;

  return (
    <nav className="border-b bg-card">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/dashboard" className="flex items-center space-x-2">
            <BookOpen className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">StudyBot</span>
          </Link>

          {/* Desktop Nav Links */}
          <div className="hidden lg:flex items-center space-x-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                    pathname === link.href
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span className="hidden xl:inline">{link.label}</span>
                </Link>
              );
            })}
          </div>

          {/* Desktop Logout */}
          <div className="hidden lg:flex items-center">
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut className="h-4 w-4 mr-2" />
              ログアウト
            </Button>
          </div>

          {/* Mobile Menu (Sheet) */}
          <div className="lg:hidden">
            <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Menu className="h-6 w-6" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-72">
                <SheetHeader>
                  <SheetTitle className="flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-primary" />
                    StudyBot
                  </SheetTitle>
                </SheetHeader>
                <div className="mt-6 space-y-1">
                  {navLinks.map((link) => {
                    const Icon = link.icon;
                    return (
                      <Link
                        key={link.href}
                        href={link.href}
                        onClick={() => setSheetOpen(false)}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                          pathname === link.href
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                        )}
                      >
                        <Icon className="h-4 w-4" />
                        {link.label}
                      </Link>
                    );
                  })}
                  <div className="border-t my-2" />
                  <button
                    onClick={logout}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground w-full"
                  >
                    <LogOut className="h-4 w-4" />
                    ログアウト
                  </button>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </nav>
  );
}
