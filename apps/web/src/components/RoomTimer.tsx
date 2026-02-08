"use client";

import { useEffect, useRef, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Timer, LogOut } from "lucide-react";

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [
    h.toString().padStart(2, "0"),
    m.toString().padStart(2, "0"),
    s.toString().padStart(2, "0"),
  ].join(":");
}

interface RoomTimerProps {
  onLeave: () => void;
}

export default function RoomTimer({ onLeave }: RoomTimerProps) {
  const [elapsed, setElapsed] = useState(0);
  const startTimeRef = useRef(Date.now());

  useEffect(() => {
    startTimeRef.current = Date.now();

    function update() {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }

    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card>
      <CardContent className="p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Timer className="h-5 w-5 text-primary" />
          <div>
            <div className="text-sm text-muted-foreground">学習中</div>
            <div className="text-2xl font-mono font-bold tracking-wider">
              {formatTime(elapsed)}
            </div>
          </div>
        </div>
        <Button variant="destructive" onClick={onLeave} className="gap-2">
          <LogOut className="h-4 w-4" />
          退出する
        </Button>
      </CardContent>
    </Card>
  );
}
