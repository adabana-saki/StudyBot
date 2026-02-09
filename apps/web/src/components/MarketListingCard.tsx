"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface MarketListingCardProps {
  listing: {
    id: number;
    name: string;
    emoji: string;
    rarity: string;
    quantity: number;
    price_per_unit: number;
    seller_name: string;
    expires_at: string;
  };
  onBuy?: (id: number) => void;
  buying?: boolean;
}

const rarityColors: Record<string, string> = {
  common: "border-gray-400",
  uncommon: "border-green-500",
  rare: "border-blue-500",
  epic: "border-purple-500",
  legendary: "border-yellow-500",
};

export function MarketListingCard({
  listing,
  onBuy,
  buying = false,
}: MarketListingCardProps) {
  const calculateExpiresIn = (expiresAt: string): number => {
    const expirationDate = new Date(expiresAt);
    const today = new Date();
    const diffTime = expirationDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return Math.max(0, diffDays);
  };

  const expiresInDays = calculateExpiresIn(listing.expires_at);
  const borderColor = rarityColors[listing.rarity.toLowerCase()] || "border-gray-400";

  return (
    <Card className={`border-2 ${borderColor} hover:shadow-lg transition-shadow`}>
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Header with emoji and name */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-start gap-2 flex-1">
              <span className="text-3xl leading-none">{listing.emoji}</span>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-sm truncate">{listing.name}</h3>
              </div>
            </div>
            <Badge variant="outline" className="text-xs whitespace-nowrap">
              {listing.rarity}
            </Badge>
          </div>

          {/* Quantity and price */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">数量</p>
              <p className="font-medium">{listing.quantity}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">単価</p>
              <p className="font-medium">🪙 {listing.price_per_unit.toLocaleString()}</p>
            </div>
          </div>

          {/* Seller and expiration */}
          <div className="space-y-1 text-xs text-muted-foreground">
            <p>
              <span className="font-medium text-foreground">{listing.seller_name}</span>
            </p>
            <p>残り {expiresInDays} 日</p>
          </div>

          {/* Buy button */}
          {onBuy && (
            <Button
              onClick={() => onBuy(listing.id)}
              disabled={buying}
              className="w-full h-8 text-sm"
              size="sm"
            >
              {buying ? "購入中..." : "購入"}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
