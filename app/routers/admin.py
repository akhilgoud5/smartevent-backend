from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Event, Booking
from app.dependencies import require_role

router = APIRouter()


# =========================
# GET ALL USERS
# =========================

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("ADMIN"))
):
    users = db.query(User).order_by(
        User.created_at.desc()
    ).all()

    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at
        }
        for user in users
    ]


# =========================
# GET ALL EVENTS
# =========================

@router.get("/events")
def get_all_events(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("ADMIN"))
):
    return db.query(Event).order_by(
        Event.created_at.desc()
    ).all()


# =========================
# GET ALL BOOKINGS
# =========================

@router.get("/bookings")
def get_all_bookings(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("ADMIN"))
):
    return db.query(Booking).order_by(
        Booking.created_at.desc()
    ).all()


# =========================
# ADMIN ANALYTICS
# =========================

@router.get("/analytics")
def admin_analytics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("ADMIN"))
):

    # -------------------------
    # BASIC TOTALS
    # -------------------------

    total_users = db.query(
        func.count(User.id)
    ).scalar()

    total_events = db.query(
        func.count(Event.id)
    ).scalar()

    total_bookings = db.query(
        func.count(Booking.id)
    ).filter(
        Booking.booking_status == "CONFIRMED"
    ).scalar()

    total_tickets_sold = db.query(
        func.coalesce(
            func.sum(Booking.ticket_quantity),
            0
        )
    ).filter(
        Booking.booking_status == "CONFIRMED"
    ).scalar()

    total_revenue = db.query(
        func.coalesce(
            func.sum(Booking.total_price),
            0
        )
    ).filter(
        Booking.booking_status == "CONFIRMED"
    ).scalar()


    # -------------------------
    # DAILY TICKET SALES
    # -------------------------

    daily_sales = db.query(
        func.date(Booking.created_at).label("sale_date"),
        func.sum(
            Booking.ticket_quantity
        ).label("tickets_sold"),
        func.sum(
            Booking.total_price
        ).label("revenue")
    ).filter(
        Booking.booking_status == "CONFIRMED"
    ).group_by(
        func.date(Booking.created_at)
    ).order_by(
        func.date(Booking.created_at)
    ).all()


    daily_sales_result = []

    for row in daily_sales:
        daily_sales_result.append({
            "date": str(row.sale_date),
            "tickets_sold": int(
                row.tickets_sold or 0
            ),
            "revenue": float(
                row.revenue or 0
            )
        })


    # -------------------------
    # MONTHLY BOOKING TRENDS
    # -------------------------

    monthly_bookings = db.query(
        func.strftime(
            "%Y-%m",
            Booking.created_at
        ).label("month"),
        func.count(
            Booking.id
        ).label("booking_count")
    ).filter(
        Booking.booking_status == "CONFIRMED"
    ).group_by(
        func.strftime(
            "%Y-%m",
            Booking.created_at
        )
    ).order_by(
        func.strftime(
            "%Y-%m",
            Booking.created_at
        )
    ).all()


    monthly_bookings_result = []

    for row in monthly_bookings:
        monthly_bookings_result.append({
            "month": str(row.month),
            "booking_count": int(
                row.booking_count or 0
            )
        })


    # -------------------------
    # MOST POPULAR EVENTS
    # -------------------------

    popular_events = db.query(
        Event.id,
        Event.title,
        func.coalesce(
            func.sum(
                Booking.ticket_quantity
            ),
            0
        ).label("tickets_sold")
    ).outerjoin(
        Booking,
        Booking.event_id == Event.id
    ).filter(
        (Booking.booking_status == "CONFIRMED")
        | (Booking.id.is_(None))
    ).group_by(
        Event.id
    ).order_by(
        func.coalesce(
            func.sum(
                Booking.ticket_quantity
            ),
            0
        ).desc()
    ).limit(10).all()


    popular_events_result = []

    for row in popular_events:
        popular_events_result.append({
            "event_id": row.id,
            "event_title": row.title,
            "tickets_sold": int(
                row.tickets_sold or 0
            )
        })


    # -------------------------
    # TOP REVENUE EVENTS
    # -------------------------

    revenue_events = db.query(
        Event.id,
        Event.title,
        func.coalesce(
            func.sum(
                Booking.total_price
            ),
            0
        ).label("revenue")
    ).outerjoin(
        Booking,
        Booking.event_id == Event.id
    ).filter(
        (Booking.booking_status == "CONFIRMED")
        | (Booking.id.is_(None))
    ).group_by(
        Event.id
    ).order_by(
        func.coalesce(
            func.sum(
                Booking.total_price
            ),
            0
        ).desc()
    ).limit(10).all()


    revenue_events_result = []

    for row in revenue_events:
        revenue_events_result.append({
            "event_id": row.id,
            "event_title": row.title,
            "revenue": float(
                row.revenue or 0
            )
        })


    # -------------------------
    # FINAL RESPONSE
    # -------------------------

    return {
        "total_users": total_users or 0,
        "total_events": total_events or 0,
        "total_bookings": total_bookings or 0,
        "total_tickets_sold": int(
            total_tickets_sold or 0
        ),
        "total_revenue": float(
            total_revenue or 0
        ),

        "daily_ticket_sales": daily_sales_result,

        "monthly_booking_trends": monthly_bookings_result,

        "most_popular_events": popular_events_result,

        "top_revenue_events": revenue_events_result
    }