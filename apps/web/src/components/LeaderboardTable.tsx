"use client";

import { LeaderboardEntry } from "@/lib/api";

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
      return "text-gray-400";
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
      <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
        <p className="text-gray-400">データがありません</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-700">
            <th className="px-4 py-3 text-left text-sm font-medium text-gray-400 w-16">
              順位
            </th>
            <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">
              ユーザー
            </th>
            <th className="px-4 py-3 text-right text-sm font-medium text-gray-400 w-24">
              スコア
            </th>
            <th className="px-4 py-3 text-right text-sm font-medium text-gray-400 w-20">
              レベル
            </th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr
              key={entry.user_id}
              className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors"
            >
              <td
                className={`px-4 py-3 text-sm ${getRankStyle(entry.rank)}`}
              >
                {getRankIcon(entry.rank)}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center space-x-3">
                  {entry.avatar_url ? (
                    <img
                      src={entry.avatar_url}
                      alt={entry.display_name}
                      className="w-8 h-8 rounded-full"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-blurple flex items-center justify-center text-white text-sm font-bold">
                      {entry.display_name.charAt(0)}
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-medium text-white">
                      {entry.display_name}
                    </p>
                    <p className="text-xs text-gray-500">@{entry.username}</p>
                  </div>
                </div>
              </td>
              <td className="px-4 py-3 text-right text-sm font-semibold text-blurple">
                {entry.value.toLocaleString()}
              </td>
              <td className="px-4 py-3 text-right text-sm text-gray-300">
                Lv.{entry.level}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
