"use client";

export default function OfflinePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4 text-center">
      <div className="text-6xl mb-6">📡</div>
      <h1 className="text-2xl font-bold mb-3">オフラインです</h1>
      <p className="text-muted-foreground mb-6 max-w-md">
        インターネット接続が見つかりません。接続を確認してからもう一度お試しください。
      </p>
      <button
        onClick={() => window.location.reload()}
        className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity"
      >
        再読み込み
      </button>
    </div>
  );
}
