"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface CorrelationChartProps {
  data: Array<{ mood: number; minutes: number }>;
  title?: string;
}

export default function CorrelationChart({
  data,
  title = "気分 vs 学習時間",
}: CorrelationChartProps) {
  if (data.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="mood"
              name="気分"
              type="number"
              domain={[1, 5]}
              label={{ value: "気分", position: "insideBottom", offset: -5 }}
            />
            <YAxis
              dataKey="minutes"
              name="学習時間"
              label={{ value: "分", angle: -90, position: "insideLeft" }}
            />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Scatter data={data} fill="#8884d8" />
          </ScatterChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
