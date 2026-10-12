
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from app.database import get_db
from app.models import Event
from datetime import datetime

from app.schemas import EventCreate, EventOut

router = APIRouter()


@router.post("/", response_model=EventOut)
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db)
):
    event_data = data.model_dump()

    event = Event(
        **event_data,
        available_tickets=data.total_tickets
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event

@router.get("/search")
def search_events(
    category: str | None = None,
    search: str | None = None,
    location: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    event_date_from: datetime | None = None,
    event_date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Event)

    if category:
        query = query.filter(
            Event.category.ilike(f"%{category}%")
        )

    if search:
        query = query.filter(
            Event.title.ilike(f"%{search}%")
        )

    if location:
        query = query.filter(
            Event.location.ilike(f"%{location}%")
        )

    if min_price is not None:
        query = query.filter(
            Event.ticket_price >= min_price
        )

    if max_price is not None:
        query = query.filter(
            Event.ticket_price <= max_price
        )

    if event_date_from:
        query = query.filter(
            Event.event_date >= event_date_from
        )

    if event_date_to:
        query = query.filter(
            Event.event_date <= event_date_to
        )

    total = query.count()

    events = (
        query.order_by(Event.event_date)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "events": jsonable_encoder(events)
    }


@router.get("/", response_model=list[EventOut])
def get_events(
    category: str | None = None,
    search: str | None = None,
    location: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort_by: str = Query(default="date"),
    order: str = Query(default="asc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Event)

    # Filter by category
    if category:
        query = query.filter(
            Event.category.ilike(f"%{category}%")
        )

    # Search title and description
    if search:
        query = query.filter(
            Event.title.ilike(f"%{search}%")
            | Event.description.ilike(f"%{search}%")
        )

    # Filter by location
    if location:
        query = query.filter(
            Event.location.ilike(f"%{location}%")
        )

    # Filter by ticket price
    if min_price is not None:
        query = query.filter(
            Event.ticket_price >= min_price
        )

    if max_price is not None:
        query = query.filter(
            Event.ticket_price <= max_price
        )

    # Validate sorting
    sort_columns = {
        "date": Event.event_date,
        "price": Event.ticket_price,
        "title": Event.title
    }

    if sort_by not in sort_columns:
        raise HTTPException(
            status_code=400,
            detail="sort_by must be date, price, or title"
        )

    if order not in ("asc", "desc"):
        raise HTTPException(
            status_code=400,
            detail="order must be asc or desc"
        )

    sort_column = sort_columns[sort_by]

    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Pagination
    events = query.offset(skip).limit(limit).all()

    return events


@router.get("/sort")
def sort_events(
    sort_by: str = Query(default="event_date", pattern="^(event_date|ticket_price|title)$"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    sort_column = {
        "event_date": Event.event_date,
        "ticket_price": Event.ticket_price,
        "title": Event.title
    }[sort_by]

    if order == "desc":
        query = db.query(Event).order_by(sort_column.desc())
    else:
        query = db.query(Event).order_by(sort_column.asc())

    return query.all()


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found"
        )

    return event
