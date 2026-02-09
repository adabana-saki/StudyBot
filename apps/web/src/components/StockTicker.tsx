'use client';

interface Stock {
  symbol: string;
  emoji: string;
  current_price: number;
  change_pct: number;
}

interface StockTickerProps {
  stocks: Stock[];
}

export default function StockTicker({ stocks }: StockTickerProps) {
  const formatPrice = (price: number): string => {
    return `${price.toLocaleString()}`;
  };

  const formatChange = (change: number): string => {
    const sign = change >= 0 ? '+' : '';
    return `${sign}${change.toFixed(1)}%`;
  };

  const getChangeColor = (change: number): string => {
    return change >= 0 ? 'text-green-400' : 'text-red-400';
  };

  return (
    <div className="overflow-x-auto bg-background">
      <div className="flex gap-4 px-4 py-3 min-w-max">
        {stocks.map((stock) => (
          <div
            key={stock.symbol}
            className="flex items-center gap-2 px-3 py-1.5 bg-card rounded-lg border border-border text-sm whitespace-nowrap"
          >
            <span className="text-lg">{stock.emoji}</span>
            <span className="font-semibold text-foreground">{stock.symbol}</span>
            <span className="text-foreground">{formatPrice(stock.current_price)}</span>
            <span className={`font-medium ${getChangeColor(stock.change_pct)}`}>
              {formatChange(stock.change_pct)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
