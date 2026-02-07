"use client";

interface StatsCardProps {
  icon: string;
  label: string;
  value: string | number;
  color?: string;
}

export default function StatsCard({
  icon,
  label,
  value,
  color = "text-blurple",
}: StatsCardProps) {
  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-gray-600 transition-colors">
      <div className="flex items-center space-x-4">
        <span className="text-3xl">{icon}</span>
        <div>
          <p className="text-sm text-gray-400">{label}</p>
          <p className={`text-2xl font-bold ${color}`}>{value}</p>
        </div>
      </div>
    </div>
  );
}
