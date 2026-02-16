import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import { Toaster } from "@/components/ui/toaster";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "StudyBot Dashboard",
  description: "StudyBotのウェブダッシュボード - 学習の進捗を確認しよう",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja" className="dark">
      <body className={`${inter.className} min-h-screen`}>
        <div className="lg:flex min-h-screen">
          <Sidebar />
          <div className="flex-1 min-w-0">
            <main>{children}</main>
          </div>
        </div>
        <Toaster />
      </body>
    </html>
  );
}
