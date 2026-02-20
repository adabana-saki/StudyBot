"use client";

import { useNativeInit, useNetworkStatus } from "@/hooks/useNative";
import { WifiOff } from "lucide-react";

export default function NativeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  useNativeInit();
  const { connected } = useNetworkStatus();

  return (
    <>
      {!connected && (
        <div className="fixed top-0 left-0 right-0 z-[100] bg-destructive text-destructive-foreground text-center py-1.5 text-sm flex items-center justify-center gap-2">
          <WifiOff className="h-3.5 w-3.5" />
          オフラインです
        </div>
      )}
      <div className={!connected ? "pt-8" : ""}>{children}</div>
    </>
  );
}
