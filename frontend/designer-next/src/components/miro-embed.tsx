"use client";

interface MiroEmbedProps {
  boardUrl: string;
  height?: string;
}

export default function MiroEmbed({ boardUrl, height = "100%" }: MiroEmbedProps) {
  const match = boardUrl.match(/\/board\/([^/?]+)/);
  const boardId = match?.[1];

  if (!boardId) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height,
          color: "var(--muted)",
          fontSize: "0.875rem",
          border: "1px dashed var(--border)",
          borderRadius: "var(--radius-lg)",
          padding: "2rem",
        }}
      >
        Preparing vision board...
      </div>
    );
  }

  const embedUrl = `https://miro.com/app/live-embed/${boardId}/?autoplay=yep&embedMode=view_only_without_ui`;

  return (
    <div
      style={{
        width: "100%",
        height,
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
        border: "1px solid var(--border)",
        background: "var(--surface)",
        animation: "fadeIn 0.5s ease-out",
      }}
    >
      <iframe
        src={embedUrl}
        style={{ width: "100%", height: "100%", border: "none" }}
        allow="fullscreen; clipboard-read; clipboard-write"
        title="Miro Vision Board"
      />
    </div>
  );
}
