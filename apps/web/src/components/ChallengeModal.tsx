"use client";

import { useState, useEffect, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { generateChallenge, verifyChallenge, ChallengeGenerateResponse, ChallengeVerifyResponse } from "@/lib/api";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

interface ChallengeModalProps {
  open: boolean;
  onClose: () => void;
  challengeMode: string;
  difficulty: number;
  onSuccess: (dismissedUntil: Date) => void;
}

export default function ChallengeModal({
  open,
  onClose,
  challengeMode,
  difficulty,
  onSuccess,
}: ChallengeModalProps) {
  const [loading, setLoading] = useState(false);
  const [challenge, setChallenge] = useState<ChallengeGenerateResponse | null>(null);
  const [mathAnswers, setMathAnswers] = useState<string[]>([]);
  const [typingAnswers, setTypingAnswers] = useState<string[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [result, setResult] = useState<ChallengeVerifyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open && !challenge) {
      loadChallenge();
    }
    if (!open) {
      setChallenge(null);
      setMathAnswers([]);
      setTypingAnswers([]);
      setCurrentIdx(0);
      setResult(null);
      setError(null);
    }
  }, [open]);

  const loadChallenge = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await generateChallenge(challengeMode, difficulty);
      setChallenge(data);
      if (challengeMode === "math") {
        setMathAnswers(new Array(data.problems.length).fill(""));
      } else {
        setTypingAnswers(new Array(data.problems.length).fill(""));
      }
      setCurrentIdx(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "チャレンジの生成に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (challenge && inputRef.current) {
      inputRef.current.focus();
    }
  }, [challenge, currentIdx]);

  const handleSubmit = async () => {
    if (!challenge) return;
    setLoading(true);
    setError(null);
    try {
      const answers = challengeMode === "math"
        ? mathAnswers.map((a) => parseInt(a) || 0)
        : typingAnswers;
      const res = await verifyChallenge(challenge.challenge_id, answers);
      setResult(res);
      if (res.correct && res.dismissed_until) {
        setTimeout(() => {
          onSuccess(new Date(res.dismissed_until!));
          onClose();
        }, 1500);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "検証に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleMathNext = () => {
    if (challenge && currentIdx < challenge.problems.length - 1) {
      setCurrentIdx(currentIdx + 1);
    }
  };

  const handleMathPrev = () => {
    if (currentIdx > 0) {
      setCurrentIdx(currentIdx - 1);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {challengeMode === "math" ? "🧮 計算チャレンジ" : "⌨️ タイピングチャレンジ"}
            <Badge variant="outline">難易度 {difficulty}</Badge>
          </DialogTitle>
        </DialogHeader>

        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-destructive text-sm">
            {error}
          </div>
        )}

        {loading && !challenge && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Result */}
        {result && (
          <div className={`rounded-lg p-4 text-center ${result.correct ? "bg-green-500/10" : "bg-destructive/10"}`}>
            {result.correct ? (
              <>
                <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-2" />
                <p className="font-bold text-green-600">正解！一時解除されます</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {result.score}/{result.total} 正解
                  {result.accuracy !== undefined && ` (精度: ${result.accuracy}%)`}
                </p>
              </>
            ) : (
              <>
                <XCircle className="h-12 w-12 text-destructive mx-auto mb-2" />
                <p className="font-bold text-destructive">不正解</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {result.score}/{result.total} 正解
                  {result.accuracy !== undefined && ` (精度: ${result.accuracy}%)`}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => {
                    setResult(null);
                    loadChallenge();
                  }}
                >
                  もう一度挑戦
                </Button>
              </>
            )}
          </div>
        )}

        {/* Math Challenge */}
        {challenge && challengeMode === "math" && !result && (
          <div className="space-y-4">
            <div className="text-center">
              <p className="text-sm text-muted-foreground mb-2">
                問題 {currentIdx + 1} / {challenge.problems.length}
              </p>
              <p className="text-3xl font-mono font-bold mb-4">
                {(challenge.problems[currentIdx] as { expression?: string }).expression} = ?
              </p>
              <Input
                ref={inputRef}
                type="number"
                value={mathAnswers[currentIdx] || ""}
                onChange={(e) => {
                  const newAnswers = [...mathAnswers];
                  newAnswers[currentIdx] = e.target.value;
                  setMathAnswers(newAnswers);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    if (currentIdx < challenge.problems.length - 1) {
                      handleMathNext();
                    } else {
                      handleSubmit();
                    }
                  }
                }}
                placeholder="回答を入力"
                className="text-center text-2xl font-mono max-w-[200px] mx-auto"
              />
            </div>

            <div className="flex justify-between items-center">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleMathPrev}
                disabled={currentIdx === 0}
              >
                前へ
              </Button>
              <div className="flex gap-1">
                {challenge.problems.map((_, i) => (
                  <div
                    key={i}
                    className={`w-2 h-2 rounded-full ${
                      i === currentIdx
                        ? "bg-primary"
                        : mathAnswers[i]
                          ? "bg-primary/40"
                          : "bg-muted-foreground/30"
                    }`}
                  />
                ))}
              </div>
              {currentIdx < challenge.problems.length - 1 ? (
                <Button variant="ghost" size="sm" onClick={handleMathNext}>
                  次へ
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={handleSubmit}
                  disabled={loading || mathAnswers.some((a) => !a)}
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "送信"}
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Typing Challenge */}
        {challenge && challengeMode === "typing" && !result && (
          <div className="space-y-4">
            {challenge.problems.map((phrase, i) => (
              <div key={i} className="space-y-1">
                <p className="text-sm font-medium text-muted-foreground">
                  フレーズ {i + 1}:
                </p>
                <p className="text-base font-bold bg-muted/50 p-2 rounded">
                  {phrase as string}
                </p>
                <Textarea
                  value={typingAnswers[i] || ""}
                  onChange={(e) => {
                    const newAnswers = [...typingAnswers];
                    newAnswers[i] = e.target.value;
                    setTypingAnswers(newAnswers);
                  }}
                  placeholder="上のフレーズを正確に入力してください"
                  rows={2}
                  className="text-sm"
                />
                {typingAnswers[i] && typingAnswers[i] === phrase ? (
                  <p className="text-xs text-green-500 flex items-center gap-1">
                    <CheckCircle className="h-3 w-3" /> 一致
                  </p>
                ) : typingAnswers[i] ? (
                  <p className="text-xs text-destructive flex items-center gap-1">
                    <XCircle className="h-3 w-3" /> 不一致
                  </p>
                ) : null}
              </div>
            ))}

            <Button
              onClick={handleSubmit}
              disabled={loading || typingAnswers.some((a) => !a)}
              className="w-full"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              送信
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
