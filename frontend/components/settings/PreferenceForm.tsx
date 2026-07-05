"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";
import { MAX_INTEREST_LENGTH, addInterest } from "@/lib/interests";
import {
  INTEREST_OPTIONS,
  LENGTH_OPTIONS,
  TONE_OPTIONS,
  VOICE_OPTIONS,
} from "@/lib/options";
import { cn } from "@/lib/utils";
import type { Length, Preference, PreferenceUpdate, Tone, Voice } from "@/types/domain";

// Shared editor used by both onboarding (multi-step) and settings (single page).
// Business logic (mutations) lives in hooks; this only collects input (PRD 4).
export function PreferenceForm({
  initial,
  onSave,
  saving,
  multiStep = false,
  saveLabel = "Save",
}: {
  initial: Preference;
  onSave: (patch: PreferenceUpdate) => void;
  saving: boolean;
  multiStep?: boolean;
  saveLabel?: string;
}) {
  const [name, setName] = useState(initial.name);
  const [interests, setInterests] = useState<string[]>(initial.interests);
  const [voice, setVoice] = useState<Voice>(initial.voice);
  const [tone, setTone] = useState<Tone>(initial.tone);
  const [length, setLength] = useState<Length>(initial.podcast_length);
  const [schedule, setSchedule] = useState<string>(initial.schedule ?? "");
  const [customInterest, setCustomInterest] = useState("");
  const [step, setStep] = useState(0);

  function toggleInterest(i: string) {
    setInterests((cur) =>
      cur.includes(i) ? cur.filter((x) => x !== i) : [...cur, i],
    );
  }

  function addCustomInterest() {
    setInterests((cur) => addInterest(cur, customInterest));
    setCustomInterest("");
  }

  // Interests the user typed themselves (not part of the preset chips).
  const customInterests = interests.filter((i) => !INTEREST_OPTIONS.includes(i));

  function submit() {
    onSave({
      name,
      interests,
      voice,
      tone,
      podcast_length: length,
      schedule: schedule || null,
    });
  }

  const steps = [
    {
      title: "What should we call you?",
      body: (
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
          className="w-full rounded-md border border-input bg-secondary/40 px-3 py-2 outline-none focus:ring-2 focus:ring-ring"
        />
      ),
      valid: name.trim().length > 0,
    },
    {
      title: "Pick your interests",
      body: (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            {INTEREST_OPTIONS.map((i) => (
              <button
                key={i}
                type="button"
                onClick={() => toggleInterest(i)}
                className={cn(
                  "rounded-full border px-3 py-1.5 text-sm capitalize transition-colors",
                  interests.includes(i)
                    ? "border-primary bg-primary/20 text-foreground"
                    : "border-border text-muted-foreground hover:text-foreground",
                )}
              >
                {i}
              </button>
            ))}
            {customInterests.map((i) => (
              <button
                key={i}
                type="button"
                onClick={() => toggleInterest(i)}
                title="Remove"
                className="rounded-full border border-primary bg-primary/20 px-3 py-1.5 text-sm text-foreground transition-colors"
              >
                {i} ×
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <input
              value={customInterest}
              maxLength={MAX_INTEREST_LENGTH}
              onChange={(e) => setCustomInterest(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addCustomInterest();
                }
              }}
              placeholder="Add your own topic..."
              className="w-full max-w-xs rounded-md border border-input bg-secondary/40 px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
            <Button variant="ghost" size="sm" onClick={addCustomInterest}>
              Add
            </Button>
          </div>
        </div>
      ),
      valid: interests.length > 0,
    },
    {
      title: "Choose a voice",
      body: (
        <RadioGroup
          options={VOICE_OPTIONS}
          value={voice}
          onChange={(v) => setVoice(v as Voice)}
        />
      ),
      valid: true,
    },
    {
      title: "Tone and length",
      body: (
        <div className="flex flex-col gap-4">
          <div>
            <p className="mb-2 text-sm text-muted-foreground">Tone</p>
            <RadioGroup options={TONE_OPTIONS} value={tone} onChange={(v) => setTone(v as Tone)} />
          </div>
          <div>
            <p className="mb-2 text-sm text-muted-foreground">Length</p>
            <RadioGroup
              options={LENGTH_OPTIONS}
              value={length}
              onChange={(v) => setLength(v as Length)}
            />
          </div>
        </div>
      ),
      valid: true,
    },
    {
      title: "Daily delivery time (UTC)",
      body: (
        <div className="flex items-center gap-3">
          <input
            type="time"
            value={schedule}
            onChange={(e) => setSchedule(e.target.value)}
            className="rounded-md border border-input bg-secondary/40 px-3 py-2 outline-none focus:ring-2 focus:ring-ring"
          />
          {schedule ? (
            <Button variant="ghost" size="sm" onClick={() => setSchedule("")}>
              Turn off
            </Button>
          ) : (
            <span className="text-sm text-muted-foreground">Off</span>
          )}
        </div>
      ),
      valid: true,
    },
  ];

  if (!multiStep) {
    return (
      <div className="flex flex-col gap-6">
        {steps.map((s) => (
          <div key={s.title}>
            <p className="mb-2 font-medium">{s.title}</p>
            {s.body}
          </div>
        ))}
        <div>
          <Button onClick={submit} disabled={saving || !name.trim()}>
            {saving ? "Saving..." : saveLabel}
          </Button>
        </div>
      </div>
    );
  }

  const s = steps[step];
  const last = step === steps.length - 1;
  return (
    <div className="flex flex-col gap-6">
      <div className="flex gap-1.5">
        {steps.map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-1 flex-1 rounded-full",
              i <= step ? "bg-primary" : "bg-secondary",
            )}
          />
        ))}
      </div>
      <div>
        <h2 className="mb-4 text-xl font-semibold">{s.title}</h2>
        {s.body}
      </div>
      <div className="flex justify-between">
        <Button variant="ghost" onClick={() => setStep((x) => Math.max(0, x - 1))} disabled={step === 0}>
          Back
        </Button>
        {last ? (
          <Button onClick={submit} disabled={saving || !s.valid}>
            {saving ? "Saving..." : "Finish"}
          </Button>
        ) : (
          <Button onClick={() => setStep((x) => x + 1)} disabled={!s.valid}>
            Next
          </Button>
        )}
      </div>
    </div>
  );
}

function RadioGroup({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={cn(
            "flex items-center justify-between rounded-md border px-3 py-2 text-left text-sm transition-colors",
            value === o.value
              ? "border-primary bg-primary/15"
              : "border-border hover:bg-secondary",
          )}
        >
          {o.label}
          {value === o.value ? <Badge>Selected</Badge> : null}
        </button>
      ))}
    </div>
  );
}
