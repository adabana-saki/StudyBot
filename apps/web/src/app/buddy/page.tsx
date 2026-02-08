"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import {
  getBuddyProfile,
  getBuddyMatches,
  getAvailableBuddies,
  updateBuddyProfile,
  BuddyProfile,
  BuddyMatch,
} from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function BuddyPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<BuddyProfile | null>(null);
  const [matches, setMatches] = useState<BuddyMatch[]>([]);
  const [available, setAvailable] = useState<BuddyProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [subjects, setSubjects] = useState("");
  const [times, setTimes] = useState("");

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    async function fetchData() {
      try {
        const [profileData, matchesData, availableData] = await Promise.all([
          getBuddyProfile(),
          getBuddyMatches(),
          getAvailableBuddies(),
        ]);
        setProfile(profileData);
        setMatches(matchesData);
        setAvailable(availableData);
        if (profileData) {
          setSubjects(profileData.subjects.join(", "));
          setTimes(profileData.preferred_times.join(", "));
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [router]);

  const handleSaveProfile = async () => {
    const subjectList = subjects.split(",").map((s) => s.trim()).filter(Boolean);
    const timeList = times.split(",").map((t) => t.trim()).filter(Boolean);
    const updated = await updateBuddyProfile({
      subjects: subjectList,
      preferred_times: timeList,
      study_style: profile?.study_style || "focused",
    });
    setProfile(updated);
  };

  if (loading) return <LoadingSpinner label="読み込み中..." />;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader title="スタディバディ" description="一緒に勉強する仲間を見つけよう" />

      <Tabs defaultValue="matches" className="mt-6">
        <TabsList>
          <TabsTrigger value="matches">マッチ</TabsTrigger>
          <TabsTrigger value="available">バディ一覧</TabsTrigger>
          <TabsTrigger value="profile">プロフィール</TabsTrigger>
        </TabsList>

        <TabsContent value="matches" className="space-y-4 mt-4">
          {matches.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">
              まだマッチがありません。Discordで `/buddy find` を試してみましょう！
            </p>
          ) : (
            matches.map((m) => (
              <Card key={m.id}>
                <CardContent className="py-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium">
                      {m.username_a} & {m.username_b}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {m.subject || "教科指定なし"}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={m.status === "active" ? "default" : "secondary"}>
                      {m.status === "active" ? "アクティブ" : "終了"}
                    </Badge>
                    <span className="text-sm font-medium">
                      {Math.round(m.compatibility_score * 100)}%
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="available" className="mt-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {available.map((b) => (
              <Card key={b.user_id}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{b.username || "ユーザー"}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1">
                    <p className="text-sm">
                      <span className="text-muted-foreground">教科:</span>{" "}
                      {b.subjects.join(", ") || "未設定"}
                    </p>
                    <p className="text-sm">
                      <span className="text-muted-foreground">時間帯:</span>{" "}
                      {b.preferred_times.join(", ") || "未設定"}
                    </p>
                    <Badge variant="secondary">{b.study_style}</Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
            {available.length === 0 && (
              <p className="col-span-full text-center text-muted-foreground py-8">
                まだバディプロフィールを設定しているユーザーがいません
              </p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="profile" className="mt-4">
          <Card className="max-w-md">
            <CardHeader>
              <CardTitle>バディプロフィール</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">教科（カンマ区切り）</label>
                <Input
                  value={subjects}
                  onChange={(e) => setSubjects(e.target.value)}
                  placeholder="数学, 英語, 物理"
                />
              </div>
              <div>
                <label className="text-sm font-medium">希望時間帯（カンマ区切り）</label>
                <Input
                  value={times}
                  onChange={(e) => setTimes(e.target.value)}
                  placeholder="朝, 昼, 夜"
                />
              </div>
              <Button onClick={handleSaveProfile}>保存</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
