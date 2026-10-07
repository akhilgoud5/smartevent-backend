from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Event
from app.schemas import EventCreate, EventOut

router = APIRouter()

@router.post("/", response_model=EventOut)
def create_event(data: EventCreate, db: Session = Depends(get_db)):
    event = Event(**data.model_dump(), available_tickets=data.total_tickets)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.get("/", response_model=list[EventOut])
def get_events(
    category: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Event)
    if category:
        query = query.filter(Event.category.ilike(category))
    if search:
        query = query.filter(Event.title.ilike(f"%{search}%"))
    return query.order_by(Event.event_date).all()

@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    return event
