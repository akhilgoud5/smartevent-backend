
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.database import get_db
from app.models import Booking, Event, Ticket, Notification, User
from app.schemas import BookingCreate, BookingOut
from app.dependencies import get_current_user
from app.websocket_manager import manager

router = APIRouter()


@router.post("/", response_model=BookingOut)
async def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if data.ticket_quantity <= 0:
        raise HTTPException(400, "Ticket quantity must be greater than zero")

    try:
        # Atomically reserve tickets so concurrent requests
        # cannot sell more tickets than are available.
        result = db.execute(
            update(Event)
            .where(
                Event.id == data.event_id,
                Event.available_tickets >= data.ticket_quantity
            )
            .values(
                available_tickets=(
                    Event.available_tickets - data.ticket_quantity
                )
            )
        )

        if result.rowcount == 0:
            db.rollback()

            event = db.query(Event).filter(
                Event.id == data.event_id
            ).first()

            if not event:
                raise HTTPException(404, "Event not found")

            raise HTTPException(400, "Not enough tickets available")

        event = db.query(Event).filter(
            Event.id == data.event_id
        ).first()

        total = event.ticket_price * data.ticket_quantity

        booking = Booking(
            user_id=user.id,
            event_id=event.id,
            ticket_quantity=data.ticket_quantity,
            total_price=total,
            booking_status="CONFIRMED"
        )

        db.add(booking)
        db.flush()

        ticket = Ticket(
            booking_id=booking.id,
            ticket_code=f"TKT-{uuid.uuid4().hex[:12].upper()}",
            qr_code_url=f"/tickets/{booking.id}/qr"
        )

        notification = Notification(
            user_id=user.id,
            title="Booking confirmed",
            message=f"Your booking for {event.title} is confirmed.",
            type="BOOKING"
        )

        db.add_all([ticket, notification])
        db.commit()

        db.refresh(booking)
        available = event.available_tickets

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, "Booking failed. Please try again.")

    # Broadcast only after the database transaction succeeds.
    await manager.broadcast(
        data.event_id,
        {
            "type": "ticket_availability",
            "event_id": data.event_id,
            "available_tickets": available
        }
    )

    return booking


@router.get("/history", response_model=list[BookingOut])
def booking_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return (
        db.query(Booking)
        .filter(Booking.user_id == user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )


@router.delete("/{booking_id}")
async def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.user_id == user.id
        )
        .with_for_update()
        .first()
    )

    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.booking_status == "CANCELLED":
        raise HTTPException(400, "Booking already cancelled")

    event_id = booking.event_id
    quantity = booking.ticket_quantity

    result = db.execute(
        update(Event)
        .where(Event.id == event_id)
        .values(
            available_tickets=(
                Event.available_tickets + quantity
            )
        )
    )

    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(404, "Event not found")

    booking.booking_status = "CANCELLED"

    try:
        db.commit()
        db.refresh(booking)

        event = db.query(Event).filter(
            Event.id == event_id
        ).first()

        available = event.available_tickets

    except Exception:
        db.rollback()
        raise HTTPException(500, "Cancellation failed. Please try again.")

    await manager.broadcast(
        event_id,
        {
            "type": "ticket_availability",
            "event_id": event_id,
            "available_tickets": available
        }
    )

    return {"message": "Booking cancelled"}
