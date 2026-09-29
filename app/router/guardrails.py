"""
PII Guardrails — detect and mask personal identifiable information in prompts
before sending to LLM providers.

Detects:
- Email addresses
- Phone numbers (international formats)
- IBANs (international bank account numbers)
- Credit card numbers (Luhn-validated)
- IP addresses (IPv4)
- Configurable custom name patterns

Opt-in per virtual key or global via settings.
Logs the TYPE of masked data (never the actual value).
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("llm_router.guardrails")

# ── Detection patterns ──────────────────────────────────────────────────────

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+?\d{1,3}[\s\-.]?)?"   # Optional country code
    r"(?:\(?\d{2,4}\)?[\s\-.]?)" # Area code
    r"\d{3,4}[\s\-.]?"           # First group
    r"\d{2,4}"                    # Last group
    r"(?!\d)"
)

_IBAN_RE = re.compile(
    r"\b[A-Z]{2}\d{2}[\s]?[\dA-Z]{4}[\s]?[\dA-Z]{4}[\s]?[\dA-Z]{4}[\s]?[\dA-Z]{0,16}\b"
)

_CREDIT_CARD_RE = re.compile(
    r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"
)

_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)

_SSN_RE = re.compile(
    r"\b\d{3}[\-\s]?\d{2}[\-\s]?\d{4}\b"
)


# ── Luhn check for credit cards ─────────────────────────────────────────────

def _luhn_check(number: str) -> bool:
    """Validate a number string using the Luhn algorithm."""
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse = digits[::-1]
    for i, d in enumerate(reverse):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


# ── Masking result ──────────────────────────────────────────────────────────

@dataclass
class PIIMaskResult:
    """Result of PII detection and masking."""
    original_text: str
    masked_text: str
    detections: List[Dict[str, str]] = field(default_factory=list)
    # Each detection: {"type": "email"|"phone"|..., "position": "chars 5-20"}
    pii_found: bool = False

    def summary(self) -> dict:
        """Return a loggable summary (types only, never values)."""
        return {
            "pii_found": self.pii_found,
            "detection_count": len(self.detections),
            "types_detected": list(set(d["type"] for d in self.detections)),
        }


# ── Guardrail engine ────────────────────────────────────────────────────────

class PIIGuardrail:
    """Detect and mask PII in text content."""

    def __init__(
        self,
        mask_emails: bool = True,
        mask_phones: bool = True,
        mask_ibans: bool = True,
        mask_credit_cards: bool = True,
        mask_ips: bool = True,
        mask_ssns: bool = True,
        custom_patterns: Optional[Dict[str, str]] = None,
    ):
        self.mask_emails = mask_emails
        self.mask_phones = mask_phones
        self.mask_ibans = mask_ibans
        self.mask_credit_cards = mask_credit_cards
        self.mask_ips = mask_ips
        self.mask_ssns = mask_ssns
        # Custom regex patterns: name → regex string
        self._custom_patterns: Dict[str, re.Pattern] = {}
        if custom_patterns:
            for name, pattern in custom_patterns.items():
                try:
                    self._custom_patterns[name] = re.compile(pattern)
                except re.error:
                    logger.warning(f"Invalid custom PII pattern '{name}': {pattern}")

        self.total_scanned: int = 0
        self.total_detections: int = 0

    def scan_and_mask(self, text: str) -> PIIMaskResult:
        """Scan text for PII, mask all findings, and return result."""
        self.total_scanned += 1
        detections: List[Dict[str, str]] = []
        masked = text

        # Email
        if self.mask_emails:
            for match in _EMAIL_RE.finditer(masked):
                detections.append({"type": "email", "position": f"chars {match.start()}-{match.end()}"})
            masked = _EMAIL_RE.sub("[EMAIL_REDACTED]", masked)

        # Phone
        if self.mask_phones:
            for match in _PHONE_RE.finditer(masked):
                # Quick sanity: must have at least 7 digits
                digits = re.sub(r"\D", "", match.group())
                if len(digits) >= 7:
                    detections.append({"type": "phone", "position": f"chars {match.start()}-{match.end()}"})
            # Replace only phone-like strings with enough digits
            def _phone_replacer(m):
                digits = re.sub(r"\D", "", m.group())
                if len(digits) >= 7:
                    return "[PHONE_REDACTED]"
                return m.group()
            masked = _PHONE_RE.sub(_phone_replacer, masked)

        # IBAN
        if self.mask_ibans:
            for match in _IBAN_RE.finditer(masked):
                detections.append({"type": "iban", "position": f"chars {match.start()}-{match.end()}"})
            masked = _IBAN_RE.sub("[IBAN_REDACTED]", masked)

        # Credit card (with Luhn validation)
        if self.mask_credit_cards:
            def _cc_replacer(m):
                raw = re.sub(r"[\s\-]", "", m.group())
                if _luhn_check(raw):
                    detections.append({"type": "credit_card", "position": f"chars {m.start()}-{m.end()}"})
                    return "[CREDIT_CARD_REDACTED]"
                return m.group()
            masked = _CREDIT_CARD_RE.sub(_cc_replacer, masked)

        # IPv4
        if self.mask_ips:
            for match in _IPV4_RE.finditer(masked):
                detections.append({"type": "ipv4", "position": f"chars {match.start()}-{match.end()}"})
            masked = _IPV4_RE.sub("[IP_REDACTED]", masked)

        # SSN
        if self.mask_ssns:
            for match in _SSN_RE.finditer(masked):
                digits = re.sub(r"\D", "", match.group())
                if len(digits) == 9:
                    detections.append({"type": "ssn", "position": f"chars {match.start()}-{match.end()}"})
            def _ssn_replacer(m):
                digits = re.sub(r"\D", "", m.group())
                if len(digits) == 9:
                    return "[SSN_REDACTED]"
                return m.group()
            masked = _SSN_RE.sub(_ssn_replacer, masked)

        # Custom patterns
        for name, pattern in self._custom_patterns.items():
            for match in pattern.finditer(masked):
                detections.append({"type": f"custom:{name}", "position": f"chars {match.start()}-{match.end()}"})
            masked = pattern.sub(f"[{name.upper()}_REDACTED]", masked)

        self.total_detections += len(detections)

        result = PIIMaskResult(
            original_text=text,
            masked_text=masked,
            detections=detections,
            pii_found=len(detections) > 0,
        )

        if result.pii_found:
            logger.info(f"PII detected and masked: {result.summary()}")

        return result

    def mask_messages(self, messages: list) -> Tuple[list, List[Dict[str, str]]]:
        """Mask PII in a list of chat messages (dicts with 'content' key).

        Returns (masked_messages, all_detections).
        """
        all_detections: List[Dict[str, str]] = []
        masked_msgs = []
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                if content:
                    result = self.scan_and_mask(content)
                    new_msg = dict(msg)
                    new_msg["content"] = result.masked_text
                    all_detections.extend(result.detections)
                    masked_msgs.append(new_msg)
                else:
                    masked_msgs.append(msg)
            else:
                # Pydantic model with .content attribute
                content = getattr(msg, "content", "")
                if content:
                    result = self.scan_and_mask(content)
                    # Create a copy with masked content
                    msg_copy = msg.model_copy() if hasattr(msg, "model_copy") else msg
                    if hasattr(msg_copy, "content"):
                        object.__setattr__(msg_copy, "content", result.masked_text) if hasattr(msg_copy, "__dict__") else None
                        try:
                            msg_copy.content = result.masked_text
                        except Exception:
                            pass
                    all_detections.extend(result.detections)
                    masked_msgs.append(msg_copy)
                else:
                    masked_msgs.append(msg)
        return masked_msgs, all_detections

    def get_stats(self) -> dict:
        return {
            "total_scanned": self.total_scanned,
            "total_detections": self.total_detections,
        }


# Global instance
pii_guardrail = PIIGuardrail()
