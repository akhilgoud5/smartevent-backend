
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Wishlist, Event, User
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/{event_id}")
def add_to_wishlist(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    existing = db.query(Wishlist).filter(
        Wishlist.user_id == user.id,
        Wishlist.event_id == event_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Event already exists in wishlist"
        )

    item = Wishlist(user_id=user.id, event_id=event_id)

    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not add event to wishlist"
        )

    return {
        "message": "Event added to wishlist",
        "wishlist_id": item.id,
        "event_id": item.event_id
    }


@router.get("/")
def get_wishlist(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    items = (
        db.query(Wishlist)
        .filter(Wishlist.user_id == user.id)
        .order_by(Wishlist.created_at.desc())
        .all()
    )

    return [
        {
            "wishlist_id": item.id,
            "event_id": item.event.id,
            "title": item.event.title,
            "category": item.event.category,
            "location": item.event.location,
            "event_date": item.event.event_date,
            "ticket_price": item.event.ticket_price,
            "available_tickets": item.event.available_tickets,
            "created_at": item.created_at
        }
        for item in items
    ]


@router.delete("/{event_id}")
def remove_from_wishlist(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    item = db.query(Wishlist).filter(
        Wishlist.user_id == user.id,
        Wishlist.event_id == event_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Event not found in wishlist"
        )

    db.delete(item)
    db.commit()

    return {"message": "Event removed from wishlist"}
