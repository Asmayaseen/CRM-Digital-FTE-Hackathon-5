"""
production/agent/formatters.py
Channel-aware response formatting — Constitution Principle IX.

THIS IS THE ONLY PLACE response formatting occurs.
All channel-specific length, greeting, and signature rules live here.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Channel limits (kept in sync with channel_configs table seed)
_MAX_LENGTHS: dict[str, int] = {
    "email": 2000,
    "whatsapp": 300,
    "web_form": 1000,
}

_WHATSAPP_SUFFIX = "📱 Reply for more help or type 'human' for live support."
_WEB_FORM_SUFFIX = "\n\n💡 Visit our Help Portal: https://help.cloudsyncpro.com"


def format_for_channel(
    response: str,
    channel: str,
    *,
    customer_name: str = "Customer",
    ticket_id: str | None = None,
) -> str:
    """
    Apply channel-specific formatting rules to an agent response.

    Args:
        response:      Raw agent response text.
        channel:       One of "email", "whatsapp", "web_form".
        customer_name: Customer's first name or full name for greeting.
        ticket_id:     Ticket reference appended to email signature.

    Returns:
        Formatted response ready for delivery.

    Raises:
        ValueError: If channel is not a recognised value.
    """
    if channel not in _MAX_LENGTHS:
        logger.warning("Unknown channel '%s', falling back to web_form formatting", channel)
        channel = "web_form"

    formatted = _apply_channel_rules(response.strip(), channel, customer_name, ticket_id)

    max_len = _MAX_LENGTHS[channel]
    if len(formatted) > max_len:
        if channel == "whatsapp":
            # Truncate early enough to still append the suffix
            suffix_len = len(_WHATSAPP_SUFFIX) + 2  # newline + space
            truncated = formatted[: max_len - suffix_len - 3] + "..."
            formatted = truncated + "\n" + _WHATSAPP_SUFFIX
        else:
            formatted = formatted[: max_len - 3] + "..."

    return formatted


def _apply_channel_rules(
    response: str,
    channel: str,
    customer_name: str,
    ticket_id: str | None,
) -> str:
    if channel == "email":
        return _format_email(response, customer_name, ticket_id)
    if channel == "whatsapp":
        return _format_whatsapp(response)
    return _format_web_form(response)


def _format_email(response: str, customer_name: str, ticket_id: str | None) -> str:
    first_name = customer_name.split()[0] if customer_name else "Customer"
    parts = [f"Hi {first_name},", "", response, ""]
    signature_lines = ["Best regards,", "CloudSync Pro Support Team"]
    if ticket_id:
        signature_lines.append(f"Reference: {ticket_id}")
    parts.extend(signature_lines)
    return "\n".join(parts)


def _format_whatsapp(response: str) -> str:
    # WhatsApp: conversational, no greeting/signature; append CTA
    return response + "\n" + _WHATSAPP_SUFFIX


def _format_web_form(response: str) -> str:
    return response + _WEB_FORM_SUFFIX
