"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Holding {
  symbol: string;
  name: string;
  emoji: string;
  market_value: number;
}

interface PortfolioDonutProps {
  holdings: Holding[];
}

const COLORS = ["#00C853", "#2196F3", "#FF9800", "#E91E63", "#9C27B0", "#00BCD4", "#FFC107", "#F44336"];

export default function PortfolioDonut({ holdings }: PortfolioDonutProps) {
  if (holdings.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">ポートフォリオ配分</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">保有銘柄がありません</p>
        </CardContent>
      </Card>
    );
  }

  const totalValue = holdings.reduce((sum, h) => sum + h.market_value, 0);

  const chartData = holdings.map((holding) => ({
    name: `${holding.emoji} ${holding.symbol}`,
    value: holding.market_value,
    percentage: totalValue > 0 ? ((holding.market_value / totalValue) * 100).toFixed(1) : "0.0",
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div
          style={{
            backgroundColor: "hsl(217 33% 12%)",
            border: "1px solid hsl(217 33% 22%)",
            borderRadius: "8px",
            padding: "8px 12px",
            color: "hsl(210 40% 98%)",
          }}
        >
          <p className="text-sm font-medium">{data.name}</p>
          <p className="text-sm">🪙 {data.value.toLocaleString()}</p>
          <p className="text-xs text-gray-400">{data.percentage}%</p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">ポートフォリオ配分</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percentage }) => `${name} ${percentage}%`}
                labelLine={false}
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2">
          {holdings.map((holding, index) => (
            <div key={holding.symbol} className="flex items-center gap-2 text-xs">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              />
              <span>{holding.emoji} {holding.symbol}</span>
              <span className="text-muted-foreground ml-auto">
                {totalValue > 0 ? ((holding.market_value / totalValue) * 100).toFixed(1) : "0.0"}%
              </span>
            </div>
          ))}
        </div>

        <div className="mt-4 pt-4 border-t">
          <div className="flex justify-between items-center text-sm">
            <span className="text-muted-foreground">総資産価値</span>
            <span className="font-semibold">🪙 {totalValue.toLocaleString()}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
