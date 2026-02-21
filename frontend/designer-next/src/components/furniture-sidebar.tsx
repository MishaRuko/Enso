"use client";

import { useState } from "react";
import type { FurnitureItem } from "@/lib/types";
import { generateMiroBoard } from "@/lib/backend";
import { CheckoutButton } from "./checkout-button";
import { EnsoLogo } from "./enso-logo";

interface FurnitureSidebarProps {
  sessionId: string;
  items: FurnitureItem[];
  onApprove?: (selectedIds: string[]) => void;
}

function formatPrice(price: number, currency: string): string {
  try {
    return new Intl.NumberFormat("en-IE", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price);
  } catch {
    return `${currency} ${price.toFixed(0)}`;
  }
}

export function FurnitureSidebar({ sessionId, items, onApprove }: FurnitureSidebarProps) {
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(items.filter((i) => i.selected).map((i) => i.id)),
  );
  const [miroLoading, setMiroLoading] = useState(false);
  const [miroUrl, setMiroUrl] = useState<string | null>(null);

  function toggleItem(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const total = items.filter((i) => selected.has(i.id)).reduce((sum, i) => sum + i.price, 0);

  const currency = items[0]?.currency ?? "EUR";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "rgba(250,249,247,0.96)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        borderLeft: "1px solid var(--border)",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "1rem 1.25rem",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <EnsoLogo size={16} color="#1a1a38" />
          <span style={{ fontWeight: 600, fontSize: "0.875rem", letterSpacing: "0.01em" }}>
            Curated Pieces
          </span>
        </div>
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 500,
            padding: "0.125rem 0.625rem",
            borderRadius: "var(--radius-full)",
            background: "var(--parchment-subtle)",
            color: "#1a1a38",
            letterSpacing: "0.02em",
          }}
        >
          {items.length}
        </span>
      </div>

      {/* Item list */}
      <div style={{ flex: 1, overflowY: "auto", padding: "0.5rem" }}>
        {items.map((item, i) => {
          const isSelected = selected.has(item.id);
          return (
            <label
              key={item.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                padding: "0.75rem",
                borderRadius: "var(--radius-lg)",
                cursor: "pointer",
                transition: "all var(--transition-fast)",
                background: isSelected ? "rgba(236,230,219,0.35)" : "transparent",
                border: `1px solid ${isSelected ? "rgba(236,230,219,0.7)" : "transparent"}`,
                animation: `fadeUp 0.3s ease-out ${i * 0.03}s both`,
              }}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggleItem(item.id)}
                style={{
                  accentColor: "#1a1a38",
                  width: "16px",
                  height: "16px",
                  flexShrink: 0,
                }}
              />

              {/* Thumbnail */}
              <div
                style={{
                  width: "52px",
                  height: "52px",
                  borderRadius: "var(--radius-md)",
                  overflow: "hidden",
                  background: "rgba(26,26,56,0.03)",
                  border: "1px solid var(--border)",
                  flexShrink: 0,
                }}
              >
                {item.image_url ? (
                  <img
                    src={item.image_url}
                    alt={item.name}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                    }}
                  />
                ) : (
                  <div
                    style={{
                      width: "100%",
                      height: "100%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "var(--muted)",
                    }}
                  >
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                  </div>
                )}
              </div>

              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: "0.8125rem",
                    fontWeight: 500,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    marginBottom: "0.125rem",
                  }}
                >
                  {item.name}
                </div>
                <div style={{ fontSize: "0.6875rem", color: "var(--muted)" }}>
                  {item.retailer}
                  {item.dimensions && (
                    <span style={{ marginLeft: "0.375rem", opacity: 0.7 }}>
                      {item.dimensions.width_cm}x{item.dimensions.depth_cm}cm
                    </span>
                  )}
                </div>
              </div>

              {/* Price */}
              <div
                style={{
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                  color: isSelected ? "#1a1a38" : "var(--text-secondary)",
                  transition: "color var(--transition-fast)",
                }}
              >
                {formatPrice(item.price, item.currency)}
              </div>
            </label>
          );
        })}
      </div>

      {/* Footer -- total + actions */}
      <div
        style={{
          padding: "1rem 1.25rem",
          borderTop: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
          background: "rgba(250,249,247,0.98)",
        }}
      >
        {/* Budget indicator bar */}
        <div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "0.8125rem",
              marginBottom: "0.5rem",
            }}
          >
            <span style={{ color: "var(--muted)" }}>
              Total ({selected.size} of {items.length})
            </span>
            <span style={{ fontWeight: 700, fontSize: "1rem" }}>
              {formatPrice(total, currency)}
            </span>
          </div>
          <div
            style={{
              height: "3px",
              borderRadius: "var(--radius-full)",
              background: "rgba(236,230,219,0.5)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${items.length > 0 ? (selected.size / items.length) * 100 : 0}%`,
                background: "var(--accent)",
                borderRadius: "var(--radius-full)",
                transition: "width 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
              }}
            />
          </div>
        </div>

        <button
          type="button"
          onClick={() => onApprove?.(Array.from(selected))}
          disabled={selected.size === 0}
          style={{
            background: selected.size > 0 ? "#1a1a38" : "rgba(236,230,219,0.4)",
            color: selected.size > 0 ? "#faf9f7" : "var(--text-3)",
            padding: "0.75rem",
            borderRadius: "var(--radius-full)",
            fontWeight: 500,
            fontSize: "0.875rem",
            letterSpacing: "0.02em",
            transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
            cursor: selected.size > 0 ? "pointer" : "not-allowed",
            opacity: selected.size === 0 ? 0.5 : 1,
            border: "none",
          }}
        >
          Approve Selection
        </button>

        <CheckoutButton
          sessionId={sessionId}
          totalPrice={total}
          currency={currency}
          itemCount={selected.size}
          disabled={selected.size === 0}
        />

        {/* Miro Mood Board button */}
        {miroUrl ? (
          <a
            href={miroUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.5rem",
              background: "#ffd02f",
              color: "#050038",
              padding: "0.75rem",
              borderRadius: "var(--radius-full)",
              fontWeight: 500,
              fontSize: "0.875rem",
              textDecoration: "none",
              transition: "opacity var(--transition-fast)",
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            View Mood Board
          </a>
        ) : (
          <button
            type="button"
            disabled={miroLoading}
            onClick={async () => {
              setMiroLoading(true);
              try {
                const { miro_board_url } = await generateMiroBoard(sessionId);
                setMiroUrl(miro_board_url);
                window.open(miro_board_url, "_blank");
              } catch (err) {
                console.error("Miro board creation failed:", err);
              } finally {
                setMiroLoading(false);
              }
            }}
            style={{
              background: miroLoading ? "rgba(26,26,56,0.06)" : "#ffd02f",
              color: "#050038",
              padding: "0.75rem",
              borderRadius: "var(--radius-full)",
              fontWeight: 500,
              fontSize: "0.875rem",
              transition: "all var(--transition-slow)",
              border: "none",
              cursor: miroLoading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.5rem",
              opacity: miroLoading ? 0.7 : 1,
            }}
          >
            {miroLoading ? (
              <>
                <span
                  style={{
                    width: "14px",
                    height: "14px",
                    border: "2px solid rgba(5,0,56,0.3)",
                    borderTopColor: "#050038",
                    borderRadius: "50%",
                    animation: "spin 0.6s linear infinite",
                    display: "inline-block",
                  }}
                />
                Creating Mood Board...
              </>
            ) : (
              "Generate Mood Board"
            )}
          </button>
        )}
      </div>
    </div>
  );
}
