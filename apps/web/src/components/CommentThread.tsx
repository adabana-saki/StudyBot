"use client";

import { useEffect, useState } from "react";
import { getComments, addComment, deleteComment, CommentResponse } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";

interface CommentThreadProps {
  eventId: number;
  onCommentCountChange: (count: number) => void;
}

export default function CommentThread({ eventId, onCommentCountChange }: CommentThreadProps) {
  const [comments, setComments] = useState<CommentResponse[]>([]);
  const [newComment, setNewComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchComments();
  }, [eventId]);

  const fetchComments = async () => {
    try {
      const data = await getComments(eventId);
      setComments(data);
      onCommentCountChange(data.length);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim() || submitting) return;

    setSubmitting(true);
    try {
      const comment = await addComment(eventId, newComment.trim());
      setComments((prev) => [...prev, comment]);
      setNewComment("");
      onCommentCountChange(comments.length + 1);
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (commentId: number) => {
    try {
      await deleteComment(commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
      onCommentCountChange(comments.length - 1);
    } catch {
      // ignore
    }
  };

  const timeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "たった今";
    if (mins < 60) return `${mins}分前`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}時間前`;
    return `${Math.floor(hours / 24)}日前`;
  };

  if (loading) return <div className="text-xs text-muted-foreground py-2">読み込み中...</div>;

  return (
    <div className="border-t pt-2 mt-2 space-y-2">
      {comments.map((comment) => (
        <div key={comment.id} className="flex items-start gap-2 group">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium">{comment.username}</span>
              <span className="text-xs text-muted-foreground">{timeAgo(comment.created_at)}</span>
            </div>
            <p className="text-sm text-muted-foreground">{comment.body}</p>
          </div>
          <button
            onClick={() => handleDelete(comment.id)}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      ))}

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="コメントを入力..."
          className="text-sm h-8"
          maxLength={500}
        />
        <Button type="submit" size="sm" disabled={!newComment.trim() || submitting}>
          送信
        </Button>
      </form>
    </div>
  );
}
