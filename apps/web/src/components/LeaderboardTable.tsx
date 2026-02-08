"use client";

import { LeaderboardEntry } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface LeaderboardTableProps {
  entries: LeaderboardEntry[];
}

function getRankStyle(rank: number): string {
  switch (rank) {
    case 1:
      return "text-yellow-400 font-bold";
    case 2:
      return "text-gray-300 font-bold";
    case 3:
      return "text-amber-600 font-bold";
    default:
      return "text-muted-foreground";
  }
}

function getRankIcon(rank: number): string {
  switch (rank) {
    case 1:
      return "🥇";
    case 2:
      return "🥈";
    case 3:
      return "🥉";
    default:
      return `#${rank}`;
  }
}

export default function LeaderboardTable({ entries }: LeaderboardTableProps) {
  if (entries.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <p className="text-muted-foreground">データがありません</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16">順位</TableHead>
            <TableHead>ユーザー</TableHead>
            <TableHead className="text-right w-24">スコア</TableHead>
            <TableHead className="text-right w-20">レベル</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map((entry) => (
            <TableRow key={entry.user_id}>
              <TableCell className={cn("text-sm", getRankStyle(entry.rank))}>
                {getRankIcon(entry.rank)}
              </TableCell>
              <TableCell>
                <div className="flex items-center space-x-3">
                  {entry.avatar_url ? (
                    <img
                      src={entry.avatar_url}
                      alt={entry.display_name}
                      className="w-8 h-8 rounded-full"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-sm font-bold">
                      {entry.display_name.charAt(0)}
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-medium">
                      {entry.display_name}
                    </p>
                    <p className="text-xs text-muted-foreground">@{entry.username}</p>
                  </div>
                </div>
              </TableCell>
              <TableCell className="text-right text-sm font-semibold text-primary">
                {entry.value.toLocaleString()}
              </TableCell>
              <TableCell className="text-right text-sm text-muted-foreground">
                Lv.{entry.level}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
