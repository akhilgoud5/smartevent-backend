import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Booking, Event, Ticket, Notification, User
from app.schemas import BookingCreate, BookingOut
from app.dependencies import get_current_user

router = APIRouter()

@router.post("/", response_model=BookingOut)
def create_booking(data: BookingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = db.query(Event).filter(Event.id == data.event_id).first()
    if not event:
        raise HTTPException(404, "Event not found")
    if data.ticket_quantity > event.available_tickets:
        raise HTTPException(400, "Not enough tickets available")

    total = event.ticket_price * data.ticket_quantity
    booking = Booking(
        user_id=user.id,
        event_id=event.id,
        ticket_quantity=data.ticket_quantity,
        total_price=total,
        booking_status="CONFIRMED"
    )
    event.available_tickets -= data.ticket_quantity
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
    db.add(ticket)
    db.add(notification)
    db.commit()
    db.refresh(booking)
    return booking

@router.get("/history", response_model=list[BookingOut])
def booking_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Booking).filter(Booking.user_id == user.id).order_by(Booking.created_at.desc()).all()

@router.delete("/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == user.id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.booking_status == "CANCELLED":
        raise HTTPException(400, "Booking already cancelled")
    booking.booking_status = "CANCELLED"
    booking.event.available_tickets += booking.ticket_quantity
    db.commit()
    return {"message": "Booking cancelled"}
