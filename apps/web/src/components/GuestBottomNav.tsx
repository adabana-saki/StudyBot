"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Timer, CheckSquare, BookOpen, BarChart2 } from "lucide-react";

const NAV_ITEMS = [
  { href: "/timer", icon: Timer, label: "タイマー" },
  { href: "/guest/todos", icon: CheckSquare, label: "TODO" },
  { href: "/guest/log", icon: BookOpen, label: "記録" },
  { href: "/guest/stats", icon: BarChart2, label: "統計" },
];

function getTodoBadge(): number {
  if (typeof window === "undefined") return 0;
  try {
    const todos = JSON.parse(localStorage.getItem("studybot_todos") || "[]");
    return todos.filter(
      (t: any) =>
        !t.completed &&
        t.deadline &&
        new Date(t.deadline) < new Date(),
    ).length;
  } catch {
    return 0;
  }
}

export default function GuestBottomNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [overdue, setOverdue] = useState(0);

  useEffect(() => {
    setOverdue(getTodoBadge());
    const timer = setInterval(() => setOverdue(getTodoBadge()), 30000);
    return () => clearInterval(timer);
  }, [pathname]);

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 glass border-t border-white/5"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="flex items-center justify-around max-w-md mx-auto h-16">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const badge = item.href === "/guest/todos" ? overdue : 0;

          return (
            <button
              key={item.href}
              onClick={() => router.push(item.href)}
              className={`relative flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-xl transition-all duration-200 ${
                isActive
                  ? "text-indigo-400"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <div
                className={`relative p-1.5 rounded-xl transition-all duration-200 ${
                  isActive ? "bg-indigo-500/15" : ""
                }`}
              >
                <item.icon className="h-5 w-5" />
                {badge > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 flex items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white">
                    {badge}
                  </span>
                )}
              </div>
              <span
                className={`text-[10px] font-medium ${
                  isActive ? "text-indigo-400" : ""
                }`}
              >
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
