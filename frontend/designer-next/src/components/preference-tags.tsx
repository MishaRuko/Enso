"use client";

import type { UserPreferences } from "@/lib/types";

interface PreferenceTagsProps {
  preferences: Partial<UserPreferences>;
}

const COLORS: Record<string, string> = {
  Style: "#3b82f6",
  Room: "#8b5cf6",
  Budget: "#22c55e",
  Color: "#f59e0b",
  Lifestyle: "#ec4899",
  "Must-have": "#14b8a6",
  Avoid: "#ef4444",
  "Has already": "#6366f1",
};

export default function PreferenceTags({ preferences }: PreferenceTagsProps) {
  const tags: { label: string; value: string }[] = [];

  if (preferences.style) {
    tags.push({ label: "Style", value: preferences.style });
  }
  if (preferences.room_type) {
    tags.push({ label: "Room", value: preferences.room_type });
  }
  if (preferences.budget_min || preferences.budget_max) {
    const min = preferences.budget_min ?? 0;
    const max = preferences.budget_max ?? 0;
    const currency = preferences.currency ?? "EUR";
    const range =
      min && max
        ? `${min.toLocaleString()}–${max.toLocaleString()} ${currency}`
        : max
          ? `up to ${max.toLocaleString()} ${currency}`
          : `from ${min.toLocaleString()} ${currency}`;
    tags.push({ label: "Budget", value: range });
  }
  for (const c of preferences.colors ?? []) {
    tags.push({ label: "Color", value: c });
  }
  for (const l of preferences.lifestyle ?? []) {
    tags.push({ label: "Lifestyle", value: l });
  }
  for (const m of preferences.must_haves ?? []) {
    tags.push({ label: "Must-have", value: m });
  }
  for (const d of preferences.dealbreakers ?? []) {
    tags.push({ label: "Avoid", value: d });
  }
  for (const e of preferences.existing_furniture ?? []) {
    tags.push({ label: "Has already", value: e });
  }

  if (tags.length === 0) {
    return (
      <p
        style={{
          color: "var(--muted)",
          fontSize: "0.8125rem",
          fontStyle: "italic",
          padding: "0.25rem 0",
        }}
      >
        Preferences will appear here as you talk...
      </p>
    );
  }

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
      {tags.map((tag, i) => {
        const color = COLORS[tag.label] ?? "#6b7280";
        return (
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
              background: `${color}15`,
              border: `1px solid ${color}35`,
              color: color,
              animation: `fadeIn 0.25s ease-out both`,
              animationDelay: `${i * 0.04}s`,
            }}
          >
            <span
              style={{
                fontSize: "0.625rem",
                opacity: 0.7,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                fontWeight: 700,
              }}
            >
              {tag.label}
            </span>
            {tag.value}
          </span>
        );
      })}
    </div>
  );
}
