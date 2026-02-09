"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import PageHeader from "@/components/PageHeader";
import StockTicker from "@/components/StockTicker";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getStocks, getPortfolioSummary, Stock } from "@/lib/api";

export default function MarketPage() {
  const authenticated = useAuthGuard();
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [summary, setSummary] = useState<{
    total_value: number;
    total_profit: number;
    total_profit_pct: number;
    stock_count: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authenticated) return;
    Promise.all([getStocks(), getPortfolioSummary()])
      .then(([s, p]) => {
        setStocks(s);
        setSummary(p);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "取得に失敗"))
      .finally(() => setLoading(false));
  }, [authenticated]);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <PageHeader title="投資市場" />
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {/* Ticker */}
      <StockTicker stocks={stocks} />

      {/* Quick Nav */}
      <div className="flex flex-wrap gap-3 my-6">
        <Link href="/market/portfolio">
          <Button variant="outline">ポートフォリオ</Button>
        </Link>
        <Link href="/market/savings">
          <Button variant="outline">貯金銀行</Button>
        </Link>
        <Link href="/market/flea">
          <Button variant="outline">フリーマーケット</Button>
        </Link>
      </div>

      {/* Portfolio Summary */}
      {summary && summary.stock_count > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">ポートフォリオサマリー</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-sm text-muted-foreground">総資産</p>
                <p className="text-xl font-bold">{summary.total_value.toLocaleString()} 🪙</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">損益</p>
                <p className={`text-xl font-bold ${summary.total_profit >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {summary.total_profit >= 0 ? "+" : ""}{summary.total_profit.toLocaleString()} 🪙
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">保有銘柄</p>
                <p className="text-xl font-bold">{summary.stock_count}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stock Grid */}
      <h2 className="text-lg font-semibold mb-4">全銘柄</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stocks.map((stock) => (
          <Link key={stock.symbol} href={`/market/stocks/${stock.symbol}`}>
            <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">{stock.emoji}</span>
                  <div>
                    <p className="font-bold">{stock.symbol}</p>
                    <p className="text-xs text-muted-foreground">{stock.name}</p>
                  </div>
                </div>
                <p className="text-lg font-bold">{stock.current_price.toLocaleString()} 🪙</p>
                <p className={`text-sm ${stock.change_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {stock.change_pct >= 0 ? "+" : ""}{stock.change_pct}%
                </p>
                <p className="text-xs text-muted-foreground mt-1">{stock.sector}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
