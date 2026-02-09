"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import PageHeader from "@/components/PageHeader";
import { MarketListingCard } from "@/components/MarketListingCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  getFleaListings,
  buyFleaListing,
  getMyFleaListings,
  cancelFleaListing,
  MarketListing,
} from "@/lib/api";

export default function FleaMarketPage() {
  const authenticated = useAuthGuard();
  const [listings, setListings] = useState<MarketListing[]>([]);
  const [myListings, setMyListings] = useState<MarketListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"browse" | "my">("browse");
  const [buying, setBuying] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!authenticated) return;
    fetchData();
  }, [authenticated]);

  async function fetchData() {
    try {
      const [l, ml] = await Promise.all([
        getFleaListings(),
        getMyFleaListings(),
      ]);
      setListings(l.items);
      setMyListings(ml);
    } catch (err) {
      setError(err instanceof Error ? err.message : "取得に失敗");
    } finally {
      setLoading(false);
    }
  }

  async function handleBuy(listingId: number) {
    setBuying(listingId);
    setError(null);
    try {
      const res = await buyFleaListing(listingId);
      setMessage(
        `${res.item_name} × ${res.quantity} を購入しました (合計: ${res.total.toLocaleString()} + 手数料: ${res.fee.toLocaleString()} 🪙)`
      );
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "購入失敗");
    } finally {
      setBuying(null);
    }
  }

  async function handleCancel(listingId: number) {
    try {
      await cancelFleaListing(listingId);
      setMessage("出品をキャンセルしました");
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "キャンセル失敗");
    }
  }

  if (loading) return <LoadingSpinner />;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <PageHeader
        title="フリーマーケット"
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

      {/* Tabs */}
      <div className="flex space-x-2 mb-6">
        <Button
          onClick={() => setTab("browse")}
          variant={tab === "browse" ? "default" : "ghost"}
          size="sm"
        >
          出品一覧
        </Button>
        <Button
          onClick={() => setTab("my")}
          variant={tab === "my" ? "default" : "ghost"}
          size="sm"
        >
          自分の出品 ({myListings.filter((l) => l.status === "active").length})
        </Button>
      </div>

      <p className="text-sm text-muted-foreground mb-4">
        取引手数料: 5% | 出品期間: 7日間
      </p>

      {tab === "browse" && (
        <>
          {listings.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              現在出品はありません
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {listings.map((listing) => (
                <MarketListingCard
                  key={listing.id}
                  listing={listing}
                  onBuy={handleBuy}
                  buying={buying === listing.id}
                />
              ))}
            </div>
          )}
        </>
      )}

      {tab === "my" && (
        <>
          {myListings.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              出品中のアイテムはありません
            </div>
          ) : (
            <div className="space-y-3">
              {myListings.map((listing) => {
                const statusIcon: Record<string, string> = {
                  active: "🟢",
                  sold: "✅",
                  cancelled: "❌",
                  expired: "⏰",
                };
                return (
                  <Card key={listing.id}>
                    <CardContent className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span>{statusIcon[listing.status] || "❓"}</span>
                        <span className="text-lg">{listing.emoji}</span>
                        <div>
                          <p className="font-medium text-sm">{listing.name} × {listing.quantity}</p>
                          <p className="text-xs text-muted-foreground">
                            {listing.price_per_unit.toLocaleString()} 🪙/個 | {listing.status}
                          </p>
                        </div>
                      </div>
                      {listing.status === "active" && (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleCancel(listing.id)}
                        >
                          キャンセル
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
