"""Stripe checkout workflow — creates payment link for selected furniture items."""

import logging

import stripe

from ..config import STRIPE_SECRET_KEY
from ..db import get_session, list_furniture, update_session

logger = logging.getLogger(__name__)

stripe.api_key = STRIPE_SECRET_KEY


async def create_checkout(session_id: str, *, success_url: str = "") -> str:
    """Create a Stripe Payment Link for all selected furniture in a session.

    1. Load selected furniture items from DB
    2. Create a Stripe Product + Price for each item
    3. Create a PaymentLink with all line items
    4. Save payment_link URL to the session

    Returns:
        The Stripe Payment Link URL.
    """
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    items = list_furniture(session_id, selected_only=True)
    if not items:
        raise ValueError("No furniture items selected for checkout")

    line_items: list[dict] = []

    for item in items:
        # Create a Stripe Product for each furniture item
        product = stripe.Product.create(
            name=item["name"],
            metadata={
                "session_id": session_id,
                "furniture_id": item["id"],
                "retailer": item.get("retailer", ""),
            },
            images=[item["image_url"]] if item.get("image_url") else [],
        )

        # Price in cents — Stripe expects integer amounts in smallest currency unit
        currency = (item.get("currency") or "EUR").lower()
        unit_amount = int(round(item["price"] * 100))

        price = stripe.Price.create(
            product=product.id,
            unit_amount=unit_amount,
            currency=currency,
        )

        line_items.append({
            "price": price.id,
            "quantity": 1,
        })

    # Build success URL — redirect back to the session page after payment
    if not success_url:
        success_url = f"http://localhost:3000/session/{session_id}?payment=success"

    payment_link = stripe.PaymentLink.create(
        line_items=line_items,
        after_completion={
            "type": "redirect",
            "redirect": {"url": success_url},
        },
        shipping_address_collection={
            "allowed_countries": [
                "FR", "DE", "ES", "IT", "NL", "BE", "AT", "PT",
                "SE", "DK", "FI", "IE", "PL", "CZ", "GB", "US",
            ],
        },
        metadata={"session_id": session_id},
    )

    # Save payment link to session
    update_session(session_id, {
        "payment_link": payment_link.url,
        "payment_status": "pending",
        "status": "checkout",
    })

    logger.info("Created payment link for session=%s items=%d url=%s",
                session_id, len(items), payment_link.url)

    return payment_link.url
