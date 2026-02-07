"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken, setRefreshToken } from "@/lib/auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get("token");
    const refresh = searchParams.get("refresh");

    if (token && refresh) {
      setToken(token);
      setRefreshToken(refresh);
      router.replace("/dashboard");
    } else {
      setError(
        "認証に失敗しました。トークンが見つかりません。もう一度お試しください。"
      );
    }
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="bg-gray-800 rounded-xl p-8 border border-red-600/50 max-w-md w-full text-center">
          <span className="text-4xl block mb-4">❌</span>
          <h1 className="text-xl font-bold text-white mb-2">認証エラー</h1>
          <p className="text-gray-400 mb-6">{error}</p>
          <a
            href="/"
            className="inline-block px-6 py-3 bg-blurple hover:bg-blurple-dark text-white font-medium rounded-lg transition-colors"
          >
            トップに戻る
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blurple mx-auto mb-4"></div>
        <p className="text-gray-400">認証中...</p>
      </div>
    </div>
  );
}
