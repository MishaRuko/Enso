"use client";

import { useState } from "react";
import { createCheckout, selectFurniture } from "@/lib/backend";

interface CheckoutButtonProps {
  sessionId: string;
  selectedIds: string[];
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

function StripeLogo() {
  return (
    <svg width="42" height="18" viewBox="0 0 120 50" fill="currentColor" aria-label="Stripe">
      <path d="M112.5 22.1c0-7.7-3.7-13.8-10.9-13.8-7.2 0-11.5 6.1-11.5 13.7 0 9.1 5.1 13.6 12.5 13.6 3.6 0 6.3-.8 8.3-2v-6c-2 1-4.3 1.6-7.2 1.6-2.9 0-5.4-1-5.7-4.4h14.4c0-.4.1-1.8.1-2.7zm-14.6-2.9c0-3.3 2-4.6 3.8-4.6 1.8 0 3.6 1.4 3.6 4.6H97.9zM79.3 8.3c-2.9 0-4.7 1.3-5.7 2.3l-.4-1.8h-7.2v35.4l8.2-1.7V36c1 .7 2.6 1.8 5.1 1.8 5.1 0 9.8-4.1 9.8-13.2C89.1 16 84.3 8.3 79.3 8.3zm-1.7 21c-1.7 0-2.7-.6-3.4-1.4l-.1-10.6c.7-.8 1.8-1.4 3.5-1.4 2.6 0 4.5 3 4.5 6.7 0 3.8-1.8 6.7-4.5 6.7zM55.5 7l8.2-1.7V0l-8.2 1.7V7zM55.5 8.8h8.2v26.8h-8.2V8.8zM46.2 11l-.5-2.2h-7.1v26.8h8.2V17.4c1.9-2.5 5.2-2.1 6.2-1.7V8.8c-1-.4-4.8-1.2-6.8 2.2zM29 3.5L21 5.1l-.1 24.5c0 4.5 3.4 7.9 7.9 7.9 2.5 0 4.3-.5 5.4-1v-6.5c-.9.4-5.6 1.7-5.6-2.5V15.3h5.6V8.8H28.6L29 3.5zM10.9 17.5c0-1.1.9-1.6 2.5-1.6 2.2 0 5 .7 7.2 1.9V10c-2.4-1-4.8-1.3-7.2-1.3C7.4 8.6 3 12 3 17.9c0 9.2 12.7 7.7 12.7 11.7 0 1.3-1.1 1.8-2.7 1.8-2.4 0-5.4-.9-7.8-2.3v7.9c2.7 1.1 5.3 1.6 7.8 1.6 6.2 0 10.5-3.1 10.5-8.9C23.5 19.8 10.9 21.6 10.9 17.5z" />
    </svg>
  );
}

export function CheckoutButton({
  sessionId,
  selectedIds,
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
      await selectFurniture(sessionId, selectedIds);
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
          padding: "0.875rem 1rem",
          borderRadius: "var(--radius-full)",
          fontWeight: 600,
          fontSize: "0.875rem",
          letterSpacing: "0.02em",
          cursor: isDisabled ? "not-allowed" : "pointer",
          transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "0.625rem",
          border: "none",
          opacity: isDisabled ? 0.5 : 1,
          boxShadow: isDisabled ? "none" : "0 4px 16px rgba(99,91,255,0.3)",
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
            Purchase with <StripeLogo /> — {formatPrice(totalPrice, currency)}
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
