"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { WellnessLog } from "@/lib/api";

interface WellnessChartProps {
  data: WellnessLog[];
}

interface ChartDataPoint {
  label: string;
  mood: number;
  energy: number;
  stress: number;
}

const LABEL_MAP: Record<string, string> = {
  mood: "気分",
  energy: "エネルギー",
  stress: "ストレス",
};

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { color: string; dataKey: string; value: number }[];
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
      <p className="text-muted-foreground text-sm mb-2">{label}</p>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center space-x-2 text-sm">
          <span
            className="inline-block w-3 h-3 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-muted-foreground">
            {LABEL_MAP[entry.dataKey] || entry.dataKey}:
          </span>
          <span className="text-foreground font-medium">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function WellnessChart({ data }: WellnessChartProps) {
  // Sort data by date ascending and format for the chart
  const chartData: ChartDataPoint[] = [...data]
    .sort(
      (a, b) =>
        new Date(a.logged_at).getTime() - new Date(b.logged_at).getTime()
    )
    .map((item) => {
      const date = new Date(item.logged_at);
      const label = `${(date.getMonth() + 1).toString().padStart(2, "0")}/${date.getDate().toString().padStart(2, "0")}`;
      return {
        label,
        mood: item.mood,
        energy: item.energy,
        stress: item.stress,
      };
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle>7日間のウェルネス推移</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
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
                domain={[1, 5]}
                ticks={[1, 2, 3, 4, 5]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                formatter={(value: string) => (
                  <span className="text-muted-foreground text-sm">
                    {LABEL_MAP[value] || value}
                  </span>
                )}
              />
              <Line
                type="monotone"
                dataKey="mood"
                stroke="#3B82F6"
                strokeWidth={2}
                dot={{ fill: "#3B82F6", r: 4 }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="energy"
                stroke="#22C55E"
                strokeWidth={2}
                dot={{ fill: "#22C55E", r: 4 }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="stress"
                stroke="#EF4444"
                strokeWidth={2}
                dot={{ fill: "#EF4444", r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
