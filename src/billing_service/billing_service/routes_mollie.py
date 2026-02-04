from fastapi import APIRouter, Request, HTTPException
from shared.config import settings

router = APIRouter(prefix="/v1/mollie", tags=["mollie"])


@router.post("/webhook")
async def mollie_webhook(request: Request):
    # Mollie webhooks are typically POSTed with minimal payload, often just an id.
    # Robust approach: verify secret/signature (depending on webhook type), then fetch object from Mollie API.
    # For now, we sanity-check reception and return 200 quickly.

    if not settings.MOLLIE_WEBHOOK_SECRET:
        # allow dev testing without configuring secrets
        payload = await request.body()
        return {"ok": True, "note": "secret not configured", "bytes": len(payload)}

    # If you configure MOLLIE_WEBHOOK_SECRET, enforce it here (implementation comes later).
    # This placeholder intentionally refuses to avoid false security claims.
    raise HTTPException(status_code=501, detail="Webhook verification not implemented yet")
