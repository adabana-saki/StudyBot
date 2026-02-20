import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import NativeProvider from "@/components/NativeProvider";
import { Toaster } from "@/components/ui/toaster";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "StudyBot Dashboard",
  description: "StudyBotのウェブダッシュボード - 学習の進捗を確認しよう",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "StudyBot",
  },
};

export const viewport: Viewport = {
  themeColor: "#4338ca",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja" className="dark">
      <head>
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
      </head>
      <body className={`${inter.className} min-h-screen`}>
        <NativeProvider>
          <div className="lg:flex min-h-screen">
            <Sidebar />
            <div className="flex-1 min-w-0">
              <main>{children}</main>
            </div>
          </div>
          <Toaster />
        </NativeProvider>
      </body>
    </html>
  );
}
