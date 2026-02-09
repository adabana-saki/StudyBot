"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import PageHeader from "@/components/PageHeader";
import StockChart from "@/components/StockChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getStockDetail, buyStock, sellStock, StockDetail } from "@/lib/api";

export default function StockDetailPage() {
  const authenticated = useAuthGuard();
  const params = useParams();
  const router = useRouter();
  const symbol = (params.symbol as string).toUpperCase();

  const [stock, setStock] = useState<StockDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [shares, setShares] = useState(1);
  const [trading, setTrading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    if (!authenticated) return;
    getStockDetail(symbol)
      .then(setStock)
      .catch((err) => setError(err instanceof Error ? err.message : "取得に失敗"))
      .finally(() => setLoading(false));
  }, [authenticated, symbol]);

  async function handleBuy() {
    setTrading(true);
    setError(null);
    try {
      const res = await buyStock(symbol, shares);
      setResult(`${shares}株を${res.total.toLocaleString()} 🪙 で購入しました。残高: ${res.balance.toLocaleString()} 🪙`);
      const updated = await getStockDetail(symbol);
      setStock(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "購入失敗");
    } finally {
      setTrading(false);
    }
  }

  async function handleSell() {
    setTrading(true);
    setError(null);
    try {
      const res = await sellStock(symbol, shares);
      const profitStr = res.profit !== undefined ? `(損益: ${res.profit >= 0 ? "+" : ""}${res.profit.toLocaleString()})` : "";
      setResult(`${shares}株を${res.total.toLocaleString()} 🪙 で売却しました ${profitStr}。残高: ${res.balance.toLocaleString()} 🪙`);
      const updated = await getStockDetail(symbol);
      setStock(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "売却失敗");
    } finally {
      setTrading(false);
    }
  }

  if (loading) return <LoadingSpinner />;
  if (!stock) return <div className="p-8 text-center">銘柄が見つかりません</div>;

  const sign = stock.change_pct >= 0 ? "+" : "";

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <PageHeader
        title={`${stock.emoji} ${stock.symbol} — ${stock.name}`}
        action={
          <Button variant="ghost" onClick={() => router.push("/market")}>
            戻る
          </Button>
        }
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      {result && (
        <div className="mb-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-sm">
          {result}
        </div>
      )}

      {/* Price Info */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-xs text-muted-foreground">現在価格</p>
            <p className="text-2xl font-bold">{stock.current_price.toLocaleString()} 🪙</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-xs text-muted-foreground">前日終値</p>
            <p className="text-lg">{stock.previous_close.toLocaleString()} 🪙</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-xs text-muted-foreground">変動率</p>
            <p className={`text-lg font-bold ${stock.change_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
              {sign}{stock.change_pct}%
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-xs text-muted-foreground">流通株数</p>
            <p className="text-lg">{stock.circulating_shares.toLocaleString()}</p>
          </CardContent>
        </Card>
      </div>

      {/* Chart */}
      {stock.history.length > 0 && (
        <div className="mb-6">
          <StockChart data={stock.history} symbol={stock.symbol} />
        </div>
      )}

      {/* Trade Panel */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">売買</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">株数:</label>
              <input
                type="number"
                min={1}
                max={100}
                value={shares}
                onChange={(e) => setShares(Math.max(1, Math.min(100, parseInt(e.target.value) || 1)))}
                className="w-20 bg-background border rounded px-2 py-1 text-sm"
              />
            </div>
            <p className="text-sm text-muted-foreground">
              合計: {(stock.current_price * shares).toLocaleString()} 🪙
            </p>
            <div className="flex gap-2 ml-auto">
              <Button onClick={handleBuy} disabled={trading} className="bg-green-600 hover:bg-green-700">
                {trading ? "処理中..." : "購入"}
              </Button>
              <Button onClick={handleSell} disabled={trading} variant="destructive">
                {trading ? "処理中..." : "売却"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">銘柄情報</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-muted-foreground">セクター:</span> {stock.sector}</div>
            <div><span className="text-muted-foreground">トピック:</span> {stock.topic_keyword}</div>
            <div><span className="text-muted-foreground">基準価格:</span> {stock.base_price.toLocaleString()} 🪙</div>
            <div><span className="text-muted-foreground">発行総数:</span> {stock.total_shares.toLocaleString()}</div>
          </div>
          <p className="text-sm text-muted-foreground mt-3">{stock.description}</p>
        </CardContent>
      </Card>
    </div>
  );
}
