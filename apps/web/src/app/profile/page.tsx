"use client";

import { useEffect, useState } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import PageHeader from "@/components/PageHeader";
import { getProfileDetail, updateProfile, ProfileDetail } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export default function ProfilePage() {
  const authenticated = useAuthGuard();
  const [profile, setProfile] = useState<ProfileDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);

  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [timezone, setTimezone] = useState("Asia/Tokyo");
  const [dailyGoal, setDailyGoal] = useState(60);

  useEffect(() => {
    if (authenticated) fetchProfile();
  }, [authenticated]);

  async function fetchProfile() {
    try {
      const data = await getProfileDetail();
      setProfile(data);
      if (data.preferences) {
        setDisplayName(data.preferences.display_name || data.username);
        setBio(data.preferences.bio || "");
        setTimezone(data.preferences.timezone || "Asia/Tokyo");
        setDailyGoal(data.preferences.daily_goal_minutes || 60);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      const updated = await updateProfile({
        display_name: displayName,
        bio,
        timezone,
        daily_goal_minutes: dailyGoal,
      });
      setProfile(updated);
      setEditMode(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新に失敗しました");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingSpinner />;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <PageHeader
        title="プロフィール"
        action={
          profile && (
            <Button
              variant={editMode ? "outline" : "default"}
              onClick={() => setEditMode(!editMode)}
            >
              {editMode ? "キャンセル" : "編集"}
            </Button>
          )
        }
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {profile && (
        <div className="space-y-6">
          {/* Profile Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">
                {profile.preferences?.custom_title
                  ? `${profile.username} | ${profile.preferences.custom_title}`
                  : profile.username}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                <div className="rounded-lg border bg-card p-3 text-center">
                  <p className="text-sm text-muted-foreground">レベル</p>
                  <p className="text-xl font-bold text-primary">Lv.{profile.level}</p>
                </div>
                <div className="rounded-lg border bg-card p-3 text-center">
                  <p className="text-sm text-muted-foreground">XP</p>
                  <p className="text-xl font-bold text-yellow-400">{profile.xp.toLocaleString()}</p>
                </div>
                <div className="rounded-lg border bg-card p-3 text-center">
                  <p className="text-sm text-muted-foreground">ランク</p>
                  <p className="text-xl font-bold">#{profile.rank}</p>
                </div>
                <div className="rounded-lg border bg-card p-3 text-center">
                  <p className="text-sm text-muted-foreground">コイン</p>
                  <p className="text-xl font-bold text-yellow-400">{profile.coins.toLocaleString()}</p>
                </div>
              </div>

              {profile.preferences?.bio && !editMode && (
                <p className="text-muted-foreground mt-2">{profile.preferences.bio}</p>
              )}
            </CardContent>
          </Card>

          {/* Edit Form */}
          {editMode && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">プロフィール編集</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="displayName">表示名</Label>
                    <Input
                      id="displayName"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      maxLength={100}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="bio">自己紹介</Label>
                    <Textarea
                      id="bio"
                      value={bio}
                      onChange={(e) => setBio(e.target.value)}
                      className="h-24 resize-none"
                      maxLength={200}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="timezone">タイムゾーン</Label>
                      <Input
                        id="timezone"
                        value={timezone}
                        onChange={(e) => setTimezone(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="dailyGoal">日目標（分）</Label>
                      <Input
                        id="dailyGoal"
                        type="number"
                        value={dailyGoal}
                        onChange={(e) => setDailyGoal(Number(e.target.value))}
                        min={10}
                        max={720}
                      />
                    </div>
                  </div>
                  <Button
                    onClick={handleSave}
                    disabled={saving}
                    className="w-full bg-green-600 hover:bg-green-700"
                  >
                    {saving ? "保存中..." : "保存"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
