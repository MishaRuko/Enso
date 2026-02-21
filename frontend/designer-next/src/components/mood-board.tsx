"use client";

export interface MoodBoardItem {
  imageUrl: string;
  category: string;
  description: string;
}

interface MoodBoardProps {
  items: MoodBoardItem[];
}

const categoryColors: Record<string, string> = {
  furniture: "#3b82f6",
  color: "#f59e0b",
  texture: "#8b5cf6",
  style: "#ec4899",
  lighting: "#22c55e",
  decor: "#14b8a6",
  material: "#f97316",
};

export default function MoodBoard({ items }: MoodBoardProps) {
  if (items.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "200px",
          border: "2px dashed var(--border)",
          borderRadius: "var(--radius-lg)",
          color: "var(--muted)",
          fontSize: "0.8125rem",
          textAlign: "center",
          padding: "2rem",
          gap: "0.75rem",
          background: "rgba(255,255,255,0.01)",
        }}
      >
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          style={{ opacity: 0.4 }}
        >
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
        <span>
          The AI consultant will add inspiration images here as you describe your style...
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
        gap: "0.75rem",
      }}
    >
      {items.map((item, i) => (
        <div
          key={`${item.imageUrl}-${i}`}
          style={{
            borderRadius: "var(--radius-lg)",
            overflow: "hidden",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            animation: "moodFadeIn 0.4s ease-out",
            transition: "border-color var(--transition-base), box-shadow var(--transition-base)",
          }}
        >
          <div
            style={{
              width: "100%",
              aspectRatio: "1",
              background: `url(${item.imageUrl}) center/cover no-repeat`,
              backgroundColor: "#1a1a2e",
            }}
          />
          <div style={{ padding: "0.5rem 0.75rem" }}>
            <span
              style={{
                display: "inline-block",
                fontSize: "0.625rem",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                padding: "0.125rem 0.5rem",
                borderRadius: "var(--radius-full)",
                background: `${categoryColors[item.category.toLowerCase()] ?? "#6b7280"}15`,
                color: categoryColors[item.category.toLowerCase()] ?? "#6b7280",
                marginBottom: "0.25rem",
              }}
            >
              {item.category}
            </span>
            <p
              style={{
                fontSize: "0.75rem",
                color: "var(--muted)",
                lineHeight: 1.4,
                margin: 0,
              }}
            >
              {item.description}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
