"use client";

import { PreferenceForm } from "@/components/settings/PreferenceForm";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePreferences, useUpdatePreferences } from "@/hooks/usePodcast";
import type { Preference } from "@/types/domain";

const DEFAULTS: Preference = {
  name: "",
  interests: [],
  voice: "rachel",
  tone: "professional",
  podcast_length: "medium",
  schedule: "07:00",
};

export function Onboarding() {
  const prefs = usePreferences();
  const update = useUpdatePreferences();

  return (
    <div className="mx-auto max-w-lg pt-6">
      <Card>
        <CardHeader>
          <CardTitle>Welcome — let&apos;s set up your podcast</CardTitle>
        </CardHeader>
        <CardContent>
          <PreferenceForm
            initial={prefs.data ?? DEFAULTS}
            saving={update.isPending}
            multiStep
            onSave={(patch) => update.mutate(patch)}
          />
        </CardContent>
      </Card>
    </div>
  );
}
