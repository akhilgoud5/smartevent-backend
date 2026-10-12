
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Payment, Notification
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@router.post("/{booking_id}/simulate")
def simulate_payment(
    booking_id: int,
    succeed: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot pay for another user's booking"
        )

    if booking.booking_status == "CONFIRMED":
        raise HTTPException(
            status_code=400,
            detail="Booking is already confirmed"
        )

    existing_payment = (
        db.query(Payment)
        .filter(Payment.booking_id == booking_id)
        .first()
    )

    if existing_payment and existing_payment.payment_status == "SUCCESS":
        raise HTTPException(
            status_code=400,
            detail="Payment already completed"
        )

    if existing_payment:
        payment = existing_payment
    else:
        payment = Payment(
            booking_id=booking.id,
            amount=booking.final_amount
            if booking.final_amount is not None
            else booking.total_price,
            payment_method="SIMULATED",
            payment_status="PENDING"
        )
        db.add(payment)

    if succeed:
        payment.payment_status = "SUCCESS"
        payment.transaction_id = f"SIM-{uuid4().hex[:12]}"
        booking.booking_status = "CONFIRMED"

        notification = Notification(
            user_id=current_user.id,
            title="Payment Successful",
            message=(
                f"Your payment for booking #{booking.id} "
                f"was successful. Amount: {payment.amount}."
            ),
            type="PAYMENT",
            is_read=False
        )

        message = "Payment successful"

    else:
        payment.payment_status = "FAILED"
        payment.transaction_id = f"SIM-{uuid4().hex[:12]}"

        notification = Notification(
            user_id=current_user.id,
            title="Payment Failed",
            message=(
                f"Your payment for booking #{booking.id} "
                "failed. Please try again."
            ),
            type="PAYMENT",
            is_read=False
        )

        message = "Payment failed"

    db.add(notification)
    db.commit()
    db.refresh(payment)

    return {
        "message": message,
        "payment_id": payment.id,
        "booking_id": payment.booking_id,
        "payment_status": payment.payment_status,
        "transaction_id": payment.transaction_id,
        "amount": payment.amount,
        "booking_status": booking.booking_status
    }


@router.get("/{booking_id}")
def get_payment(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    payment = (
        db.query(Payment)
        .filter(Payment.booking_id == booking_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found"
        )

    return {
        "payment_id": payment.id,
        "booking_id": payment.booking_id,
        "payment_status": payment.payment_status,
        "transaction_id": payment.transaction_id,
        "amount": payment.amount  
    }
