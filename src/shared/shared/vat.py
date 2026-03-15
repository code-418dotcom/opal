"""VAT calculation and VIES validation for EU digital services."""
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

LOG = logging.getLogger(__name__)

# Aardvark Hosting — seller details
SELLER_COUNTRY = "NL"
SELLER_VAT_RATE = 21.0  # Dutch BTW rate

EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}


@dataclass
class VATResult:
    """Result of VAT calculation for a transaction."""
    net_cents: int          # Price excluding VAT
    vat_rate: float         # VAT percentage (0, 21, etc.)
    vat_cents: int          # VAT amount in cents
    total_cents: int        # net + vat
    reverse_charged: bool   # True if buyer self-assesses
    exempt_reason: str      # Human-readable reason for 0% VAT, or ""


def calculate_vat(
    price_cents: int,
    buyer_country: Optional[str],
    buyer_vat_number: Optional[str],
) -> VATResult:
    """Calculate VAT for a digital service sale.

    Prices in the system are stored EXCLUDING VAT (net).
    VAT is added on top based on buyer's country and VAT status.

    Rules:
    - NL buyer → 21% BTW
    - EU buyer with valid VAT number (not NL) → 0% reverse-charge
    - EU buyer without VAT number → 21% NL rate (below €10k OSS threshold)
    - Non-EU buyer → 0% (outside EU VAT scope)
    """
    net_cents = price_cents
    country = (buyer_country or "").upper().strip()
    vat_num = (buyer_vat_number or "").strip()

    # Non-EU: no VAT
    if not country or country not in EU_COUNTRIES:
        return VATResult(
            net_cents=net_cents,
            vat_rate=0,
            vat_cents=0,
            total_cents=net_cents,
            reverse_charged=False,
            exempt_reason="Outside EU — VAT not applicable",
        )

    # EU buyer with VAT number, not same country as seller → reverse-charge
    if vat_num and country != SELLER_COUNTRY:
        return VATResult(
            net_cents=net_cents,
            vat_rate=0,
            vat_cents=0,
            total_cents=net_cents,
            reverse_charged=True,
            exempt_reason="VAT reverse-charged per Article 196 EU VAT Directive",
        )

    # NL or EU without VAT number → charge 21%
    vat_cents = round(net_cents * SELLER_VAT_RATE / 100)
    return VATResult(
        net_cents=net_cents,
        vat_rate=SELLER_VAT_RATE,
        vat_cents=vat_cents,
        total_cents=net_cents + vat_cents,
        reverse_charged=False,
        exempt_reason="",
    )


# ── VIES VAT Number Validation ─────────────────────────────────────

# Basic format: 2-letter country prefix + alphanumeric
_VAT_PATTERN = re.compile(r"^[A-Z]{2}[0-9A-Za-z+*.]{2,13}$")

VIES_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number"


def validate_vat_number(vat_number: str) -> dict:
    """Validate an EU VAT number via the VIES API.

    Returns {"valid": bool, "name": str|None, "address": str|None, "error": str|None}.
    """
    vat = vat_number.replace(" ", "").replace(".", "").replace("-", "").upper()

    if not _VAT_PATTERN.match(vat):
        return {"valid": False, "name": None, "address": None, "error": "Invalid format"}

    country_code = vat[:2]
    number = vat[2:]

    if country_code not in EU_COUNTRIES:
        return {"valid": False, "name": None, "address": None, "error": f"Country '{country_code}' is not an EU member state"}

    try:
        resp = httpx.post(
            VIES_URL,
            json={"countryCode": country_code, "vatNumber": number},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "valid": data.get("valid", False),
            "name": data.get("name"),
            "address": data.get("address"),
            "error": None,
        }
    except Exception as e:
        LOG.warning("VIES validation failed for %s: %s", vat[:5] + "...", e)
        return {"valid": False, "name": None, "address": None, "error": f"VIES service unavailable: {e}"}
