"""GDPR / AVG data subject rights: export, deletion, privacy info."""
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from shared.db_sqlalchemy import export_user_data, delete_user_data
from shared.storage import delete_blob
from web_api.auth import get_current_user

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/privacy", tags=["privacy"])
public_router = APIRouter(prefix="/v1/privacy", tags=["privacy"])


@router.get("/export")
def export_my_data(user: dict = Depends(get_current_user)):
    """Download all personal data (GDPR Art. 15 / AVG inzagerecht)."""
    data = export_user_data(user["user_id"])
    if not data:
        return {"user": {"user_id": user["user_id"]}, "note": "No data found"}
    return data


class DeleteConfirmIn(BaseModel):
    confirm: bool


@router.post("/delete-account")
def delete_my_account(body: DeleteConfirmIn, user: dict = Depends(get_current_user)):
    """Delete account and all personal data (GDPR Art. 17 / AVG recht op vergetelheid).
    This action is irreversible."""
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to delete your account")

    if user["user_id"] in ("apikey", "anonymous"):
        raise HTTPException(status_code=400, detail="Cannot delete system accounts")

    LOG.info("GDPR deletion requested by user %s", user["user_id"])

    result = delete_user_data(user["user_id"])
    if not result.get("deleted"):
        raise HTTPException(status_code=404, detail="User not found")

    # Clean up blob storage
    blob_paths = result.pop("blob_paths", [])
    blobs_deleted = 0
    for container, path in blob_paths:
        try:
            delete_blob(container, path)
            blobs_deleted += 1
        except Exception as e:
            LOG.warning("Failed to delete blob %s/%s: %s", container, path, e)

    result["blobs_deleted"] = blobs_deleted
    LOG.info("GDPR deletion completed for user %s: %s", user["user_id"], result)
    return result


@public_router.get("/info")
def privacy_info():
    """Public endpoint: what data we collect and how we process it."""
    return {
        "data_controller": "Opal Optics",
        "data_collected": [
            {"field": "email", "purpose": "Account identification and communication", "retention": "Until account deletion"},
            {"field": "display_name", "purpose": "Personalization", "retention": "Until account deletion"},
            {"field": "product_images", "purpose": "Image processing service delivery", "retention": "90 days after processing"},
            {"field": "payment_history", "purpose": "Financial records and VAT compliance", "retention": "7 years (Dutch fiscal requirement)"},
            {"field": "token_transactions", "purpose": "Service usage tracking", "retention": "Until account deletion"},
        ],
        "third_parties": [
            {"name": "Microsoft Entra", "purpose": "Authentication", "location": "EU/US", "dpa": True},
            {"name": "Mollie", "purpose": "Payment processing", "location": "Netherlands", "dpa": True},
            {"name": "FAL.ai", "purpose": "AI image generation (text prompts only, no personal data)", "location": "US"},
            {"name": "Shopify", "purpose": "E-commerce integration (only when connected by user)", "location": "US/Canada", "dpa": True},
        ],
        "your_rights": {
            "access": "GET /v1/privacy/export — download all your data",
            "erasure": "POST /v1/privacy/delete-account — delete your account and all data",
            "portability": "GET /v1/privacy/export — machine-readable JSON export",
            "complaint": "You can file a complaint with the Autoriteit Persoonsgegevens (AP) at autoriteitpersoonsgegevens.nl",
        },
        "contact": "privacy@opaloptics.com",
        "legal_basis": "Contract (service delivery) and Legitimate Interest (product improvement)",
    }
