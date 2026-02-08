"use client";

import { type ReactNode } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function Modal({
  isOpen,
  onClose,
  title,
  maxWidth = "max-w-sm",
  children,
}: {
  isOpen: boolean;
  onClose?: () => void;
  title?: string;
  maxWidth?: string;
  children: ReactNode;
}) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose?.()}>
      <DialogContent className={maxWidth}>
        {title && (
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
          </DialogHeader>
        )}
        {children}
      </DialogContent>
    </Dialog>
  );
}
