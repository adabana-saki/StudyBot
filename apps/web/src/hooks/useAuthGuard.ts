"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

/**
 * 認証ガードhook。未認証ユーザーをトップページにリダイレクトする。
 * @returns authenticated - 認証済みかどうか
 */
export function useAuthGuard(): boolean {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
    } else {
      setAuthenticated(true);
    }
  }, [router]);

  return authenticated;
}
