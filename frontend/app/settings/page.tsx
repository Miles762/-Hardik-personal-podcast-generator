"use client";

import { PreferenceForm } from "@/components/settings/PreferenceForm";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { usePreferences, useUpdatePreferences } from "@/hooks/usePodcast";

// Settings (PRD 10, 3.2): edit interests, voice, length, schedule, tone.
export default function SettingsPage() {
  const prefs = usePreferences();
  const update = useUpdatePreferences();

  return (
    <div className="mx-auto max-w-lg pt-2">
      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
        </CardHeader>
        <CardContent>
          {prefs.isLoading || !prefs.data ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <PreferenceForm
              initial={prefs.data}
              saving={update.isPending}
              saveLabel={update.isSuccess ? "Saved" : "Save changes"}
              onSave={(patch) => update.mutate(patch)}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
