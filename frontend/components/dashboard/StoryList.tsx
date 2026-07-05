"use client";

import { ExternalLink } from "lucide-react";

import { Badge } from "@/components/ui/misc";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatRelative } from "@/lib/utils";
import type { Story } from "@/types/domain";

// Today's Stories (PRD 10): headline, summary, source, link, timestamp.
export function StoryList({ stories }: { stories: Story[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Today&apos;s Stories</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {stories.map((s, i) => (
          <div key={i} className="flex flex-col gap-1 border-b border-border pb-4 last:border-0 last:pb-0">
            <div className="flex items-center gap-2">
              <Badge>{s.source}</Badge>
              {s.published_at ? (
                <span className="text-xs text-muted-foreground">
                  {formatRelative(s.published_at)}
                </span>
              ) : null}
            </div>
            <a
              href={s.url}
              target="_blank"
              rel="noreferrer"
              className="group flex items-start gap-1 font-medium hover:text-primary"
            >
              {s.headline}
              <ExternalLink size={14} className="mt-1 opacity-0 group-hover:opacity-100" />
            </a>
            {s.summary ? (
              <p className="text-sm text-muted-foreground">{s.summary}</p>
            ) : null}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
