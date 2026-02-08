"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import {
  getMyInsights,
  getMyReports,
  getDailyStudy,
  UserInsight,
  WeeklyReport,
  DailyStudy,
} from "@/lib/api";
import InsightCard from "@/components/InsightCard";
import StudyHeatmap from "@/components/StudyHeatmap";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function InsightsPage() {
  const router = useRouter();
  const [insights, setInsights] = useState<UserInsight[]>([]);
  const [reports, setReports] = useState<WeeklyReport[]>([]);
  const [dailyStudy, setDailyStudy] = useState<DailyStudy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    async function fetchData() {
      try {
        const [insightsData, reportsData, dailyData] = await Promise.all([
          getMyInsights(),
          getMyReports(),
          getDailyStudy(90),
        ]);
        setInsights(insightsData);
        setReports(reportsData);
        setDailyStudy(dailyData);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [router]);

  if (loading) return <LoadingSpinner label="読み込み中..." />;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader title="AIインサイト" description="AIが分析した学習パターンと提案" />

      <div className="mt-6 space-y-6">
        {/* Heatmap */}
        <StudyHeatmap data={dailyStudy} />

        <Tabs defaultValue="insights">
          <TabsList>
            <TabsTrigger value="insights">インサイト</TabsTrigger>
            <TabsTrigger value="reports">週次レポート</TabsTrigger>
          </TabsList>

          <TabsContent value="insights" className="space-y-3 mt-4">
            {insights.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                まだインサイトがありません。Discordで `/insights preview` を試してみましょう！
              </p>
            ) : (
              insights.map((ins) => (
                <InsightCard
                  key={ins.id}
                  type={ins.insight_type}
                  title={ins.title}
                  body={ins.body}
                  confidence={ins.confidence}
                />
              ))
            )}
          </TabsContent>

          <TabsContent value="reports" className="space-y-3 mt-4">
            {reports.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                まだ週次レポートがありません
              </p>
            ) : (
              reports.map((report) => (
                <Card key={report.id}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">
                      {report.week_start} 〜 {report.week_end}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm whitespace-pre-line">{report.summary}</p>
                    {report.insights.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {report.insights.map((ins: { title: string; body: string }, i: number) => (
                          <p key={i} className="text-xs text-muted-foreground">
                            - {ins.title}: {ins.body}
                          </p>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
