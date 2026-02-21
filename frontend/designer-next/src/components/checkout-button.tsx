"use client";

import { useState } from "react";
import { createCheckout } from "@/lib/backend";

interface CheckoutButtonProps {
  sessionId: string;
  totalPrice: number;
  currency: string;
  itemCount: number;
  disabled?: boolean;
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

export function CheckoutButton({
  sessionId,
  totalPrice,
  currency,
  itemCount,
  disabled = false,
}: CheckoutButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheckout() {
    setLoading(true);
    setError(null);

    try {
      const data = await createCheckout(sessionId);

      if (data.payment_link) {
        window.open(data.payment_link, "_blank");
      } else {
        throw new Error("No payment link returned");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setLoading(false);
    }
  }

  const isDisabled = disabled || itemCount === 0 || loading;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
      <button
        type="button"
        onClick={handleCheckout}
        disabled={isDisabled}
        style={{
          background: isDisabled ? "rgba(26,26,56,0.06)" : "var(--stripe-purple)",
          color: isDisabled ? "var(--muted)" : "#fff",
          padding: "0.75rem",
          borderRadius: "var(--radius-full)",
          fontWeight: 500,
          fontSize: "0.875rem",
          letterSpacing: "0.02em",
          cursor: isDisabled ? "not-allowed" : "pointer",
          transition: "all var(--transition-slow)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "0.5rem",
          border: "none",
          opacity: isDisabled ? 0.5 : 1,
        }}
      >
        {loading ? (
          <span style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
            <span
              style={{
                width: "14px",
                height: "14px",
                border: "2px solid rgba(255,255,255,0.3)",
                borderTopColor: "#fff",
                borderRadius: "50%",
                animation: "spin 0.6s linear infinite",
                display: "inline-block",
              }}
            />
            Creating payment link...
          </span>
        ) : (
          <>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
              <line x1="1" y1="10" x2="23" y2="10" />
            </svg>
            Purchase {itemCount} item{itemCount !== 1 ? "s" : ""} —{" "}
            {formatPrice(totalPrice, currency)}
          </>
        )}
      </button>

      {error && (
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--error)",
            padding: "0.375rem 0.75rem",
            borderRadius: "var(--radius-full)",
            background: "var(--error-subtle)",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
