
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Event, EventUpdate, User
from app.dependencies import get_current_user

router = APIRouter()


class EventUpdateCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@router.post("/{event_id}")
def create_event_update(
    event_id: int,
    data: EventUpdateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Only ADMIN or the organizer who owns this event may post updates.
    # This assumes your Event model has organizer_id and User has role.
    role = getattr(user, "role", "USER")
    organizer_id = getattr(event, "organizer_id", None)

    if role != "ADMIN" and not (
        role == "ORGANIZER" and organizer_id == user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Only the event organizer or admin can post updates"
        )

    update_item = EventUpdate(
        event_id=event_id,
        message=data.message.strip()
    )

    if not update_item.message:
        raise HTTPException(
            status_code=422,
            detail="Announcement message cannot be empty"
        )

    try:
        db.add(update_item)
        db.commit()
        db.refresh(update_item)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save event update"
        )

    return {
        "message": "Event update published",
        "update_id": update_item.id,
        "event_id": update_item.event_id,
        "announcement": update_item.message,
        "created_at": update_item.created_at
    }


@router.get("/{event_id}")
def get_event_updates(
    event_id: int,
    db: Session = Depends(get_db)
):
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    updates = (
        db.query(EventUpdate)
        .filter(EventUpdate.event_id == event_id)
        .order_by(EventUpdate.created_at.desc())
        .all()
    )

    return updates
