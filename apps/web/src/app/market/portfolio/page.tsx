"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import PageHeader from "@/components/PageHeader";
import PortfolioDonut from "@/components/PortfolioDonut";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  getPortfolio,
  getStockTransactions,
  Portfolio,
  StockTransaction,
} from "@/lib/api";

export default function PortfolioPage() {
  const authenticated = useAuthGuard();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [transactions, setTransactions] = useState<StockTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authenticated) return;
    Promise.all([getPortfolio(), getStockTransactions(10)])
      .then(([p, t]) => {
        setPortfolio(p);
        setTransactions(t.items);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "取得に失敗"))
      .finally(() => setLoading(false));
  }, [authenticated]);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <PageHeader
        title="ポートフォリオ"
        action={
          <Link href="/market">
            <Button variant="ghost">市場に戻る</Button>
          </Link>
        }
      />
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {portfolio && (
        <>
          {/* Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-xs text-muted-foreground">総資産</p>
                <p className="text-xl font-bold">{portfolio.total_value.toLocaleString()} 🪙</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-xs text-muted-foreground">投資額</p>
                <p className="text-lg">{portfolio.total_invested.toLocaleString()} 🪙</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-xs text-muted-foreground">損益</p>
                <p className={`text-lg font-bold ${portfolio.total_profit >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {portfolio.total_profit >= 0 ? "+" : ""}{portfolio.total_profit.toLocaleString()} 🪙
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-xs text-muted-foreground">利益率</p>
                <p className={`text-lg font-bold ${portfolio.total_profit_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {portfolio.total_profit_pct >= 0 ? "+" : ""}{portfolio.total_profit_pct}%
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Donut + Holdings */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <PortfolioDonut holdings={portfolio.holdings} />

            <Card>
              <CardHeader>
                <CardTitle className="text-base">保有銘柄</CardTitle>
              </CardHeader>
              <CardContent>
                {portfolio.holdings.length === 0 ? (
                  <p className="text-sm text-muted-foreground">保有銘柄はありません</p>
                ) : (
                  <div className="space-y-3">
                    {portfolio.holdings.map((h) => (
                      <Link key={h.symbol} href={`/market/stocks/${h.symbol}`}>
                        <div className="flex items-center justify-between p-2 rounded hover:bg-accent cursor-pointer">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{h.emoji}</span>
                            <div>
                              <p className="font-medium text-sm">{h.symbol}</p>
                              <p className="text-xs text-muted-foreground">{h.shares}株 @ {h.avg_buy_price.toLocaleString()}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium">{h.market_value.toLocaleString()} 🪙</p>
                            <p className={`text-xs ${h.profit >= 0 ? "text-green-400" : "text-red-400"}`}>
                              {h.profit >= 0 ? "+" : ""}{h.profit.toLocaleString()} ({h.profit >= 0 ? "+" : ""}{h.profit_pct}%)
                            </p>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {/* Recent Transactions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">直近の取引</CardTitle>
        </CardHeader>
        <CardContent>
          {transactions.length === 0 ? (
            <p className="text-sm text-muted-foreground">取引履歴はありません</p>
          ) : (
            <div className="space-y-2">
              {transactions.map((t) => (
                <div key={t.id} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                  <div className="flex items-center gap-2">
                    <span className={t.transaction_type === "buy" ? "text-green-400" : "text-red-400"}>
                      {t.transaction_type === "buy" ? "購入" : "売却"}
                    </span>
                    <span>{t.emoji} {t.symbol}</span>
                  </div>
                  <div className="text-right text-muted-foreground">
                    {t.shares}株 × {t.price_per_share.toLocaleString()} = {t.total_amount.toLocaleString()} 🪙
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
