
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Coupon, Booking
from app.dependencies import get_current_user

router = APIRouter(prefix="/coupons", tags=["Coupons"])


class CouponCreate(BaseModel):
    coupon_code: str = Field(min_length=3, max_length=50)
    discount_type: str
    discount_value: float = Field(gt=0)
    minimum_booking_amount: float = Field(default=0, ge=0)
    expiry_date: datetime | None = None
    usage_limit: int | None = Field(default=None, gt=0)


class CouponValidate(BaseModel):
    booking_id: int
    coupon_code: str


@router.post("/")
def create_coupon(
    data: CouponCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    code = data.coupon_code.strip().upper()
    discount_type = data.discount_type.upper()

    if discount_type not in ("PERCENTAGE", "FIXED"):
        raise HTTPException(
            status_code=400,
            detail="Discount type must be PERCENTAGE or FIXED"
        )

    if discount_type == "PERCENTAGE" and data.discount_value > 100:
        raise HTTPException(
            status_code=400,
            detail="Percentage discount cannot exceed 100"
        )

    if data.expiry_date and data.expiry_date <= datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="Expiry date must be in the future"
        )

    if db.query(Coupon).filter(Coupon.coupon_code == code).first():
        raise HTTPException(
            status_code=400,
            detail="Coupon code already exists"
        )

    coupon = Coupon(
        coupon_code=code,
        discount_type=discount_type,
        discount_value=data.discount_value,
        minimum_booking_amount=data.minimum_booking_amount,
        expiry_date=data.expiry_date,
        usage_limit=data.usage_limit,
        usage_count=0,
        is_active=True
    )

    db.add(coupon)
    db.commit()
    db.refresh(coupon)

    return {
        "message": "Coupon created successfully",
        "coupon_id": coupon.id,
        "coupon_code": coupon.coupon_code
    }


@router.post("/validate")
def validate_coupon(
    data: CouponValidate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == data.booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(404, "Booking not found")

    if booking.user_id != current_user.id:
        raise HTTPException(403, "You cannot modify this booking")

    if booking.booking_status == "CONFIRMED":
        raise HTTPException(
            400,
            "Booking is already confirmed"
        )

    coupon = (
        db.query(Coupon)
        .filter(Coupon.coupon_code == data.coupon_code.strip().upper())
        .first()
    )

    if not coupon or not coupon.is_active:
        raise HTTPException(400, "Invalid or inactive coupon")

    if coupon.expiry_date and coupon.expiry_date <= datetime.utcnow():
        raise HTTPException(400, "Coupon has expired")

    if (
        coupon.usage_limit is not None
        and coupon.usage_count >= coupon.usage_limit
    ):
        raise HTTPException(400, "Coupon usage limit reached")

    amount = booking.total_price

    if amount < coupon.minimum_booking_amount:
        raise HTTPException(
            400,
            f"Minimum booking amount is {coupon.minimum_booking_amount}"
        )

    if coupon.discount_type == "PERCENTAGE":
        discount = amount * coupon.discount_value / 100
    else:
        discount = coupon.discount_value

    discount = round(min(discount, amount), 2)
    final_amount = round(amount - discount, 2)

    booking.coupon_id = coupon.id
    booking.discount_amount = discount
    booking.final_amount = final_amount

    db.commit()

    return {
        "message": "Coupon applied successfully",
        "booking_id": booking.id,
        "original_amount": amount,
        "discount_amount": discount,
        "final_amount": final_amount,
        "coupon_code": coupon.coupon_code
    }
