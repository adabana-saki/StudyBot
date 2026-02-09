"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import PageHeader from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  getSavingsStatus,
  depositSavings,
  withdrawSavings,
  getInterestHistory,
  SavingsStatus,
  InterestHistoryEntry,
} from "@/lib/api";

export default function SavingsPage() {
  const authenticated = useAuthGuard();
  const [status, setStatus] = useState<SavingsStatus | null>(null);
  const [history, setHistory] = useState<InterestHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [amount, setAmount] = useState(100);
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!authenticated) return;
    fetchData();
  }, [authenticated]);

  async function fetchData() {
    try {
      const [s, h] = await Promise.all([getSavingsStatus(), getInterestHistory()]);
      setStatus(s);
      setHistory(h);
    } catch (err) {
      setError(err instanceof Error ? err.message : "取得に失敗");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeposit(type: string) {
    setProcessing(true);
    setError(null);
    try {
      const res = await depositSavings(amount, type);
      setMessage(`${res.type_label} に ${res.amount.toLocaleString()} 🪙 を預金しました`);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "預金失敗");
    } finally {
      setProcessing(false);
    }
  }

  async function handleWithdraw(type: string) {
    setProcessing(true);
    setError(null);
    try {
      const res = await withdrawSavings(amount, type);
      setMessage(`${res.type_label} から ${res.amount.toLocaleString()} 🪙 を引き出しました`);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "引き出し失敗");
    } finally {
      setProcessing(false);
    }
  }

  if (loading) return <LoadingSpinner />;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <PageHeader
        title="貯金銀行"
        action={
          <Link href="/market">
            <Button variant="ghost">市場に戻る</Button>
          </Link>
        }
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      {message && (
        <div className="mb-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-sm">
          {message}
        </div>
      )}

      {/* Summary */}
      {status && (
        <div className="grid grid-cols-2 gap-4 mb-6">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-xs text-muted-foreground">預金合計</p>
              <p className="text-xl font-bold">{status.total_savings.toLocaleString()} 🪙</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-xs text-muted-foreground">累計利息</p>
              <p className="text-xl font-bold text-green-400">+{status.total_interest.toLocaleString()} 🪙</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Accounts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Regular */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">💰 普通預金</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-2">日利 0.1% / いつでも引き出し可</p>
            {status?.accounts.find((a) => a.account_type === "regular") ? (
              <div className="mb-4">
                <p className="text-lg font-bold">
                  {status.accounts.find((a) => a.account_type === "regular")!.balance.toLocaleString()} 🪙
                </p>
                <p className="text-xs text-muted-foreground">
                  累計利息: {status.accounts.find((a) => a.account_type === "regular")!.total_interest_earned.toLocaleString()} 🪙
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground mb-4">口座未開設</p>
            )}
            <div className="flex gap-2">
              <Button size="sm" onClick={() => handleDeposit("regular")} disabled={processing}>預金</Button>
              <Button size="sm" variant="outline" onClick={() => handleWithdraw("regular")} disabled={processing}>引き出し</Button>
            </div>
          </CardContent>
        </Card>

        {/* Fixed */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">🔒 定期預金</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-2">日利 0.3% / 7日ロック</p>
            {status?.accounts.find((a) => a.account_type === "fixed") ? (() => {
              const acc = status.accounts.find((a) => a.account_type === "fixed")!;
              return (
                <div className="mb-4">
                  <p className="text-lg font-bold">{acc.balance.toLocaleString()} 🪙</p>
                  <p className="text-xs text-muted-foreground">
                    累計利息: {acc.total_interest_earned.toLocaleString()} 🪙
                  </p>
                  {acc.maturity_date && (
                    <p className="text-xs text-muted-foreground">
                      満期日: {new Date(acc.maturity_date).toLocaleDateString("ja-JP")}
                    </p>
                  )}
                </div>
              );
            })() : (
              <p className="text-sm text-muted-foreground mb-4">口座未開設</p>
            )}
            <div className="flex gap-2">
              <Button size="sm" onClick={() => handleDeposit("fixed")} disabled={processing}>預金</Button>
              <Button size="sm" variant="outline" onClick={() => handleWithdraw("fixed")} disabled={processing}>引き出し</Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Amount Input */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <label className="text-sm text-muted-foreground">金額:</label>
            <input
              type="number"
              min={10}
              value={amount}
              onChange={(e) => setAmount(Math.max(10, parseInt(e.target.value) || 10))}
              className="w-32 bg-background border rounded px-2 py-1 text-sm"
            />
            <span className="text-sm text-muted-foreground">🪙</span>
            <div className="flex gap-1 ml-auto">
              {[100, 500, 1000, 5000].map((v) => (
                <Button key={v} size="sm" variant="ghost" onClick={() => setAmount(v)}>
                  {v.toLocaleString()}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Interest History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">利息履歴</CardTitle>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground">利息履歴はありません</p>
          ) : (
            <div className="space-y-2">
              {history.map((h) => (
                <div key={h.id} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                  <span>{h.account_type === "regular" ? "💰 普通" : "🔒 定期"}</span>
                  <span className="text-green-400">+{h.amount.toLocaleString()} 🪙</span>
                  <span className="text-muted-foreground">残高: {h.balance_after.toLocaleString()}</span>
                  <span className="text-muted-foreground text-xs">
                    {new Date(h.calculated_at).toLocaleDateString("ja-JP")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
