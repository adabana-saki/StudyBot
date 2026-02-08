import { Loader2 } from "lucide-react";

export default function LoadingSpinner({
  label = "読み込み中...",
}: {
  label?: string;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
        <p className="text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}
