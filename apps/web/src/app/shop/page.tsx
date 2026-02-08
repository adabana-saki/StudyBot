"use client";

import { useEffect, useState } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import Modal from "@/components/Modal";
import PageHeader from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  getShopItems,
  getInventory,
  purchaseItem,
  getCurrencyBalance,
  ShopItem,
  InventoryItem,
  CurrencyBalance,
} from "@/lib/api";

const CATEGORIES = [
  { value: "", label: "すべて" },
  { value: "theme", label: "テーマ" },
  { value: "title", label: "称号" },
  { value: "role", label: "ロール" },
  { value: "boost", label: "ブースト" },
  { value: "badge", label: "バッジ" },
];

const RARITY_VARIANTS: Record<string, string> = {
  common: "border-gray-500 text-gray-400 bg-gray-500/10",
  uncommon: "border-green-500 text-green-400 bg-green-500/10",
  rare: "border-blue-500 text-blue-400 bg-blue-500/10",
  epic: "border-purple-500 text-purple-400 bg-purple-500/10",
  legendary: "border-yellow-500 text-yellow-400 bg-yellow-500/10",
};

const RARITY_CARD_BORDERS: Record<string, string> = {
  common: "border-gray-500",
  uncommon: "border-green-500",
  rare: "border-blue-500",
  epic: "border-purple-500",
  legendary: "border-yellow-500",
};

/** ショップページ - アイテム閲覧・購入・インベントリ管理 */
export default function ShopPage() {
  const authenticated = useAuthGuard();
  const [items, setItems] = useState<ShopItem[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [balance, setBalance] = useState<CurrencyBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState("");
  const [tab, setTab] = useState<"shop" | "inventory">("shop");
  const [purchasing, setPurchasing] = useState<number | null>(null);
  const [confirmItem, setConfirmItem] = useState<ShopItem | null>(null);

  useEffect(() => {
    if (authenticated) fetchData();
  }, [authenticated]);

  useEffect(() => {
    if (!authenticated) return;
    getShopItems(category || undefined)
      .then(setItems)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "カテゴリ取得に失敗しました")
      );
  }, [category, authenticated]);

  async function fetchData() {
    try {
      const [itemsData, invData, balData] = await Promise.all([
        getShopItems(),
        getInventory(),
        getCurrencyBalance(),
      ]);
      setItems(itemsData);
      setInventory(invData);
      setBalance(balData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }

  async function handlePurchase(item: ShopItem) {
    setPurchasing(item.id);
    try {
      const result = await purchaseItem(item.id);
      setBalance((prev) =>
        prev ? { ...prev, balance: result.balance } : prev
      );
      const invData = await getInventory();
      setInventory(invData);
      setConfirmItem(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "購入に失敗しました");
    } finally {
      setPurchasing(null);
    }
  }

  if (loading) return <LoadingSpinner />;

  if (error && !items.length) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="border-destructive/50 max-w-md w-full text-center">
          <CardContent className="p-8">
            <p className="text-muted-foreground">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <PageHeader
        title="ショップ"
        action={
          balance ? (
            <Card>
              <CardContent className="px-4 py-2">
                <span className="text-yellow-400 font-bold">
                  {balance.balance.toLocaleString()}
                </span>
                <span className="text-muted-foreground ml-1">コイン</span>
              </CardContent>
            </Card>
          ) : undefined
        }
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {/* Tabs */}
      <div className="flex space-x-2 mb-6">
        <Button
          onClick={() => setTab("shop")}
          variant={tab === "shop" ? "default" : "ghost"}
          size="sm"
        >
          ショップ
        </Button>
        <Button
          onClick={() => setTab("inventory")}
          variant={tab === "inventory" ? "default" : "ghost"}
          size="sm"
        >
          インベントリ ({inventory.length})
        </Button>
      </div>

      {tab === "shop" && (
        <>
          {/* Category Filter */}
          <div className="flex flex-wrap gap-2 mb-6">
            {CATEGORIES.map((cat) => (
              <Button
                key={cat.value}
                onClick={() => setCategory(cat.value)}
                variant={category === cat.value ? "default" : "outline"}
                size="sm"
                className="rounded-full"
              >
                {cat.label}
              </Button>
            ))}
          </div>

          {/* Item Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((item) => {
              const rarityBadgeClass =
                RARITY_VARIANTS[item.rarity] || RARITY_VARIANTS.common;
              const rarityBorderClass =
                RARITY_CARD_BORDERS[item.rarity] || RARITY_CARD_BORDERS.common;
              const owned = inventory.some((inv) => inv.item_id === item.id);
              return (
                <Card
                  key={item.id}
                  className={cn(rarityBorderClass, "hover:shadow-lg transition-shadow")}
                >
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between mb-3">
                      <span className="text-3xl">{item.emoji}</span>
                      <Badge
                        variant="outline"
                        className={rarityBadgeClass}
                      >
                        {item.rarity}
                      </Badge>
                    </div>
                    <h3 className="font-semibold mb-1">{item.name}</h3>
                    <p className="text-muted-foreground text-sm mb-3">
                      {item.description}
                    </p>
                    <div className="flex items-center justify-between">
                      <span className="text-yellow-400 font-bold">
                        {item.price.toLocaleString()} コイン
                      </span>
                      {owned ? (
                        <Badge variant="secondary" className="text-green-400 bg-green-400/10 border-transparent">
                          購入済み
                        </Badge>
                      ) : (
                        <Button
                          onClick={() => setConfirmItem(item)}
                          disabled={
                            !balance || balance.balance < item.price
                          }
                          size="sm"
                        >
                          購入
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {items.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              アイテムがありません
            </div>
          )}
        </>
      )}

      {tab === "inventory" && (
        <div className="space-y-3">
          {inventory.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              アイテムがありません。ショップで購入しましょう！
            </div>
          ) : (
            inventory.map((item) => (
              <Card key={item.id}>
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{item.emoji}</span>
                    <div>
                      <h3 className="font-medium">{item.name}</h3>
                      <p className="text-muted-foreground text-sm">
                        {item.category} / x{item.quantity}
                      </p>
                    </div>
                  </div>
                  {item.equipped && (
                    <Badge variant="secondary" className="text-green-400 bg-green-400/10 border-transparent">
                      装備中
                    </Badge>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Purchase Confirmation Modal */}
      <Modal isOpen={!!confirmItem} title="購入確認" onClose={() => setConfirmItem(null)}>
        {confirmItem && (
          <>
            <div className="flex items-center space-x-3 mb-4">
              <span className="text-3xl">{confirmItem.emoji}</span>
              <div>
                <p className="font-medium">{confirmItem.name}</p>
                <p className="text-yellow-400 font-bold">
                  {confirmItem.price.toLocaleString()} コイン
                </p>
              </div>
            </div>
            <p className="text-muted-foreground text-sm mb-4">
              このアイテムを購入しますか？
            </p>
            <div className="flex space-x-3">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setConfirmItem(null)}
              >
                キャンセル
              </Button>
              <Button
                className="flex-1"
                onClick={() => handlePurchase(confirmItem)}
                disabled={purchasing !== null}
              >
                {purchasing ? "購入中..." : "購入する"}
              </Button>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}
