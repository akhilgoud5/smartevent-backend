from io import BytesIO

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ticket, Booking, User
from app.schemas import TicketOut
from app.dependencies import get_current_user


router = APIRouter()


@router.get("/", response_model=list[TicketOut])
def my_tickets(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return (
        db.query(Ticket)
        .join(Booking)
        .filter(
            Booking.user_id == user.id,
            Booking.booking_status == "CONFIRMED"
        )
        .all()
    )


@router.get("/{ticket_code}")
def verify_ticket(
    ticket_code: str,
    db: Session = Depends(get_db)
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_code == ticket_code)
        .first()
    )

    if not ticket:
        raise HTTPException(404, "Invalid ticket")

    if ticket.booking.booking_status != "CONFIRMED":
        raise HTTPException(400, "Ticket is not valid")

    return {
        "valid": True,
        "ticket_code": ticket.ticket_code,
        "booking_id": ticket.booking_id,
        "event_id": ticket.booking.event_id,
        "ticket_quantity": ticket.booking.ticket_quantity
    }


@router.get("/{ticket_id}/qr")
def generate_qr_code(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(404, "Ticket not found")

    if ticket.booking.booking_status != "CONFIRMED":
        raise HTTPException(400, "Ticket is not valid")

    # QR contains the unique ticket code
    qr_data = ticket.ticket_code

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    qr_image = qr.make_image()

    image_bytes = BytesIO()
    qr_image.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    return StreamingResponse(
        image_bytes,
        media_type="image/png"
    )