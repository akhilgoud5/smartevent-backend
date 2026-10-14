
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Event, Booking, User
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Only administrators can view the dashboard.
    if getattr(user, "role", "USER") != "ADMIN":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail="Only admins can access analytics"
        )

    total_events = db.query(Event).count()

    total_bookings = db.query(Booking).count()

    confirmed_bookings = db.query(Booking).filter(
        Booking.booking_status == "CONFIRMED"
    ).count()

    total_tickets_sold = db.query(
        func.coalesce(
            func.sum(Booking.ticket_quantity), 0
        )
    ).filter(
        Booking.booking_status == "CONFIRMED"
    ).scalar()

    total_revenue = db.query(
        func.coalesce(
            func.sum(Booking.total_price), 0
        )
    ).filter(
        Booking.booking_status == "CONFIRMED"
    ).scalar()

    return {
        "total_events": total_events,
        "total_bookings": total_bookings,
        "confirmed_bookings": confirmed_bookings,
        "total_tickets_sold": total_tickets_sold,
        "total_revenue": float(total_revenue)
    }
