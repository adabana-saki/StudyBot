"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface StockChartProps {
  data: { price: number; recorded_date: string; volume: number }[];
  symbol: string;
}

export default function StockChart({ data, symbol }: StockChartProps) {
  const formattedData = data.map((item) => {
    const date = new Date(item.recorded_date);
    const label = `${(date.getMonth() + 1).toString().padStart(2, "0")}/${date.getDate().toString().padStart(2, "0")}`;
    return { ...item, label };
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{symbol} 株価チャート</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={formattedData}
              margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 33% 22%)" />
              <XAxis
                dataKey="label"
                stroke="hsl(215 20% 55%)"
                fontSize={12}
                tickLine={false}
              />
              <YAxis
                stroke="hsl(215 20% 55%)"
                fontSize={12}
                tickLine={false}
                tickFormatter={(value) => `¥${value}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(217 33% 12%)",
                  border: "1px solid hsl(217 33% 22%)",
                  borderRadius: "8px",
                  color: "hsl(210 40% 98%)",
                }}
                formatter={(value: number) => [`🪙 ${value}`, "株価"]}
                labelFormatter={(label) => `日付: ${label}`}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke="#00C853"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
