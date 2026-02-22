"use client";

import type { UserPreferences } from "@/lib/types";

interface PreferenceTagsProps {
  preferences: Partial<UserPreferences>;
  onRemove?: (key: string, value: string) => void;
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

interface Tag {
  label: string;
  value: string;
  key: string;
}

export default function PreferenceTags({ preferences, onRemove }: PreferenceTagsProps) {
  const tags: Tag[] = [];

  if (preferences.style) {
    tags.push({ label: "Style", value: preferences.style, key: "style" });
  }
  if (preferences.room_type) {
    tags.push({ label: "Room", value: preferences.room_type, key: "room_type" });
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
    tags.push({ label: "Budget", value: range, key: "budget" });
  }
  for (const c of preferences.colors ?? []) {
    tags.push({ label: "Color", value: c, key: "colors" });
  }
  for (const l of preferences.lifestyle ?? []) {
    tags.push({ label: "Lifestyle", value: l, key: "lifestyle" });
  }
  for (const m of preferences.must_haves ?? []) {
    tags.push({ label: "Must-have", value: m, key: "must_haves" });
  }
  for (const d of preferences.dealbreakers ?? []) {
    tags.push({ label: "Avoid", value: d, key: "dealbreakers" });
  }
  for (const e of preferences.existing_furniture ?? []) {
    tags.push({ label: "Has already", value: e, key: "existing_furniture" });
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
            key={`${tag.key}-${tag.value}-${i}`}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.375rem",
              padding: "0.3125rem 0.625rem",
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
            {onRemove && (
              <button
                type="button"
                onClick={() => onRemove(tag.key, tag.value)}
                title={`Remove ${tag.label}`}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginLeft: "0.125rem",
                  width: "14px",
                  height: "14px",
                  borderRadius: "50%",
                  background: "transparent",
                  border: "none",
                  color: color,
                  cursor: "pointer",
                  opacity: 0.5,
                  padding: 0,
                  lineHeight: 1,
                  fontSize: "0.875rem",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.opacity = "1"; }}
                onMouseLeave={(e) => { e.currentTarget.style.opacity = "0.5"; }}
              >
                ×
              </button>
            )}
          </span>
        );
      })}
    </div>
  );
}
