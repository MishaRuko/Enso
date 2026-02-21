"use client";

import type { UserPreferences } from "@/lib/types";

interface PreferenceTagsProps {
  preferences: Partial<UserPreferences>;
}

export default function PreferenceTags({ preferences }: PreferenceTagsProps) {
  const tags: { label: string; value: string; color: string }[] = [];

  if (preferences.style) {
    tags.push({ label: "Style", value: preferences.style, color: "#3b82f6" });
  }
  if (preferences.room_type) {
    tags.push({ label: "Room", value: preferences.room_type, color: "#8b5cf6" });
  }
  if (preferences.budget_min || preferences.budget_max) {
    const min = preferences.budget_min ?? 0;
    const max = preferences.budget_max ?? 0;
    const currency = preferences.currency ?? "EUR";
    tags.push({
      label: "Budget",
      value: `${min.toLocaleString()}-${max.toLocaleString()} ${currency}`,
      color: "#22c55e",
    });
  }
  if (preferences.colors?.length) {
    for (const c of preferences.colors) {
      tags.push({ label: "Color", value: c, color: "#f59e0b" });
    }
  }
  if (preferences.lifestyle?.length) {
    for (const l of preferences.lifestyle) {
      tags.push({ label: "Lifestyle", value: l, color: "#ec4899" });
    }
  }
  if (preferences.must_haves?.length) {
    for (const m of preferences.must_haves) {
      tags.push({ label: "Must-have", value: m, color: "#14b8a6" });
    }
  }
  if (preferences.dealbreakers?.length) {
    for (const d of preferences.dealbreakers) {
      tags.push({ label: "Avoid", value: d, color: "#ef4444" });
    }
  }

  if (tags.length === 0) {
    return (
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.8125rem",
          padding: "1rem 0",
          fontStyle: "italic",
        }}
      >
        Preferences will appear here as you talk with the AI consultant...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
      {tags.map((tag, i) => (
        <span
          key={`${tag.label}-${tag.value}-${i}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.375rem",
            padding: "0.3125rem 0.75rem",
            borderRadius: "var(--radius-full)",
            fontSize: "0.8125rem",
            fontWeight: 500,
            background: `${tag.color}12`,
            border: `1px solid ${tag.color}30`,
            color: tag.color,
            animation: "fadeIn 0.3s ease-out",
            transition: "all var(--transition-fast)",
          }}
        >
          <span
            style={{
              fontSize: "0.625rem",
              opacity: 0.7,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
              fontWeight: 600,
            }}
          >
            {tag.label}
          </span>
          {tag.value}
        </span>
      ))}
    </div>
  );
}
