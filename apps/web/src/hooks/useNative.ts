"use client";

import { useEffect, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import {
  isNative,
  setupDeepLinks,
  onNetworkChange,
  configureStatusBar,
  hideSplashScreen,
  type NetworkStatus,
} from "@/lib/native";

/**
 * ネイティブ機能を初期化するフック
 * layout.tsx やトップレベルで1回呼ぶ
 */
export function useNativeInit() {
  const router = useRouter();

  useEffect(() => {
    if (!isNative()) return;

    const init = async () => {
      // ステータスバー設定
      await configureStatusBar();

      // スプラッシュスクリーン非表示
      await hideSplashScreen();

      // ディープリンク
      await setupDeepLinks((path) => {
        router.push(path);
      });
    };

    init();
  }, [router]);

  return { isNative: isNative() };
}

/**
 * ネットワーク状態を監視するフック
 */
export function useNetworkStatus() {
  const [status, setStatus] = useState<NetworkStatus>({
    connected: true,
    connectionType: "unknown",
  });

  useEffect(() => {
    let cleanup: (() => void) | undefined;

    const setup = async () => {
      // 初期値
      setStatus({
        connected: navigator.onLine,
        connectionType: "unknown",
      });

      // 変更監視
      cleanup = await onNetworkChange((newStatus) => {
        setStatus(newStatus);
      });
    };

    setup();
    return () => cleanup?.();
  }, []);

  return status;
}

/**
 * オフラインキャッシュ付きAPI呼び出しフック
 */
export function useOfflineCache<T>(key: string, fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [isOffline, setIsOffline] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetcher();
      setData(result);
      setIsOffline(false);
      // キャッシュに保存
      try {
        localStorage.setItem(
          `offline_cache_${key}`,
          JSON.stringify({ data: result, timestamp: Date.now() }),
        );
      } catch {
        // localStorage容量超過時は無視
      }
    } catch {
      // オフライン: キャッシュから読み込み
      setIsOffline(true);
      try {
        const cached = localStorage.getItem(`offline_cache_${key}`);
        if (cached) {
          const parsed = JSON.parse(cached);
          setData(parsed.data);
        }
      } catch {
        // キャッシュ破損時は無視
      }
    } finally {
      setLoading(false);
    }
  }, [key, fetcher]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, loading, isOffline, refresh };
}
