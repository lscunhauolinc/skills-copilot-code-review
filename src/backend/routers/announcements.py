"""Announcement management endpoints for the High School Management System API."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementPayload(BaseModel):
    """Payload used to create and update announcements."""

    title: str = Field(..., min_length=3, max_length=120)
    message: str = Field(..., min_length=3, max_length=800)
    expires_at: str
    starts_at: Optional[str] = None


class AnnouncementUpdatePayload(BaseModel):
    """Payload used to partially update announcements."""

    title: Optional[str] = Field(None, min_length=3, max_length=120)
    message: Optional[str] = Field(None, min_length=3, max_length=800)
    expires_at: Optional[str] = None
    starts_at: Optional[str] = None


def _require_logged_user(username: Optional[str]) -> Dict[str, Any]:
    """Validate if a user exists and can manage announcements."""
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = teachers_collection.find_one({"_id": username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")

    return user


def _parse_iso_datetime(value: str, field_name: str) -> datetime:
    """Parse ISO datetime values and normalize UTC timestamps."""
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {field_name} format") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _announcement_document_to_response(document: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Mongo document for API response."""
    response = dict(document)
    response["id"] = response.pop("_id")
    return response


@router.get("/active", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get active announcements for public display.

    Active announcements are those where the current time is before expires_at and,
    if starts_at exists, after starts_at.
    """
    now = datetime.now(timezone.utc)
    active_announcements: List[Dict[str, Any]] = []

    for document in announcements_collection.find({}).sort("expires_at", 1):
        starts_at_raw = document.get("starts_at")
        expires_at_raw = document.get("expires_at")

        if not expires_at_raw:
            continue

        starts_at = _parse_iso_datetime(starts_at_raw, "starts_at") if starts_at_raw else None
        expires_at = _parse_iso_datetime(expires_at_raw, "expires_at")

        if starts_at and now < starts_at:
            continue
        if now > expires_at:
            continue

        active_announcements.append(_announcement_document_to_response(document))

    return active_announcements


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def list_announcements(teacher_username: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """List all announcements for management UI. Requires login."""
    _require_logged_user(teacher_username)

    announcements: List[Dict[str, Any]] = []
    for document in announcements_collection.find({}).sort("expires_at", 1):
        announcements.append(_announcement_document_to_response(document))

    return announcements


@router.post("", response_model=Dict[str, Any])
def create_announcement(payload: AnnouncementPayload, teacher_username: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Create a new announcement. Requires login."""
    user = _require_logged_user(teacher_username)

    title = payload.title.strip()
    message = payload.message.strip()

    if len(title) < 3 or len(message) < 3:
        raise HTTPException(status_code=422, detail="title and message are required")

    starts_at = _parse_iso_datetime(payload.starts_at, "starts_at") if payload.starts_at else None
    expires_at = _parse_iso_datetime(payload.expires_at, "expires_at")

    if starts_at and starts_at >= expires_at:
        raise HTTPException(status_code=422, detail="starts_at must be earlier than expires_at")

    announcement_id = f"ann-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    document = {
        "_id": announcement_id,
        "title": title,
        "message": message,
        "starts_at": starts_at.isoformat().replace("+00:00", "Z") if starts_at else None,
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "created_by": user["_id"],
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    announcements_collection.insert_one(document)
    return _announcement_document_to_response(document)


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    payload: AnnouncementUpdatePayload,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Update an existing announcement. Requires login."""
    _require_logged_user(teacher_username)

    existing = announcements_collection.find_one({"_id": announcement_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")

    update_fields: Dict[str, Any] = {}

    if payload.title is not None:
        title = payload.title.strip()
        if len(title) < 3:
            raise HTTPException(status_code=422, detail="title is too short")
        update_fields["title"] = title
    if payload.message is not None:
        message = payload.message.strip()
        if len(message) < 3:
            raise HTTPException(status_code=422, detail="message is too short")
        update_fields["message"] = message

    starts_at_raw = payload.starts_at if payload.starts_at is not None else existing.get("starts_at")
    expires_at_raw = payload.expires_at if payload.expires_at is not None else existing.get("expires_at")

    if not expires_at_raw:
        raise HTTPException(status_code=422, detail="expires_at is required")

    starts_at = _parse_iso_datetime(starts_at_raw, "starts_at") if starts_at_raw else None
    expires_at = _parse_iso_datetime(expires_at_raw, "expires_at")

    if starts_at and starts_at >= expires_at:
        raise HTTPException(status_code=422, detail="starts_at must be earlier than expires_at")

    update_fields["starts_at"] = starts_at.isoformat().replace("+00:00", "Z") if starts_at else None
    update_fields["expires_at"] = expires_at.isoformat().replace("+00:00", "Z")
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    announcements_collection.update_one(
        {"_id": announcement_id},
        {"$set": update_fields}
    )

    updated = announcements_collection.find_one({"_id": announcement_id})
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update announcement")

    return _announcement_document_to_response(updated)


@router.delete("/{announcement_id}", response_model=Dict[str, str])
def delete_announcement(announcement_id: str, teacher_username: Optional[str] = Query(None)) -> Dict[str, str]:
    """Delete an announcement. Requires login."""
    _require_logged_user(teacher_username)

    result = announcements_collection.delete_one({"_id": announcement_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted successfully"}
