"use client";

import { Dashboard } from "@/components/dashboard/Dashboard";
import { Onboarding } from "@/components/settings/Onboarding";
import { Skeleton } from "@/components/ui/misc";
import { usePreferences } from "@/hooks/usePodcast";

// Home: onboarding until the user has interests set, then the dashboard (PRD 10).
export default function Home() {
  const prefs = usePreferences();

  if (prefs.isLoading) {
    return (
      <div className="flex flex-col gap-4 pt-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  const needsOnboarding = !prefs.data || prefs.data.interests.length === 0;
  return needsOnboarding ? <Onboarding /> : <Dashboard />;
}
