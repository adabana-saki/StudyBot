"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface StudyChartProps {
  data: { day: string; total_minutes: number }[];
}

export default function StudyChart({ data }: StudyChartProps) {
  const formattedData = data.map((item) => {
    const date = new Date(item.day);
    const label = `${(date.getMonth() + 1).toString().padStart(2, "0")}/${date.getDate().toString().padStart(2, "0")}`;
    return { ...item, label };
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>学習時間の推移</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={formattedData}
              margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
            >
              <defs>
                <linearGradient id="colorMinutes" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#5865F2" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#5865F2" stopOpacity={0.1} />
                </linearGradient>
              </defs>
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
                tickFormatter={(value) => `${value}分`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(217 33% 12%)",
                  border: "1px solid hsl(217 33% 22%)",
                  borderRadius: "8px",
                  color: "hsl(210 40% 98%)",
                }}
                formatter={(value: number) => [`${value}分`, "学習時間"]}
                labelFormatter={(label) => `日付: ${label}`}
              />
              <Area
                type="monotone"
                dataKey="total_minutes"
                stroke="#5865F2"
                strokeWidth={2}
                fill="url(#colorMinutes)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
