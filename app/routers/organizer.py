
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Event, Booking
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/organizer",
    tags=["Organizer"]
)


class EventUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    event_date: Optional[datetime] = None
    ticket_price: Optional[float] = Field(None, ge=0)
    banner_image: Optional[str] = Field(None, max_length=500)


def require_organizer(user: User):
    if user.role not in ["ORGANIZER", "ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Only organizers and admins can manage events"
        )


def get_managed_event(db: Session, event_id: int, user: User):
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found"
        )

    if user.role != "ADMIN" and event.organizer_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You can manage only your own events"
        )

    return event


@router.get("/profile")
def organizer_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    require_organizer(user)

    query = db.query(Event)

    if user.role != "ADMIN":
        query = query.filter(Event.organizer_id == user.id)

    events = query.all()

    return {
        "organizer_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "total_events": len(events),
        "events": [
            {
                "id": event.id,
                "title": event.title,
                "category": event.category,
                "location": event.location,
                "event_date": event.event_date,
                "ticket_price": event.ticket_price,
                "total_tickets": event.total_tickets,
                "available_tickets": event.available_tickets
            }
            for event in events
        ]
    }


@router.get("/events")
def list_managed_events(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    require_organizer(user)

    query = db.query(Event)

    if user.role != "ADMIN":
        query = query.filter(Event.organizer_id == user.id)

    return query.order_by(Event.id.desc()).all()


@router.put("/events/{event_id}")
def update_managed_event(
    event_id: int,
    data: EventUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    require_organizer(user)

    event = get_managed_event(db, event_id, user)
    updates = data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update"
        )

    for field, value in updates.items():
        setattr(event, field, value)

    try:
        db.commit()
        db.refresh(event)
        return {
            "message": "Event updated successfully",
            "event": {
                "id": event.id,
                "title": event.title,
                "category": event.category,
                "location": event.location,
                "event_date": event.event_date,
                "ticket_price": event.ticket_price
            }
        }
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to update event"
        )


@router.delete("/events/{event_id}")
def delete_managed_event(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    require_organizer(user)

    event = get_managed_event(db, event_id, user)

    existing_booking = db.query(Booking.id).filter(
        Booking.event_id == event_id
    ).first()

    if existing_booking:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete an event with booking history"
        )

    try:
        db.delete(event)
        db.commit()
        return {"message": "Event deleted successfully"}
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to delete event"
        )
