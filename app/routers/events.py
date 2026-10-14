
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Event, Booking, User
from app.schemas import EventCreate, EventOut
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/", response_model=EventOut)
def create_event(data: EventCreate, db: Session = Depends(get_db)):
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
        query = query.filter(Event.category.ilike(f"%{category}%"))
    if search:
        query = query.filter(Event.title.ilike(f"%{search}%"))
    if location:
        query = query.filter(Event.location.ilike(f"%{location}%"))
    if min_price is not None:
        query = query.filter(Event.ticket_price >= min_price)
    if max_price is not None:
        query = query.filter(Event.ticket_price <= max_price)
    if event_date_from:
        query = query.filter(Event.event_date >= event_date_from)
    if event_date_to:
        query = query.filter(Event.event_date <= event_date_to)

    total = query.count()
    events = (
        query.order_by(Event.event_date.asc())
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


@router.get("/sort")
def sort_events(
    sort_by: str = Query(
        default="event_date",
        pattern="^(event_date|ticket_price|title)$"
    ),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    columns = {
        "event_date": Event.event_date,
        "ticket_price": Event.ticket_price,
        "title": Event.title
    }
    column = columns[sort_by]
    query = db.query(Event)
    query = query.order_by(
        column.desc() if order == "desc" else column.asc()
    )
    return query.all()


@router.get("/recommendations/me", response_model=list[EventOut])
def recommend_events(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    categories = (
        db.query(Event.category)
        .join(Booking, Booking.event_id == Event.id)
        .filter(
            Booking.user_id == user.id,
            Booking.booking_status == "CONFIRMED"
        )
        .distinct()
        .all()
    )
    preferred_categories = [row[0] for row in categories]

    booked_ids = (
        db.query(Booking.event_id)
        .filter(
            Booking.user_id == user.id,
            Booking.booking_status == "CONFIRMED"
        )
        .subquery()
    )

    query = db.query(Event).filter(
        Event.event_date >= datetime.utcnow(),
        Event.available_tickets > 0,
        ~Event.id.in_(booked_ids)
    )

    if preferred_categories:
        matching = (
            query.filter(Event.category.in_(preferred_categories))
            .order_by(Event.event_date.asc())
            .limit(10)
            .all()
        )
        if matching:
            return matching

    return query.order_by(Event.event_date.asc()).limit(10).all()


@router.get("/trending", response_model=list[EventOut])
def trending_events(db: Session = Depends(get_db)):
    booking_counts = (
        db.query(
            Booking.event_id.label("event_id"),
            func.sum(Booking.ticket_quantity).label("tickets_sold")
        )
        .filter(Booking.booking_status == "CONFIRMED")
        .group_by(Booking.event_id)
        .subquery()
    )

    return (
        db.query(Event)
        .outerjoin(booking_counts, Event.id == booking_counts.c.event_id)
        .filter(
            Event.event_date >= datetime.utcnow(),
            Event.available_tickets > 0
        )
        .order_by(
            booking_counts.c.tickets_sold.desc().nullslast(),
            Event.event_date.asc()
        )
        .limit(10)
        .all()
    )


# Keep static routes BEFORE /{event_id}.

@router.get("/upcoming")
def get_upcoming_events(db: Session = Depends(get_db)):
    events = (
        db.query(Event)
        .filter(Event.event_date >= datetime.utcnow())
        .order_by(Event.event_date.asc())
        .all()
    )

    return {
        "count": len(events),
        "events": [
            {
                "id": event.id,
                "title": event.title,
                "category": event.category,
                "location": event.location,
                "event_date": event.event_date,
                "ticket_price": event.ticket_price,
                "available_tickets": event.available_tickets
            }
            for event in events
        ]
    }


@router.get("/availability/summary")
def event_availability_summary(db: Session = Depends(get_db)):
    events = db.query(Event).all()
    return {
        "total_events": len(events),
        "total_tickets": sum(e.total_tickets or 0 for e in events),
        "available_tickets": sum(e.available_tickets or 0 for e in events),
        "sold_tickets": sum(
            (e.total_tickets or 0) - (e.available_tickets or 0)
            for e in events
        )
    }


@router.get("/categories/summary")
def event_category_summary(db: Session = Depends(get_db)):
    results = (
        db.query(
            Event.category,
            func.count(Event.id).label("event_count")
        )
        .group_by(Event.category)
        .all()
    )
    return {
        "categories": [
            {"category": category, "event_count": count}
            for category, count in results
        ]
    }


@router.get("/filter/date-range")
def filter_events_by_date(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Dates must use YYYY-MM-DD format"
        )

    if start > end:
        raise HTTPException(
            status_code=400,
            detail="start_date must not be after end_date"
        )

    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    events = (
        db.query(Event)
        .filter(Event.event_date >= start, Event.event_date <= end)
        .order_by(Event.event_date.asc())
        .all()
    )
    return {"count": len(events), "events": jsonable_encoder(events)}


@router.get("/{event_id}/availability")
def check_event_availability(
    event_id: int,
    db: Session = Depends(get_db)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "event_id": event.id,
        "event_title": event.title,
        "total_tickets": event.total_tickets,
        "available_tickets": event.available_tickets,
        "sold_tickets": event.total_tickets - event.available_tickets
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

    if category:
        query = query.filter(Event.category.ilike(f"%{category}%"))
    if search:
        query = query.filter(
            Event.title.ilike(f"%{search}%") |
            Event.description.ilike(f"%{search}%")
        )
    if location:
        query = query.filter(Event.location.ilike(f"%{location}%"))
    if min_price is not None:
        query = query.filter(Event.ticket_price >= min_price)
    if max_price is not None:
        query = query.filter(Event.ticket_price <= max_price)

    columns = {
        "date": Event.event_date,
        "price": Event.ticket_price,
        "title": Event.title
    }
    if sort_by not in columns:
        raise HTTPException(400, "sort_by must be date, price, or title")
    if order not in ("asc", "desc"):
        raise HTTPException(400, "order must be asc or desc")

    column = columns[sort_by]
    query = query.order_by(
        column.desc() if order == "desc" else column.asc()
    )
    return query.offset(skip).limit(limit).all()


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
