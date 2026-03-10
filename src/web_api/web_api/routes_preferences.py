"""User preferences API — UI settings like help tooltips, tips bar, etc."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from shared.db import SessionLocal
from shared.models import UserPreference
from web_api.auth import get_current_user

router = APIRouter(prefix="/v1/account", tags=["preferences"])

DEFAULT_PREFERENCES = {
    "show_help_tooltips": True,
    "show_tips_bar": True,
    "dismissed_tips": [],
}


class PreferencesUpdate(BaseModel):
    show_help_tooltips: bool | None = None
    show_tips_bar: bool | None = None
    dismissed_tips: list[str] | None = None


@router.get("/preferences")
def get_preferences(user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    if user_id == "apikey":
        return {"preferences": DEFAULT_PREFERENCES}

    with SessionLocal() as s:
        pref = s.get(UserPreference, user_id)
        if not pref:
            return {"preferences": DEFAULT_PREFERENCES}
        merged = {**DEFAULT_PREFERENCES, **(pref.preferences or {})}
        return {"preferences": merged}


@router.put("/preferences")
def update_preferences(
    body: PreferencesUpdate,
    user: dict = Depends(get_current_user),
):
    user_id = user["user_id"]
    if user_id == "apikey":
        return {"preferences": DEFAULT_PREFERENCES}

    with SessionLocal() as s:
        pref = s.get(UserPreference, user_id)
        if not pref:
            pref = UserPreference(user_id=user_id, preferences={})
            s.add(pref)

        current = {**DEFAULT_PREFERENCES, **(pref.preferences or {})}
        updates = body.model_dump(exclude_none=True)
        current.update(updates)
        pref.preferences = current
        s.commit()
        s.refresh(pref)
        return {"preferences": pref.preferences}
