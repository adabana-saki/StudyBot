import { X } from "lucide-react";

export default function ErrorBanner({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss: () => void;
}) {
  return (
    <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 mb-4 text-destructive text-sm flex items-center justify-between">
      <span>{message}</span>
      <button
        onClick={onDismiss}
        className="ml-2 hover:text-destructive/80 transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
