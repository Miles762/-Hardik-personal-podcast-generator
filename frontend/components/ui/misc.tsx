import { type HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-border bg-secondary/60 px-2.5 py-0.5 text-xs font-medium text-secondary-foreground",
        className,
      )}
      {...props}
    />
  );
}

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("shimmer rounded-md bg-secondary/60", className)}
      {...props}
    />
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border p-10 text-center">
      <p className="font-medium text-foreground">{title}</p>
      {hint ? <p className="text-sm text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-5 text-sm text-destructive-foreground">
      {message}
    </div>
  );
}
