
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
        raise HTTPException(
            status_code=400,
            detail="Ticket quantity must be greater than zero"
        )

    try:
        # Atomically reserve only the tickets that are available.
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

            event_exists = db.query(Event.id).filter(
                Event.id == data.event_id
            ).first()

            if not event_exists:
                raise HTTPException(404, "Event not found")

            raise HTTPException(409, "Not enough tickets available")

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

        available_row = db.query(Event.available_tickets).filter(
            Event.id == data.event_id
        ).first()
        available = available_row[0]

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        print("BOOKING ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Booking failed. Please try again."
        )

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
    try:
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
            .where(
                Event.id == event_id,
                Event.available_tickets + quantity <= Event.total_tickets
            )
            .values(
                available_tickets=Event.available_tickets + quantity
            )
        )

        if result.rowcount == 0:
            raise HTTPException(
                409,
                "Ticket availability could not be restored safely"
            )

        booking.booking_status = "CANCELLED"
        db.commit()

        available_row = db.query(Event.available_tickets).filter(
            Event.id == event_id
        ).first()

        if not available_row:
            raise HTTPException(404, "Event not found")

        available = available_row[0]

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        print("CANCELLATION ERROR:", repr(exc))
        raise HTTPException(
            status_code=500,
            detail="Cancellation failed. Please try again."
        )

    await manager.broadcast(
        event_id,
        {
            "type": "ticket_availability",
            "event_id": event_id,
            "available_tickets": available
        }
    )

    return {"message": "Booking cancelled"}
