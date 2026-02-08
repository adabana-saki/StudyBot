"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken, setRefreshToken } from "@/lib/auth";
import { fetchAPI } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");

    if (!code) {
      setError(
        "認証に失敗しました。認証コードが見つかりません。もう一度お試しください。"
      );
      return;
    }

    // 認証コードをJWTトークンに交換
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${API_URL}/api/auth/exchange`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    })
      .then(async (res) => {
        if (!res.ok) {
          throw new Error("認証コードの交換に失敗しました");
        }
        const data: TokenResponse = await res.json();
        setToken(data.access_token);
        setRefreshToken(data.refresh_token);
        router.replace("/dashboard");
      })
      .catch(() => {
        setError(
          "認証に失敗しました。認証コードが無効か有効期限切れです。もう一度お試しください。"
        );
      });
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="max-w-md w-full border-destructive/50">
          <CardContent className="pt-6 text-center">
            <span className="text-4xl block mb-4">❌</span>
            <h1 className="text-xl font-bold mb-2">認証エラー</h1>
            <p className="text-muted-foreground mb-6">{error}</p>
            <Button asChild>
              <a href="/">トップに戻る</a>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <LoadingSpinner label="認証中..." />;
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<LoadingSpinner label="認証中..." />}>
      <AuthCallbackContent />
    </Suspense>
  );
}
